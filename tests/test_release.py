"""Release failures are tested independently of the allowlist selection code."""
import base64
import hashlib
import json
from pathlib import Path
import zipfile
import pytest
from scripts.release import build_release, validate_archive, ReleaseError, safe_path

@pytest.fixture
def source(tmp_path):
    (tmp_path/'README.md').write_text('Synthetic educational simulator.\n')
    (tmp_path/'release-files.json').write_text(json.dumps({'files':['README.md']}))
    (tmp_path/'data').mkdir()
    (tmp_path/'data/sender-secrets.json').write_text(json.dumps({'operator-key-01':'a7'*32}))
    return tmp_path

def test_release_is_deterministic_and_has_no_runtime_material(source,tmp_path_factory):
    dest=tmp_path_factory.mktemp('releases')
    (source/'data/kavach.sqlite3').write_bytes(b'private database')
    (source/'.env').write_text('PRIVATE=never-release')
    a,b=dest/'a.zip',dest/'b.zip'
    build_release(source,a);build_release(source,b)
    assert a.read_bytes()==b.read_bytes()
    assert validate_archive(a,source)['status']=='PASS'
    with zipfile.ZipFile(a) as z:
        assert set(z.namelist())=={'kavach/README.md','kavach/RELEASE_MANIFEST.json'}

@pytest.mark.parametrize('name',['data/sender-secrets.json','data/kavach.sqlite3','x.sqlite3-journal','x.db','x.sqlite-wal','x.sqlite3-shm','.env','.env.local','node_modules/a.js','.venv/a','../secret','/tmp/x','x\\secret','some/private.key','credentials/secret','cache.tmp','archive.zip','C:/secrets','folder/file:stream','README.','folder /file','NUL.txt','COM1','x/.. ','bad\x00name'])
def test_forbidden_paths_are_rejected_even_if_allowlisted(source,name,tmp_path_factory):
    (source/'release-files.json').write_text(json.dumps({'files':[name]}))
    with pytest.raises(ReleaseError):build_release(source,tmp_path_factory.mktemp('bad')/'bad.zip')

@pytest.mark.parametrize('encoding',['hex','raw','base64'])
def test_release_refuses_known_secret_in_permitted_file(source,encoding,tmp_path_factory):
    value='a7'*32
    payload={'hex':value.encode(),'raw':bytes.fromhex(value),'base64':base64.b64encode(bytes.fromhex(value))}[encoding]
    (source/'README.md').write_bytes(b'LEAK '+payload)
    dest=tmp_path_factory.mktemp('leak')/'leak.zip'
    with pytest.raises(ReleaseError,match='signing material'):build_release(source,dest)
    assert not dest.exists()

def test_built_frontend_is_scanned_even_if_not_packaged(source,tmp_path_factory):
    (source/'dist').mkdir();(source/'dist/bundle.js').write_text('a7'*32)
    with pytest.raises(ReleaseError,match='compiled frontend'):build_release(source,tmp_path_factory.mktemp('leak')/'leak.zip')

def test_private_key_marker_fails_build(source,tmp_path_factory):
    (source/'README.md').write_text('-----BEGIN' + ' PRIVATE KEY-----')
    with pytest.raises(ReleaseError,match='Private-key'):build_release(source,tmp_path_factory.mktemp('leak')/'leak.zip')

def test_independent_zip_validation_rejects_appended_forbidden_entry(source,tmp_path_factory):
    archive=tmp_path_factory.mktemp('tamper')/'tamper.zip';build_release(source,archive)
    with zipfile.ZipFile(archive,'a') as z:z.writestr('kavach/data/sender-secrets.json','{}')
    with pytest.raises(ReleaseError):validate_archive(archive,source)

def test_symlink_cannot_smuggle_runtime_content(source,tmp_path_factory):
    (source/'README.md').unlink()
    try:
        (source/'README.md').symlink_to(source/'data/sender-secrets.json')
    except OSError as exc:
        if getattr(exc,'winerror',None)==1314:
            pytest.skip('Windows lacks symlink creation privilege; real symlink gate runs on Linux CI.')
        raise
    with pytest.raises(ReleaseError,match='unsafe'):build_release(source,tmp_path_factory.mktemp('leak')/'leak.zip')

def test_real_submission_archive_when_built():
    root=Path(__file__).resolve().parents[1]
    import tempfile
    with tempfile.TemporaryDirectory(prefix='kavach-release-gate-') as directory:
        archive=Path(directory)/'release.zip'
        build_release(root,archive)
        assert validate_archive(archive,root)['status']=='PASS'

def test_new_source_cannot_be_omitted(source,tmp_path_factory):
    component=source/'web/src/components/NewPanel.tsx'
    component.parent.mkdir(parents=True)
    component.write_text('export const Panel = () => null;')
    with pytest.raises(ReleaseError,match='Required sources omitted'):
        build_release(source,tmp_path_factory.mktemp('missing')/'bad.zip')

def test_missing_allowlisted_source_fails(source,tmp_path_factory):
    (source/'README.md').unlink()
    with pytest.raises(ReleaseError,match='Missing or unsafe'):
        build_release(source,tmp_path_factory.mktemp('missing')/'bad.zip')

def test_generated_report_is_refused(source,tmp_path_factory):
    (source/'release-files.json').write_text(json.dumps({'files':['reports/result.json']}))
    with pytest.raises(ReleaseError,match='Generated reports'):
        build_release(source,tmp_path_factory.mktemp('report')/'bad.zip')

def test_independent_validation_detects_hash_tampering(source,tmp_path_factory):
    archive=tmp_path_factory.mktemp('hash')/'bad.zip'
    build_release(source,archive)
    with zipfile.ZipFile(archive) as original:
        entries=[(entry,original.read(entry)) for entry in original.infolist()]
    with zipfile.ZipFile(archive,'w') as changed:
        for entry,content in entries:
            changed.writestr(entry,b'changed' if entry.filename.endswith('README.md') else content)
    with pytest.raises(ReleaseError,match='hash mismatch'):
        validate_archive(archive,source)

def test_archive_symlink_is_rejected_without_os_privileges(source,tmp_path_factory):
    import stat
    archive=tmp_path_factory.mktemp('symlink-zip')/'bad.zip'
    build_release(source,archive)
    with zipfile.ZipFile(archive) as original:
        entries=[(entry,original.read(entry)) for entry in original.infolist()]
    with zipfile.ZipFile(archive,'w') as changed:
        for entry,content in entries:
            if entry.filename.endswith('README.md'):
                entry.external_attr=(stat.S_IFLNK | 0o777)<<16
            changed.writestr(entry,content)
    with pytest.raises(ReleaseError,match='symlink'):
        validate_archive(archive,source)
