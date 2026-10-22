export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  institution_id: string | null;
  region_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface DashboardStats {
  total_applications: number;
  applications_by_stage: Record<string, number>;
  pending_compliance: number;
  unread_notifications: number;
}

export interface Region {
  id: string;
  code: string;
  name: string;
}

export interface Institution {
  id: string;
  pid: string;
  name: string;
  institution_type: string;
  state: string;
  city: string;
  region_id: string;
}

export interface AcademicYear {
  id: string;
  year_label: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
}

export interface Application {
  id: string;
  reference_number: string;
  institution_id: string;
  category_id: string;
  academic_year_id: string;
  stage: string;
  status: string;
  submitted_by: string | null;
  assigned_officer_id: string | null;
  region_id: string;
  version: number;
  form_data: Record<string, unknown> | null;
  submitted_at: string | null;
  decided_at: string | null;
  decision: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface UserDetail {
  id: string;
  email: string;
  full_name: string;
  role: string;
  institution_id: string | null;
  region_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  institution_name: string | null;
  region_name: string | null;
}

export interface Role {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  is_active: boolean;
}

export interface InstitutionDetail {
  id: string;
  pid: string;
  name: string;
  institution_type: string;
  region_id: string;
  region_name: string | null;
  state: string;
  city: string;
  address: string | null;
  pincode: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  established_year: number | null;
  website: string | null;
  created_at: string;
  updated_at: string;
  user_count: number;
}

export interface AuditEvent {
  id: string;
  actor_id: string | null;
  actor_role: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  changes: Record<string, unknown> | null;
  occurred_at: string;
}

export type RoleName =
  | 'institution_applicant'
  | 'institution_signatory'
  | 'regional_officer'
  | 'scrutiny_officer'
  | 'regional_coordinator'
  | 'bureau_officer'
  | 'evc_coordinator'
  | 'evc_member'
  | 'sac_shc_member'
  | 'competent_authority'
  | 'compliance_officer'
  | 'system_admin'
  | 'rule_admin'
  | 'audit_reviewer';

// ---------------------------------------------------------------- Phase 3 --

export interface ApplicationCategory {
  id: string;
  code: string;
  name: string;
  processing_category: number;
  requires_self_disclosure: boolean;
  requires_scrutiny: boolean;
  requires_evc: boolean;
  sac_shc_applicable: string;
  route_type: 'FULL' | 'SCRUTINY_ONLY' | 'SELF_DISCLOSURE' | string;
  workflow_name: string;
}

export interface ApplicationListItem {
  id: string;
  reference_number: string;
  institution_id: string;
  institution_name: string;
  category_code: string;
  category_name: string;
  route_type: string;
  academic_year: string;
  region_code: string | null;
  stage: string;
  stage_label: string;
  status: string;
  payment_status: string;
  version: number;
  submitted_at: string | null;
  decided_at: string | null;
  decision: string | null;
  created_at: string;
  updated_at: string;
  needs_my_action: boolean;
}

export type FieldType = 'text' | 'textarea' | 'email' | 'tel' | 'select' | 'integer' | 'checkbox';

export interface FormField {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  min_length?: number;
  max_length?: number;
  min?: number;
  max?: number;
  pattern?: string;
  options?: string[];
  help?: string;
  section?: string;
  greater_than_field?: string;
  different_from_field?: string;
}

export interface FormSchema {
  category_code: string;
  version: number;
  verification_status: string;
  verification_note: string;
  has_category_fields: boolean;
  fields: FormField[];
}

export interface AvailableAction {
  to_stage: string;
  to_stage_label: string;
  label: string;
  tone: 'approve' | 'reject' | 'warn' | 'neutral';
  requires_remarks: boolean;
  is_decision: boolean;
  definition_trigger: string;
  note: string | null;
  blockers: string[];
}

export interface ClockSummary {
  current_owner: 'AICTE' | 'INSTITUTION' | 'HELD' | null;
  completed: boolean;
  elapsed_seconds: Record<string, number>;
  policy_note: string;
}

export interface ApplicationDetail {
  id: string;
  reference_number: string;
  institution: { id: string; name: string; pid: string; city: string; state: string };
  category: {
    id: string; code: string; name: string; processing_category: number;
    requires_scrutiny: boolean; requires_evc: boolean; requires_self_disclosure: boolean; sac_shc_applicable: string;
  };
  academic_year: { id: string; year_label: string };
  region: { id: string; code: string; name: string } | null;
  workflow: {
    id: string; name: string; version: number; route_type: string;
    stages: { code: string; label: string; type: string }[];
  };
  stage: string;
  stage_label: string;
  stage_type: string;
  stage_note: string | null;
  status: 'ACTIVE' | 'WITHDRAWN' | 'CLOSED' | string;
  version: number;
  form_data: Record<string, unknown>;
  form_schema_version: number | null;
  form_errors: Record<string, string>;
  payment: { status: string; reference: string | null; confirmed_at: string | null; is_mock: boolean; fee_note: string };
  submitted_at: string | null;
  decided_at: string | null;
  decision: string | null;
  decision_remarks: string | null;
  created_at: string;
  updated_at: string;
  permissions: { can_edit: boolean; can_withdraw: boolean; can_mock_pay: boolean };
  available_actions: AvailableAction[];
  clock: ClockSummary;
}

export interface TimelineActor {
  name: string | null;
  role: string | null;
}

export interface TimelineTransition {
  id: string;
  sequence_no: number | null;
  from_stage: string;
  from_stage_label: string;
  to_stage: string;
  to_stage_label: string;
  trigger_type: string;
  actor: TimelineActor;
  remarks: string | null;
  rule_family_code: string | null;
  rule_version: number | null;
  metadata: Record<string, unknown>;
  occurred_at: string;
}

export interface Timeline {
  application_id: string;
  transitions: TimelineTransition[];
  stage_entries: {
    id: string; stage: string; stage_label: string; entered_at: string; exited_at: string | null;
    duration_seconds: number | null; entered_by: TimelineActor; remarks: string | null;
  }[];
  clock_events: { id: string; event_type: string; clock_owner: string; occurred_at: string; reason: string | null }[];
  clock: ClockSummary;
}
