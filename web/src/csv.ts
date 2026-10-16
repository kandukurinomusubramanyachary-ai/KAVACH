/** CSV serialisation for evidence export (roadmap feature 16).
 * Pure functions, no React, no network. RFC 4180 quoting.
 */

/** Quote a single cell. Null/undefined become empty, never the string "null". */
export function csvCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  const raw = String(value);
  // A rejected envelope can still contain an attacker-controlled claimed sender.
  // Keep spreadsheets from evaluating it. JSON remains the byte-faithful evidence.
  const text = typeof value === 'string' && /^[\t\r\n ]*[=+\-@]/.test(raw) ? "'" + raw : raw;
  return /[",\n\r]/.test(text) ? '"' + text.replaceAll('"', '""') + '"' : text;
}

/** Serialise rows to CSV with CRLF record separators and comma field separators. */
export function toCsv(rows: unknown[][]): string {
  return rows.map(row => row.map(csvCell).join(',')).join('\r\n');
}
