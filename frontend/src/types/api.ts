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
