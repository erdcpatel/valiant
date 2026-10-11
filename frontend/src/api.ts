import {
  WorkflowSchema,
  WorkflowRun,
  RunEvent,
  UserProfile,
  EnvironmentInfo,
  RunComparisonResult,
  ScheduleConfig,
  WebhookConfig,
} from './types';

const API_BASE = '/api';

let _activeEnvironment: string = localStorage.getItem('valiant_env') || 'dev';

export function setActiveApiEnvironment(env: string) {
  _activeEnvironment = env;
  try {
    localStorage.setItem('valiant_env', env);
  } catch (e) {
    // quiet localstorage failure
  }
}

export function getActiveApiEnvironment(): string {
  return _activeEnvironment;
}

function getEnvHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return {
    'X-Valiant-Env': _activeEnvironment,
    ...extra,
  };
}

export async function getEnvironments(): Promise<{
  active_env: string;
  default_env: string;
  allowed_environments: EnvironmentInfo[];
}> {
  const res = await fetch(`${API_BASE}/environments`, {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch platform environments');
  return res.json();
}

export async function getMe(): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to get auth profile');
  return res.json();
}

export async function loginUser(username: string, password: string): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: getEnvHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ username, password }),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
    throw new Error(err.detail || 'Login failed');
  }
  return res.json();
}

export async function logoutUser(): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  return res.json();
}

