export type InputType =
  | 'text'
  | 'password'
  | 'number'
  | 'boolean'
  | 'select'
  | 'date'
  | 'email'
  | 'checkbox'
  | 'json';

export interface InputFieldSchema {
  name: string;
  type: InputType;
  label?: string;
  required?: boolean;
  default?: any;
  help_text?: string;
  options?: string[];
  min_value?: number;
  max_value?: number;
  sensitive?: boolean;
}

export interface StepSchema {
  name: string;
  order: number;
  description?: string;
  requires: string[];
  tags: string[];
  parallel_group?: string;
  condition?: string;
  requires_approval?: boolean;
  approval_prompt?: string;
  approval_roles?: string[];
}

export interface WorkflowSchema {
  id: string;
  name: string;
  description: string;
  version: string;
  author?: string;
  tags: string[];
  is_default?: boolean;
  step_count: number;
  steps: StepSchema[];
  inputs: InputFieldSchema[];
  profiles?: Record<string, Record<string, any>>;
}

export type StepStatus = 'pending' | 'running' | 'waiting_approval' | 'rejected' | 'success' | 'failed' | 'skipped';

export interface StepResult {
  id?: number;
  name: string;
  order?: number;
  parallel_group?: string;
  requires?: string[];
  condition?: string;
  status: StepStatus;
  success: boolean;
  message: string;
  skipped: boolean;
  reused?: boolean;
  requires_approval?: boolean;
  approval_prompt?: string;
  approved_by?: string;
  approved_at?: string;
  approval_notes?: string;
  context_before?: Record<string, any>;
  context_snapshot?: Record<string, any>;
  context_delta?: StepContextDelta;
  lineage?: StepLineage;
  executed?: boolean;
  time_taken: number;
  attempts: number;
  metrics: Record<string, any>;
  tags: string[];
  logs: string[];
  data?: any;
  error?: string;
  tabular_data?: TabularDataPayload;
}

export interface TabularColumn {
  name: string;
  type: string;
  category: 'numeric' | 'string' | 'datetime' | 'boolean' | 'other';
}

export interface TabularDataPayload {
  columns: TabularColumn[];
  total_rows: number;
  total_cols: number;
  shape: [number, number];
  preview_limit: number;
  preview_rows: Record<string, any>[];
  has_artifact: boolean;
  artifact_path?: string;
  estimated_size_bytes?: number;
  formatted_size?: string;
}

export interface StepContextDelta {
  reads?: string[];
  added?: Record<string, any>;
  modified?: Record<string, { before: any; after: any }>;
  deleted?: string[];
}

export interface StepLineage {
  upstream_sources?: Record<string, string>;
  downstream_targets?: Record<string, string[]>;
}

export type RunStatus = 'pending' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'cancelled';

export interface WorkflowRun {
  id: string;
  workflow_name: string;
  status: RunStatus;
  success: boolean;
  parent_run_id?: string;
  resumed_from_step?: string;
  total_steps: number;
  executed_steps: number;
  successful_steps: number;
  failed_steps: number;
  skipped_steps: number;
  total_time: number;
  started_at: string;
  completed_at?: string;
  triggered_by?: string;
  environment?: string;
  profile?: string;
  inputs: Record<string, any>;
  context?: Record<string, any>;
  error?: string;
  steps: StepResult[];
}

export interface EnvironmentInfo {
  id: string;
  label: string;
  badge: string;
  color: string;
  description: string;
  is_prod: boolean;
  requires_confirmation: boolean;
}

export interface UserProfile {
  authenticated: boolean;
  username: string;
  role: string;
  name?: string;
  email?: string;
  auth_enabled: boolean;
}

export interface RunEvent {
  run_id: string;
  event_type: 'run_started' | 'step_started' | 'step_log' | 'step_finished' | 'run_finished' | 'run_cancelled' | 'step_waiting_approval' | 'step_approved' | 'step_rejected';
  timestamp: number;
  step_name?: string;
  data: any;
}

export interface StepComparison {
  name: string;
  status_a: string;
  status_b: string;
  success_a: boolean;
  success_b: boolean;
  time_a: number;
  time_b: number;
  time_delta: number;
  match_type: 'regressed' | 'improved' | 'slower' | 'faster' | 'matched' | 'missing_in_target' | 'new_in_target';
  error_a?: string | null;
  error_b?: string | null;
  message_a?: string | null;
  message_b?: string | null;
}

export interface RunComparisonSummary {
  workflow_name: string;
  run_a_id: string;
  run_b_id: string;
  env_a: string;
  env_b: string;
  status_a: string;
  status_b: string;
  success_a: boolean;
  success_b: boolean;
  outcome: 'regression' | 'improved' | 'same';
  time_a: number;
  time_b: number;
  time_delta: number;
  time_ratio: number;
  regressed_steps_count: number;
  slower_steps_count: number;
  inputs_differ_count: number;
  context_differ_count: number;
}

export interface RunComparisonResult {
  summary: RunComparisonSummary;
  step_comparisons: StepComparison[];
  inputs_diff: Record<string, { a: any; b: any }>;
  context_diff: Record<string, { a: any; b: any }>;
  run_a: WorkflowRun;
  run_b: WorkflowRun;
}

export interface ScheduleConfig {
  id: string;
  name: string;
  workflow_name: string;
  cron_expression: string;
  human_description?: string;
  inputs: Record<string, any>;
  enabled: boolean;
  environment: string;
  last_run_at?: string | null;
  last_run_id?: string | null;
  last_status?: string | null;
  next_run_at?: string | null;
  created_at: string;
}

export interface WebhookConfig {
  id: string;
  name: string;
  workflow_name: string;
  token: string;
  environment: string;
  enabled: boolean;
  has_secret?: boolean;
  secret_header?: string | null;
  parameter_mapping: Record<string, any>;
  trigger_count: number;
  last_triggered_at?: string | null;
  created_at: string;
}
