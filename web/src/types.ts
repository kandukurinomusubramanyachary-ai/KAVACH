export type MessageType='COMMAND'|'TELEMETRY';
export type Mode='NORMAL'|'POWER_SAVING'|'SAFE';
export type Action='GET_STATUS'|'SET_MODE'|'SET_REPORT_INTERVAL'|'TELEMETRY_STATUS';
export type JsonValue=string|number|boolean|null|JsonValue[]|{[key:string]:JsonValue};
export interface MessageEnvelope {
 version:1;message_id:string;message_type:MessageType;sender_id:string;target_id:string;
 key_id:string;sequence:number;issued_at:number;expires_at:number;action:Action;
 payload:Record<string,JsonValue>;auth_tag:string;
}
/** antenna_status and power_level_pct are synthetic model outputs derived from mode.
 * They are not spacecraft telemetry, not physical truth, and no message can set them. */
export interface ProtectedState {mode:Mode;report_interval_s:number;antenna_status:AntennaStatus;power_level_pct:number}
export type AntennaStatus='NOMINAL'|'DEGRADED'|'STOWED';
export interface Telemetry {battery_pct:number;temperature_c:number;mode:Mode;received_at:number;source:string;message_id?:string}
export interface StateSnapshot {session_id:string;protected_state:ProtectedState;latest_telemetry:Telemetry|null;target_id:string;policy_version:string;state_schema_version:number}
export type ScenarioId='valid'|'tampered'|'replay'|'expired'|'future'|'unauthorised'|'invalid'|'telemetry'|'unknown_key'|'bad_tag'|'malformed';
export interface Health {status:string;database?:string;session_id?:string}
export type Stage='structure'|'identity'|'authentication'|'payload'|'time'|'permissions'|'replay'|'commit';
export interface ValidationCheck {stage:Stage;label:string;status:'PASS'|'FAIL'|'NOT_RUN';explanation:string}
export interface Decision {
 event_id?:string;session_id?:string;verdict:'ACCEPTED'|'REJECTED'|'SERVICE_ERROR';reason_code:string;explanation:string;
 checks?:ValidationCheck[];sender_verified:boolean;received_at?:number;protected_state_before?:ProtectedState|null;
 protected_state_after?:ProtectedState|null;state_changed:boolean;telemetry_before?:Telemetry|null;telemetry_after?:Telemetry|null;
 policy_version:string;input_sha256?:string;message:Partial<MessageEnvelope>|null;submitted_text?:string;duration_ms?:number;
 audit_persisted?:boolean;replay_state_advanced?:boolean;replay_sequence_before?:number|null;replay_sequence_after?:number|null;
 roundtrip_ms?:number;input_truncated?:boolean;input_hash_scope?:string;prototype_only?:boolean;
 /** Which validation stage first failed, per the receiver. Null when accepted. */
 first_failed_stage?:Stage|null
}
export interface AuditRecord extends Decision {event_id:string;session_id:string;received_at:number;
 /** Which validation stage first failed, resolved server-side. Null when accepted. */
 first_failed_stage?:Stage|null}
export interface AuditPage {events:AuditRecord[];total:number}
export interface FixtureResponse {message:MessageEnvelope;raw_text?:string;modified:boolean;session_id:string;expected_outcome?:string;expectation_source?:string}
export interface ScenarioResult {name:string;expected:string;observed:string;passed:boolean;state_preserved:boolean;result:Decision;event_id?:string;note?:string}
export interface ScenarioReport {suite_id:string;session_id:string;executed_at:number;clock:string;passed:number;total:number;results:ScenarioResult[];isolated:boolean}

export interface Metrics {
 scope:string;session_id:string;
 live:{messages_checked:number;accepted:number;rejected:number;service_errors:number;
  replay_attempts_detected:number;out_of_order_rejected:number;authentication_failures:number;
  authorisation_denials:number;reason_code_breakdown:Record<string,number>;
  rejection_reasons:Record<string,number>;first_failed_stages:Record<string,number>;
  acceptance_rate:number|null};
 scenario_suites:{runs:number;cases_executed:number;cases_passed:number;cases_failed:number;
  protected_state_integrity_violations:number;note:string};
}
export interface AnomalyFinding {rule:string;detail:string;event_id?:string;received_at?:number;verdict?:string;reason_code?:string}
export interface AnomalyReport {session_id:string;findings:AnomalyFinding[];finding_count:number;
 rules:{rule:string;description:string;thresholds:Record<string,unknown>}[];disclaimer:string}
export interface AuditChainProblem {kind:string;detail:string;link?:number}
export interface AuditChainReport {status:'VERIFIED'|'FAILED';links_checked:number;uncovered_records:number;
 uncovered_note?:string;problems:AuditChainProblem[];genesis:string;covered_fields:string[];limitations:string[]}
export interface PolicyRole {role:string;label:string;permissions:Record<string,string[]>;senders:string[]}
export interface PolicySnapshot {policy_version:string;roles:PolicyRole[];default_roles:Record<string,string>;
 server_authoritative:boolean;note:string}