export async function getWorkflows(): Promise<Record<string, WorkflowSchema>> {
  const res = await fetch(`${API_BASE}/workflows`, {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch workflows');
  const json = await res.json();
  return json.data;
}

export async function getWorkflow(id: string): Promise<WorkflowSchema> {
  const res = await fetch(`${API_BASE}/workflows/${id}`, {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error(`Failed to fetch workflow ${id}`);
  const json = await res.json();
  return json.data;
}

export async function getRuns(
  limit = 50,
  workflow?: string,
  user?: string,
  env?: string
): Promise<WorkflowRun[]> {
  const targetEnv = env || _activeEnvironment;
  const url = new URL(`${window.location.origin}${API_BASE}/runs`);
  url.searchParams.set('limit', String(limit));
  url.searchParams.set('env', targetEnv);
  if (workflow) url.searchParams.set('workflow_name', workflow);
  if (user) url.searchParams.set('user', user);

  const res = await fetch(url.toString(), {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch runs');
  const json = await res.json();
  return json.data;
}

export async function getRun(runId: string, env?: string): Promise<WorkflowRun> {
  const targetEnv = env || _activeEnvironment;
  const url = new URL(`${window.location.origin}${API_BASE}/runs/${runId}`);
  url.searchParams.set('env', targetEnv);
  const res = await fetch(url.toString(), {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error(`Failed to fetch run ${runId}`);
  const json = await res.json();
  return json.data;
}

export async function triggerRun(
  workflowName: string,
  inputs: Record<string, any>,
  asyncMode = true,
  environment?: string,
  profile?: string
): Promise<{ run_id: string; status: string; environment?: string; profile?: string; data?: any }> {
  const targetEnv = environment || _activeEnvironment;
  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: getEnvHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      workflow_name: workflowName,
      inputs,
      async_mode: asyncMode,
      environment: targetEnv,
      profile: profile || targetEnv,
    }),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to start run' }));
    throw new Error(err.detail || 'Execution request failed');
  }
  return res.json();
}

export async function cancelRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/${runId}/cancel`, {
    method: 'POST',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to cancel run');
}

export async function deleteRun(runId: string, env?: string): Promise<void> {
  const targetEnv = env || _activeEnvironment;
  const url = new URL(`${window.location.origin}${API_BASE}/runs/${runId}`);
  url.searchParams.set('env', targetEnv);
  const res = await fetch(url.toString(), {
    method: 'DELETE',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to delete run');
}

export async function resumeRun(
  runId: string,
  fromStep?: string,
  overrideInputs?: Record<string, any>,
  environment?: string,
  profile?: string
): Promise<{ success: boolean; run_id: string; parent_run_id: string; resumed_from_step: string; status: string }> {
  const targetEnv = environment || _activeEnvironment;
  const res = await fetch(`${API_BASE}/runs/${runId}/resume`, {
    method: 'POST',
    headers: getEnvHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      from_step: fromStep,
      override_inputs: overrideInputs,
      async_mode: true,
      environment: targetEnv,
      profile: profile || targetEnv,
    }),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to resume workflow' }));
    throw new Error(err.detail || 'Resume request failed');
  }
  return res.json();
}

export async function approveStep(
  runId: string,
  stepName: string,
  payload?: { notes?: string; approver?: string },
  env?: string
): Promise<{ success: boolean; status: string; message: string }> {
  const targetEnv = env || _activeEnvironment;
  const url = new URL(`${window.location.origin}${API_BASE}/runs/${runId}/steps/${encodeURIComponent(stepName)}/approve`);
  if (targetEnv) url.searchParams.set('env', targetEnv);
  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: getEnvHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload || {}),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to approve step' }));
    throw new Error(err.detail || 'Step approval failed');
  }
  return res.json();
}

export async function rejectStep(
  runId: string,
  stepName: string,
  payload?: { reason?: string; approver?: string },
  env?: string
): Promise<{ success: boolean; status: string; message: string }> {
  const targetEnv = env || _activeEnvironment;
  const url = new URL(`${window.location.origin}${API_BASE}/runs/${runId}/steps/${encodeURIComponent(stepName)}/reject`);
  if (targetEnv) url.searchParams.set('env', targetEnv);
  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: getEnvHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload || {}),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to reject step' }));
    throw new Error(err.detail || 'Step rejection failed');
  }
  return res.json();
}

export async function cleanupRuns(maxKeep = 40, env?: string): Promise<{ deleted_count: number; message: string }> {
  const targetEnv = env || _activeEnvironment;
  const res = await fetch(`${API_BASE}/runs/cleanup`, {
    method: 'POST',
    headers: getEnvHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ max_keep: maxKeep, environment: targetEnv }),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to prune runs');
  return res.json();
}

export async function clearAllRuns(env?: string): Promise<{ deleted_count: number; message: string }> {
  const targetEnv = env || _activeEnvironment;
  const url = new URL(`${window.location.origin}${API_BASE}/runs`);
  url.searchParams.set('env', targetEnv);
  const res = await fetch(url.toString(), {
    method: 'DELETE',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to clear runs');
  return res.json();
}

export function subscribeToRunEvents(
  runId: string,
  onEvent: (event: RunEvent) => void
): () => void {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}${API_BASE}/ws/runs/${runId}`;

  let ws: WebSocket | null = new WebSocket(wsUrl);

  ws.onmessage = (messageEvent) => {
    try {
      const data: RunEvent = JSON.parse(messageEvent.data);
      onEvent(data);
    } catch (e) {
      // ignore parse errors
    }
  };

  const pingInterval = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send('ping');
    }
  }, 10000);

  return () => {
    clearInterval(pingInterval);
    if (ws) {
      ws.close();
      ws = null;
    }
  };
}

export async function compareRuns(
  runA: string,
  runB: string,
  envA?: string,
  envB?: string
): Promise<RunComparisonResult> {
  const url = new URL(`${window.location.origin}${API_BASE}/runs/compare/diff`);
  url.searchParams.set('run_a', runA);
  url.searchParams.set('run_b', runB);
  if (envA) url.searchParams.set('env_a', envA);
  if (envB) url.searchParams.set('env_b', envB);

  const res = await fetch(url.toString(), {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to compare runs' }));
    throw new Error(err.detail || 'Comparison failed');
  }
  const json = await res.json();
  return json.data;
}

export async function getSchedules(): Promise<ScheduleConfig[]> {
  const res = await fetch(`${API_BASE}/schedules`, {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch schedules');
  const json = await res.json();
  return json.data;
}

export async function createSchedule(data: {
  name: string;
  workflow_name: string;
  cron_expression: string;
  inputs?: Record<string, any>;
  enabled?: boolean;
}): Promise<ScheduleConfig> {
  const res = await fetch(`${API_BASE}/schedules`, {
    method: 'POST',
    headers: getEnvHeaders({ 'Content-Type': 'application/json' }),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create schedule' }));
    throw new Error(err.detail || 'Failed to create schedule');
  }
  const json = await res.json();
  return json.data;
}

export async function toggleSchedule(scheduleId: string): Promise<ScheduleConfig> {
  const res = await fetch(`${API_BASE}/schedules/${scheduleId}/toggle`, {
    method: 'PATCH',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to toggle schedule');
  const json = await res.json();
  return json.data;
}

export async function runScheduleNow(scheduleId: string): Promise<{ run_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/schedules/${scheduleId}/run`, {
    method: 'POST',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to trigger schedule' }));
    throw new Error(err.detail || 'Failed to trigger schedule');
  }
  const json = await res.json();
  return json.data;
}

export async function deleteSchedule(scheduleId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/schedules/${scheduleId}`, {
    method: 'DELETE',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to delete schedule');
}

export async function validateCron(cronExpression: string): Promise<{
  valid: boolean;
  human_description?: string;
  next_runs?: string[];
  error?: string;
}> {
  const res = await fetch(`${API_BASE}/schedules/validate-cron`, {
    method: 'POST',
    headers: getEnvHeaders({ 'Content-Type': 'application/json' }),
    credentials: 'include',
    body: JSON.stringify({ cron_expression: cronExpression }),
  });
  if (!res.ok) throw new Error('Failed to validate cron');
  return res.json();
}

export async function getWebhooks(): Promise<WebhookConfig[]> {
  const res = await fetch(`${API_BASE}/webhooks`, {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch webhooks');
  const json = await res.json();
  return json.data;
}

export async function createWebhook(data: {
  name: string;
  workflow_name: string;
  secret_header?: string;
  parameter_mapping?: Record<string, any>;
  enabled?: boolean;
}): Promise<WebhookConfig> {
  const res = await fetch(`${API_BASE}/webhooks`, {
    method: 'POST',
    headers: getEnvHeaders({ 'Content-Type': 'application/json' }),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create webhook' }));
    throw new Error(err.detail || 'Failed to create webhook');
  }
  const json = await res.json();
  return json.data;
}

export async function toggleWebhook(webhookId: string): Promise<WebhookConfig> {
  const res = await fetch(`${API_BASE}/webhooks/${webhookId}/toggle`, {
    method: 'PATCH',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to toggle webhook');
  const json = await res.json();
  return json.data;
}

export async function testWebhookPing(webhookId: string): Promise<{ run_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/webhooks/${webhookId}/test`, {
    method: 'POST',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to test webhook' }));
    throw new Error(err.detail || 'Failed to test webhook');
  }
  const json = await res.json();
  return json.data;
}

export async function deleteWebhook(webhookId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/webhooks/${webhookId}`, {
    method: 'DELETE',
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to delete webhook');
}

export interface TabularQueryParams {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortDesc?: boolean;
  search?: string;
}

export interface TabularQueryResponse {
  step_name: string;
  total_rows: number;
  page: number;
  page_size: number;
  total_pages: number;
  columns: Array<{ name: string; type: string; category: string }>;
  rows: Record<string, any>[];
  has_artifact: boolean;
  formatted_size?: string;
}

export async function fetchStepTabularData(
  runId: string,
  stepName: string,
  params: TabularQueryParams = {},
  env?: string
): Promise<TabularQueryResponse> {
  const targetEnv = env || _activeEnvironment;
  const url = new URL(`${window.location.origin}${API_BASE}/runs/${runId}/steps/${encodeURIComponent(stepName)}/tabular/data`);
  if (targetEnv) url.searchParams.set('env', targetEnv);
  if (params.page !== undefined) url.searchParams.set('page', String(params.page));
  if (params.pageSize !== undefined) url.searchParams.set('page_size', String(params.pageSize));
  if (params.sortBy) url.searchParams.set('sort_by', params.sortBy);
  if (params.sortDesc !== undefined) url.searchParams.set('sort_desc', String(params.sortDesc));
  if (params.search) url.searchParams.set('search', params.search);

  const res = await fetch(url.toString(), {
    headers: getEnvHeaders(),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch tabular data' }));
    throw new Error(err.detail || 'Failed to fetch tabular data');
  }
  return res.json();
}

export function getTabularExportUrl(
  runId: string,
  stepName: string,
  format: 'csv' | 'parquet' | 'json' = 'csv',
  env?: string
): string {
  const targetEnv = env || _activeEnvironment;
  const url = new URL(`${window.location.origin}${API_BASE}/runs/${runId}/steps/${encodeURIComponent(stepName)}/tabular/export`);
  url.searchParams.set('format', format);
  if (targetEnv) url.searchParams.set('env', targetEnv);
  return url.toString();
}

export function getRunReportUrl(runId: string, download: boolean = false, env?: string): string {
  const targetEnv = env || _activeEnvironment;
  const url = new URL(`${window.location.origin}${API_BASE}/runs/${runId}/report/html`);
  if (download) url.searchParams.set('download', 'true');
  if (targetEnv) url.searchParams.set('env', targetEnv);
  return url.toString();
}

