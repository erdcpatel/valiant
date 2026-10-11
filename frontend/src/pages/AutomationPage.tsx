import React, { useState, useEffect } from 'react';
import {
  Clock,
  Radio,
  Plus,
  Play,
  Trash2,
  Copy,
  Check,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Zap,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import {
  getSchedules,
  createSchedule,
  toggleSchedule,
  runScheduleNow,
  deleteSchedule,
  validateCron,
  getWebhooks,
  createWebhook,
  toggleWebhook,
  testWebhookPing,
  deleteWebhook,
} from '../api';
import { ScheduleConfig, WebhookConfig, WorkflowSchema } from '../types';

interface AutomationPageProps {
  workflows: Record<string, WorkflowSchema>;
  activeEnvironment: string;
  onViewRunDetail?: (runId: string) => void;
}

const CRON_PRESETS = [
  { label: 'Every 5 min', expr: '*/5 * * * *', desc: 'Every 5 minutes' },
  { label: 'Every 15 min', expr: '*/15 * * * *', desc: 'Every 15 minutes' },
  { label: 'Hourly', expr: '0 * * * *', desc: 'Every hour at minute 0' },
  { label: 'Daily (Midnight)', expr: '0 0 * * *', desc: 'Every day at 00:00 UTC' },
  { label: 'Weekdays 9 AM', expr: '0 9 * * 1-5', desc: 'Mon-Fri at 09:00 UTC' },
];

export const AutomationPage: React.FC<AutomationPageProps> = ({
  workflows,
  activeEnvironment,
  onViewRunDetail: _onViewRunDetail,
}) => {
  const [subTab, setSubTab] = useState<'schedules' | 'webhooks'>('schedules');
  const [schedules, setSchedules] = useState<ScheduleConfig[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // Modals state
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);
  const [isWebhookModalOpen, setIsWebhookModalOpen] = useState(false);

  // Schedule form state
  const [schedName, setSchedName] = useState('');
  const [schedWorkflow, setSchedWorkflow] = useState('');
  const [schedCron, setSchedCron] = useState('0 * * * *');
  const [schedInputs, setSchedInputs] = useState('{}');
  const [cronValidation, setCronValidation] = useState<{
    valid: boolean;
    human_description?: string;
    next_runs?: string[];
    error?: string;
  } | null>(null);

  // Webhook form state
  const [hookName, setHookName] = useState('');
  const [hookWorkflow, setHookWorkflow] = useState('');
  const [hookSecret, setHookSecret] = useState('');
  const [hookParamMap, setHookParamMap] = useState('{}');

  // Copy feedback state
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const workflowList = Object.values(workflows);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sData, wData] = await Promise.all([getSchedules(), getWebhooks()]);
      setSchedules(sData);
      setWebhooks(wData);
    } catch (err: any) {
      setError(err.message || 'Failed to load automation records');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeEnvironment]);

  // Live validation for cron expressions
  useEffect(() => {
    if (!schedCron.trim()) {
      setCronValidation(null);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const val = await validateCron(schedCron);
        setCronValidation(val);
      } catch {
        setCronValidation({ valid: false, error: 'Validation request failed' });
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [schedCron]);

  const handleToggleSchedule = async (sched: ScheduleConfig) => {
    setActionLoadingId(`sched-toggle-${sched.id}`);
    try {
      const updated = await toggleSchedule(sched.id);
      setSchedules((prev) => prev.map((s) => (s.id === sched.id ? updated : s)));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRunScheduleNow = async (sched: ScheduleConfig) => {
    setActionLoadingId(`sched-run-${sched.id}`);
    try {
      const res = await runScheduleNow(sched.id);
      setSuccessNotice(`Triggered schedule "${sched.name}"! Run ID: ${res.run_id}`);
      setTimeout(() => setSuccessNotice(null), 4000);
      loadData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDeleteSchedule = async (sched: ScheduleConfig) => {
    if (!confirm(`Are you sure you want to delete schedule "${sched.name}"?`)) return;
    setActionLoadingId(`sched-del-${sched.id}`);
    try {
      await deleteSchedule(sched.id);
      setSchedules((prev) => prev.map((s) => s).filter((s) => s.id !== sched.id));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleCreateScheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!schedName.trim() || !schedWorkflow) return;
    let parsedInputs = {};
    try {
      if (schedInputs.trim()) {
        parsedInputs = JSON.parse(schedInputs);
      }
    } catch {
      setError('Schedule inputs must be valid JSON');
      return;
    }

    try {
      await createSchedule({
        name: schedName.trim(),
        workflow_name: schedWorkflow,
        cron_expression: schedCron.trim(),
        inputs: parsedInputs,
      });
      setIsScheduleModalOpen(false);
      setSchedName('');
      setSchedInputs('{}');
      setSuccessNotice(`Scheduled "${schedName}" successfully`);
      setTimeout(() => setSuccessNotice(null), 3000);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleToggleWebhook = async (hook: WebhookConfig) => {
    setActionLoadingId(`hook-toggle-${hook.id}`);
    try {
      const updated = await toggleWebhook(hook.id);
      setWebhooks((prev) => prev.map((w) => (w.id === hook.id ? updated : w)));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleTestWebhookPing = async (hook: WebhookConfig) => {
    setActionLoadingId(`hook-test-${hook.id}`);
    try {
      const res = await testWebhookPing(hook.id);
      setSuccessNotice(`Test ping executed for "${hook.name}"! Run ID: ${res.run_id}`);
      setTimeout(() => setSuccessNotice(null), 4000);
      loadData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDeleteWebhook = async (hook: WebhookConfig) => {
    if (!confirm(`Are you sure you want to delete webhook "${hook.name}"?`)) return;
    setActionLoadingId(`hook-del-${hook.id}`);
    try {
      await deleteWebhook(hook.id);
      setWebhooks((prev) => prev.map((w) => w).filter((w) => w.id !== hook.id));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleCreateWebhookSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hookName.trim() || !hookWorkflow) return;
    let parsedParamMap = {};
    try {
      if (hookParamMap.trim()) {
        parsedParamMap = JSON.parse(hookParamMap);
      }
    } catch {
      setError('Parameter mapping must be valid JSON');
      return;
    }

    try {
      await createWebhook({
        name: hookName.trim(),
        workflow_name: hookWorkflow,
        secret_header: hookSecret.trim() ? hookSecret.trim() : undefined,
        parameter_mapping: parsedParamMap,
      });
      setIsWebhookModalOpen(false);
      setHookName('');
      setHookSecret('');
      setHookParamMap('{}');
      setSuccessNotice(`Created webhook "${hookName}" successfully`);
      setTimeout(() => setSuccessNotice(null), 3000);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const copyWebhookUrl = (token: string) => {
    const fullUrl = `${window.location.origin}/api/webhooks/${token}`;
    navigator.clipboard.writeText(fullUrl);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  // Format relative time helper
  const formatTime = (isoString?: string | null) => {
    if (!isoString) return 'Never';
    try {
      const date = new Date(isoString);
      return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const activeSchedulesCount = schedules.filter((s) => s.enabled).length;
  const activeWebhooksCount = webhooks.filter((w) => w.enabled).length;
  const totalWebhookTriggers = webhooks.reduce((acc, curr) => acc + (curr.trigger_count || 0), 0);

  return (
    <div className="space-y-6">
      {/* Top Banner / Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Clock className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center space-x-2">
                <span>Automation Hub</span>
                <span className="text-xs font-mono font-medium uppercase px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                  {activeEnvironment.toUpperCase()}
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Trigger workflows via scheduled cron timers or inbound authenticated HTTP webhooks.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="flex items-center space-x-1.5 px-3 py-2 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg transition-colors"
            title="Refresh Automations"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          {subTab === 'schedules' ? (
            <button
              onClick={() => {
                if (workflowList.length > 0 && !schedWorkflow) {
                  setSchedWorkflow(workflowList[0].name);
                }
                setIsScheduleModalOpen(true);
              }}
              className="flex items-center space-x-2 px-4 py-2 text-sm font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-sm shadow-sky-500/20 transition-all"
            >
              <Plus className="h-4 w-4" />
              <span>New Schedule</span>
            </button>
          ) : (
            <button
              onClick={() => {
                if (workflowList.length > 0 && !hookWorkflow) {
                  setHookWorkflow(workflowList[0].name);
                }
                setIsWebhookModalOpen(true);
              }}
              className="flex items-center space-x-2 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-sm shadow-indigo-500/20 transition-all"
            >
              <Plus className="h-4 w-4" />
              <span>New Webhook</span>
            </button>
          )}
        </div>
      </div>

      {/* Metric Cards Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center space-x-4">
          <div className="p-3 rounded-lg bg-sky-500/10 text-sky-400">
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white font-mono">{activeSchedulesCount}</div>
            <div className="text-xs text-slate-400">Active Schedules ({schedules.length} total)</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center space-x-4">
          <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Radio className="h-5 w-5" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white font-mono">{activeWebhooksCount}</div>
            <div className="text-xs text-slate-400">Active Webhooks ({webhooks.length} total)</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center space-x-4">
          <div className="p-3 rounded-lg bg-amber-500/10 text-amber-400">
            <Zap className="h-5 w-5" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white font-mono">{totalWebhookTriggers}</div>
            <div className="text-xs text-slate-400">Total Inbound Triggers</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center space-x-4">
          <div className="p-3 rounded-lg bg-indigo-500/10 text-indigo-400">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-semibold text-white">In-Process Scheduler</div>
            <div className="text-xs text-emerald-400 flex items-center space-x-1 mt-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Loop Active (15s tick)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {successNotice && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm flex items-center space-x-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{successNotice}</span>
        </div>
      )}

      {/* Sub-Tab Navigation Switcher */}
      <div className="flex border-b border-slate-800 space-x-6">
        <button
          onClick={() => setSubTab('schedules')}
          className={`flex items-center space-x-2 pb-3 text-sm font-semibold border-b-2 transition-all ${
            subTab === 'schedules'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Clock className="h-4 w-4" />
          <span>Scheduled Crons</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-xs bg-slate-800 text-slate-300">
            {schedules.length}
          </span>
        </button>

        <button
          onClick={() => setSubTab('webhooks')}
          className={`flex items-center space-x-2 pb-3 text-sm font-semibold border-b-2 transition-all ${
            subTab === 'webhooks'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Radio className="h-4 w-4" />
          <span>Inbound Webhooks</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-xs bg-slate-800 text-slate-300">
            {webhooks.length}
          </span>
        </button>
      </div>

      {/* Sub-Tab 1: SCHEDULES TABLE */}
      {subTab === 'schedules' && (
        <div className="space-y-4">
          {schedules.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-slate-900/30 border border-slate-800/80">
              <Clock className="h-10 w-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-medium text-slate-300">No schedules configured</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
                Automate periodic workflow runs (e.g. nightly checks, hourly cleanups, monitor pings) in{' '}
                {activeEnvironment.toUpperCase()}.
              </p>
              <button
                onClick={() => {
                  if (workflowList.length > 0 && !schedWorkflow) setSchedWorkflow(workflowList[0].name);
                  setIsScheduleModalOpen(true);
                }}
                className="inline-flex items-center space-x-2 px-3.5 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-sm"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Create Schedule</span>
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/40">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-900/60 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Schedule / Workflow</th>
                    <th className="py-3 px-4">Cadence</th>
                    <th className="py-3 px-4">Next Fire</th>
                    <th className="py-3 px-4">Last Run</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                  {schedules.map((sched) => {
                    const isRunning = actionLoadingId === `sched-run-${sched.id}`;
                    const isToggling = actionLoadingId === `sched-toggle-${sched.id}`;

                    return (
                      <tr key={sched.id} className="hover:bg-slate-900/30 transition-colors">
                        <td className="py-3.5 px-4 font-sans">
                          <button
                            onClick={() => handleToggleSchedule(sched)}
                            disabled={isToggling}
                            className={`flex items-center space-x-2 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                              sched.enabled
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20'
                                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700'
                            }`}
                            title={sched.enabled ? 'Click to Pause' : 'Click to Enable'}
                          >
                            <span
                              className={`h-2 w-2 rounded-full ${
                                sched.enabled ? 'bg-emerald-400' : 'bg-slate-500'
                              }`}
                            ></span>
                            <span>{sched.enabled ? 'Active' : 'Paused'}</span>
                          </button>
                        </td>

                        <td className="py-3.5 px-4">
                          <div className="font-sans font-medium text-slate-100 text-sm">
                            {sched.name}
                          </div>
                          <div className="flex items-center space-x-2 mt-0.5">
                            <span className="text-sky-400 font-mono">{sched.workflow_name}</span>
                            <span className="text-[10px] text-slate-500 uppercase px-1 rounded bg-slate-900 border border-slate-800">
                              {sched.environment}
                            </span>
                          </div>
                        </td>

                        <td className="py-3.5 px-4">
                          <div className="inline-block px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-amber-300 font-mono">
                            {sched.cron_expression}
                          </div>
                          {sched.human_description && (
                            <div className="font-sans text-[11px] text-slate-400 mt-1">
                              {sched.human_description}
                            </div>
                          )}
                        </td>

                        <td className="py-3.5 px-4">
                          {sched.enabled && sched.next_run_at ? (
                            <div className="text-slate-300 font-sans">
                              {formatTime(sched.next_run_at)}
                            </div>
                          ) : (
                            <span className="text-slate-500 font-sans italic">Paused</span>
                          )}
                        </td>

                        <td className="py-3.5 px-4">
                          {sched.last_run_at ? (
                            <div>
                              <div className="text-slate-400 font-sans">
                                {formatTime(sched.last_run_at)}
                              </div>
                              {sched.last_status && (
                                <span
                                  className={`inline-block mt-0.5 px-1.5 py-0.2 rounded text-[10px] uppercase font-semibold ${
                                    sched.last_status === 'completed'
                                      ? 'text-emerald-400 bg-emerald-500/10'
                                      : 'text-rose-400 bg-rose-500/10'
                                  }`}
                                >
                                  {sched.last_status}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-500 font-sans">Never run</span>
                          )}
                        </td>

                        <td className="py-3.5 px-4 text-right font-sans">
                          <div className="flex items-center justify-end space-x-2">
                            <button
                              onClick={() => handleRunScheduleNow(sched)}
                              disabled={isRunning}
                              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/20 text-xs font-semibold transition-colors disabled:opacity-50"
                              title="Trigger immediate execution"
                            >
                              <Play className={`h-3 w-3 fill-sky-400 ${isRunning ? 'animate-spin' : ''}`} />
                              <span>Run Now</span>
                            </button>

                            <button
                              onClick={() => handleDeleteSchedule(sched)}
                              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                              title="Delete Schedule"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Sub-Tab 2: WEBHOOKS TABLE */}
      {subTab === 'webhooks' && (
        <div className="space-y-4">
          {webhooks.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-slate-900/30 border border-slate-800/80">
              <Radio className="h-10 w-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-medium text-slate-300">No webhooks configured</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
                Expose secure inbound HTTP endpoints for GitHub Actions, CI/CD pipelines, or third-party webhooks in{' '}
                {activeEnvironment.toUpperCase()}.
              </p>
              <button
                onClick={() => {
                  if (workflowList.length > 0 && !hookWorkflow) setHookWorkflow(workflowList[0].name);
                  setIsWebhookModalOpen(true);
                }}
                className="inline-flex items-center space-x-2 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-sm"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Create Webhook</span>
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/40">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-900/60 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Webhook / Workflow</th>
                    <th className="py-3 px-4">Target Endpoint</th>
                    <th className="py-3 px-4">Authentication</th>
                    <th className="py-3 px-4">Invocations</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                  {webhooks.map((hook) => {
                    const isTesting = actionLoadingId === `hook-test-${hook.id}`;
                    const isToggling = actionLoadingId === `hook-toggle-${hook.id}`;
                    const isCopied = copiedToken === hook.token;
                    const endpointUrl = `${window.location.origin}/api/webhooks/${hook.token}`;

                    return (
                      <tr key={hook.id} className="hover:bg-slate-900/30 transition-colors">
                        <td className="py-3.5 px-4 font-sans">
                          <button
                            onClick={() => handleToggleWebhook(hook)}
                            disabled={isToggling}
                            className={`flex items-center space-x-2 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                              hook.enabled
                                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20'
                                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700'
                            }`}
                            title={hook.enabled ? 'Click to Disable' : 'Click to Enable'}
                          >
                            <span
                              className={`h-2 w-2 rounded-full ${
                                hook.enabled ? 'bg-indigo-400' : 'bg-slate-500'
                              }`}
                            ></span>
                            <span>{hook.enabled ? 'Active' : 'Disabled'}</span>
                          </button>
                        </td>

                        <td className="py-3.5 px-4">
                          <div className="font-sans font-medium text-slate-100 text-sm">
                            {hook.name}
                          </div>
                          <div className="flex items-center space-x-2 mt-0.5">
                            <span className="text-indigo-400 font-mono">{hook.workflow_name}</span>
                            <span className="text-[10px] text-slate-500 uppercase px-1 rounded bg-slate-900 border border-slate-800">
                              {hook.environment}
                            </span>
                          </div>
                        </td>

                        <td className="py-3.5 px-4">
                          <div className="flex items-center space-x-1.5 bg-slate-900/80 border border-slate-800 px-2 py-1 rounded max-w-sm">
                            <span className="text-slate-400 truncate select-all">{endpointUrl}</span>
                            <button
                              onClick={() => copyWebhookUrl(hook.token)}
                              className="text-slate-400 hover:text-slate-200 shrink-0 p-0.5"
                              title="Copy URL"
                            >
                              {isCopied ? (
                                <Check className="h-3.5 w-3.5 text-emerald-400" />
                              ) : (
                                <Copy className="h-3.5 w-3.5" />
                              )}
                            </button>
                          </div>
                        </td>

                        <td className="py-3.5 px-4 font-sans">
                          {hook.has_secret ? (
                            <div className="flex items-center space-x-1 text-emerald-400 text-xs">
                              <ShieldCheck className="h-3.5 w-3.5" />
                              <span>X-Valiant-Secret Protected</span>
                            </div>
                          ) : (
                            <span className="text-slate-500 text-xs">Public Token Only</span>
                          )}
                        </td>

                        <td className="py-3.5 px-4">
                          <div className="text-slate-200 font-bold font-mono">
                            {hook.trigger_count} runs
                          </div>
                          <div className="text-[11px] text-slate-500 font-sans mt-0.5">
                            Last: {formatTime(hook.last_triggered_at)}
                          </div>
                        </td>

                        <td className="py-3.5 px-4 text-right font-sans">
                          <div className="flex items-center justify-end space-x-2">
                            <button
                              onClick={() => handleTestWebhookPing(hook)}
                              disabled={isTesting}
                              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 text-xs font-semibold transition-colors disabled:opacity-50"
                              title="Trigger a test webhook event"
                            >
                              <Zap className={`h-3 w-3 ${isTesting ? 'animate-spin' : ''}`} />
                              <span>Test Ping</span>
                            </button>

                            <button
                              onClick={() => handleDeleteWebhook(hook)}
                              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                              title="Delete Webhook"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* CREATE SCHEDULE MODAL */}
      {isScheduleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
                  <Calendar className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Create Scheduled Cron</h3>
                  <p className="text-xs text-slate-400">
                    Runs in <span className="uppercase text-sky-400 font-mono">{activeEnvironment}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsScheduleModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateScheduleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Schedule Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Nightly Database Cleanup"
                  value={schedName}
                  onChange={(e) => setSchedName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Target Workflow
                </label>
                <select
                  value={schedWorkflow}
                  onChange={(e) => setSchedWorkflow(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
                >
                  {workflowList.map((wf) => (
                    <option key={wf.name} value={wf.name}>
                      {wf.name} — {wf.description}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold uppercase text-slate-400">
                    Cron Cadence (5-field or interval)
                  </label>
                </div>

                {/* Quick Presets */}
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {CRON_PRESETS.map((preset) => (
                    <button
                      type="button"
                      key={preset.label}
                      onClick={() => setSchedCron(preset.expr)}
                      className={`text-[11px] px-2 py-0.5 rounded border transition-colors ${
                        schedCron === preset.expr
                          ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>

                <input
                  type="text"
                  required
                  placeholder="0 * * * * or */15 * * * *"
                  value={schedCron}
                  onChange={(e) => setSchedCron(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 font-mono rounded-lg px-3 py-2 text-sm text-amber-300 focus:outline-none focus:border-sky-500"
                />

                {/* Live validation feedback */}
                {cronValidation && (
                  <div className="mt-2 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                    {cronValidation.valid ? (
                      <div className="space-y-1">
                        <div className="text-emerald-400 flex items-center space-x-1.5">
                          <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                          <span className="font-medium">{cronValidation.human_description}</span>
                        </div>
                        {cronValidation.next_runs && cronValidation.next_runs.length > 0 && (
                          <div className="text-slate-400 font-mono text-[11px] pl-5">
                            Next fire: {formatTime(cronValidation.next_runs[0])}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-rose-400 flex items-center space-x-1.5">
                        <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                        <span>Invalid expression: {cronValidation.error}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Workflow Inputs (JSON Object)
                </label>
                <textarea
                  rows={3}
                  value={schedInputs}
                  onChange={(e) => setSchedInputs(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 font-mono rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-sky-500"
                  placeholder='{ "threshold": 50 }'
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsScheduleModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={cronValidation?.valid === false}
                  className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-sm disabled:opacity-50 transition-all"
                >
                  Create Schedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CREATE WEBHOOK MODAL */}
      {isWebhookModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                  <Radio className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Create Inbound Webhook</h3>
                  <p className="text-xs text-slate-400">
                    Runs in <span className="uppercase text-indigo-400 font-mono">{activeEnvironment}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsWebhookModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateWebhookSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Webhook Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. GitHub Deployment Trigger"
                  value={hookName}
                  onChange={(e) => setHookName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Target Workflow
                </label>
                <select
                  value={hookWorkflow}
                  onChange={(e) => setHookWorkflow(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  {workflowList.map((wf) => (
                    <option key={wf.name} value={wf.name}>
                      {wf.name} — {wf.description}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Optional Secret Token (<span className="text-slate-500 font-mono">X-Valiant-Secret</span> header)
                </label>
                <input
                  type="password"
                  placeholder="Leave empty for token-only auth, or set shared secret"
                  value={hookSecret}
                  onChange={(e) => setHookSecret(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  When set, callers must provide this value in the{' '}
                  <code className="text-slate-400">X-Valiant-Secret</code> HTTP request header.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Parameter Mapping (JSON Object)
                </label>
                <textarea
                  rows={2}
                  value={hookParamMap}
                  onChange={(e) => setHookParamMap(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 font-mono rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
                  placeholder='{ "branch": "ref", "commit": "after" }'
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Optionally map incoming webhook JSON payload keys to workflow input parameters.
                </p>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsWebhookModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-sm transition-all"
                >
                  Generate Webhook
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
