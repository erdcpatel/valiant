import React, { useState, useEffect, useRef } from 'react';
import { WorkflowRun, StepResult, RunEvent } from '../types';
import { StepTimeline } from '../components/StepTimeline';
import { WorkflowDAG } from '../components/WorkflowDAG';
import { subscribeToRunEvents, getRun, cancelRun, resumeRun, approveStep, rejectStep, getRunReportUrl, getRunLogUrl } from '../api';
import {
  RotateCw,
  XCircle,
  StopCircle,
  Terminal,
  Activity,
  ArrowLeft,
  Copy,
  Check,
  Network,
  ListOrdered,
  RotateCcw,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  FileText,
  Download,
} from 'lucide-react';

interface LiveRunPageProps {
  runId: string;
  onBackToWorkflows: () => void;
}

export const LiveRunPage: React.FC<LiveRunPageProps> = ({ runId, onBackToWorkflows }) => {
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [activeStep, setActiveStep] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [copied, setCopied] = useState(false);
  const urlParams = new URLSearchParams(window.location.search);
  const initialViewMode = (urlParams.get('view') as 'dag' | 'timeline') || 'dag';
  const [viewMode, setViewMode] = useState<'dag' | 'timeline'>(initialViewMode);
  const [selectedDagStep, setSelectedDagStep] = useState<string | null>(null);
  const terminalContainerRef = useRef<HTMLDivElement>(null);

  // Initial fetch and WebSocket subscription
  useEffect(() => {
    let isMounted = true;

    // Load initial run snapshot with polling retry
    let retryTimer: any = null;
    const fetchRunSnapshot = (attempt = 1) => {
      getRun(runId)
        .then((data) => {
          if (isMounted) {
            setRun((prev) => {
              if (!prev) return data;
              return {
                ...data,
                steps: data.steps && data.steps.length > 0 ? data.steps : prev.steps,
              };
            });
            const initialLogs: string[] = [];
            data.steps?.forEach((s) => {
              if (s.logs) initialLogs.push(...s.logs);
            });
            if (initialLogs.length > 0) {
              setLogs((prev) => (prev.length === 0 ? initialLogs : prev));
            }
          }
        })
        .catch(() => {
          if (isMounted && attempt < 20) {
            retryTimer = setTimeout(() => fetchRunSnapshot(attempt + 1), 300);
          }
        });
    };
    fetchRunSnapshot();

    // Connect to live WebSocket event stream
    const unsubscribe = subscribeToRunEvents(runId, (event: RunEvent) => {
      const now = new Date().toLocaleTimeString();

      if (event.event_type === 'run_started') {
        setLogs((prev) => [...prev, `[${now}] ▶ Workflow '${event.data.workflow_name}' started`]);
        setRun((prev) => {
          if (prev) {
            return {
              ...prev,
              status: 'running',
              steps: event.data.steps && event.data.steps.length > 0 ? event.data.steps : prev.steps,
            };
          }
          return {
            id: runId,
            workflow_name: event.data.workflow_name || 'Workflow',
            status: 'running',
            success: false,
            parent_run_id: event.data.parent_run_id,
            resumed_from_step: event.data.resumed_from_step,
            steps: event.data.steps || [],
            total_steps: event.data.total_steps || (event.data.steps?.length || 0),
            executed_steps: 0,
            successful_steps: 0,
            failed_steps: 0,
            skipped_steps: 0,
            total_time: 0,
            inputs: event.data.inputs || {},
            context: {},
            started_at: new Date().toISOString(),
          };
        });
      } else if (event.event_type === 'step_started') {
        setActiveStep(event.step_name || null);
        setLogs((prev) => [...prev, `[${now}] ⏳ Step '${event.step_name}' started`]);
        setRun((prev) => {
          if (!prev) {
            return {
              id: runId,
              workflow_name: 'Workflow',
              status: 'running',
              success: false,
              steps: [{ name: event.step_name!, status: 'running', order: 1 } as any],
              total_steps: 1,
              executed_steps: 0,
              successful_steps: 0,
              failed_steps: 0,
              skipped_steps: 0,
              total_time: 0,
              inputs: {},
              context: {},
              started_at: new Date().toISOString(),
            };
          }
          return {
            ...prev,
            steps: prev.steps.map((s) =>
              s.name === event.step_name ? { ...s, status: 'running' } : s
            ),
          };
        });
      } else if (event.event_type === 'step_finished') {
        const stepData = event.data as StepResult;
        setActiveStep(null);
        const icon = stepData.reused ? '⚡' : stepData.success ? '✔' : stepData.skipped ? '⏭' : '✖';
        setLogs((prev) => [
          ...prev,
          `[${now}] ${icon} Step '${event.step_name}' finished: ${stepData.message || stepData.status}`,
        ]);

        setRun((prev) => {
          if (!prev) {
            return {
              id: runId,
              workflow_name: 'Workflow',
              status: 'running',
              success: false,
              steps: [stepData],
              total_steps: 1,
              executed_steps: stepData.executed ? 1 : 0,
              successful_steps: stepData.success ? 1 : 0,
              failed_steps: stepData.status === 'failed' ? 1 : 0,
              skipped_steps: stepData.skipped ? 1 : 0,
              total_time: stepData.time_taken || 0,
              inputs: {},
              context: stepData.context_snapshot || {},
              started_at: new Date().toISOString(),
            };
          }
          const exists = prev.steps.some((s) => s.name === event.step_name);
          const updatedSteps = exists
            ? prev.steps.map((s) => (s.name === event.step_name ? { ...s, ...stepData } : s))
            : [...prev.steps, stepData];

          const successCount = updatedSteps.filter((s) => s.status === 'success').length;
          const failCount = updatedSteps.filter((s) => s.status === 'failed').length;

          return {
            ...prev,
            steps: updatedSteps,
            successful_steps: successCount,
            failed_steps: failCount,
            context: stepData.context_snapshot ? { ...prev.context, ...stepData.context_snapshot } : prev.context,
          };
        });
      } else if (event.event_type === 'run_finished') {
        setActiveStep(null);
        const wfResult = event.data;
        const icon = wfResult.success ? '✔' : '✖';
        setLogs((prev) => [
          ...prev,
          `[${now}] ${icon} Run completed: ${wfResult.status?.toUpperCase() || 'COMPLETED'} (${wfResult.total_time || 0}s)`,
        ]);
        getRun(runId)
          .then((fresh) => setRun(fresh))
          .catch(() => {
            setRun((prev) => (prev ? { ...prev, ...wfResult } : (wfResult as any)));
          });
      } else if (event.event_type === 'step_waiting_approval') {
        setActiveStep(event.step_name || null);
        setLogs((prev) => [
          ...prev,
          `[${now}] 🛡️ Step '${event.step_name}' PAUSED: Operator approval required (${event.data?.approval_prompt || 'Review required'})`,
        ]);
        setRun((prev) => {
          if (!prev) return prev;
          const updated = prev.steps.map((s) =>
            s.name === event.step_name
              ? {
                  ...s,
                  status: 'waiting_approval' as const,
                  requires_approval: true,
                  approval_prompt: event.data?.approval_prompt,
                  message: `Waiting for operator approval: ${event.data?.approval_prompt || ''}`.trim(),
                }
              : s
          );
          return {
            ...prev,
            status: 'waiting_approval' as const,
            steps: updated,
          };
        });
      } else if (event.event_type === 'step_approved') {
        setLogs((prev) => [
          ...prev,
          `[${now}] 🛡️ Step '${event.step_name}' APPROVED by ${event.data?.approved_by || 'operator'}`,
        ]);
        setRun((prev) => {
          if (!prev) return prev;
          const updated = prev.steps.map((s) =>
            s.name === event.step_name
              ? {
                  ...s,
                  status: 'running' as const,
                  approved_by: event.data?.approved_by,
                  approved_at: event.data?.approved_at,
                  approval_notes: event.data?.notes,
                }
              : s
          );
          return {
            ...prev,
            status: 'running' as const,
            steps: updated,
          };
        });
      } else if (event.event_type === 'step_rejected') {
        setActiveStep(null);
        setLogs((prev) => [
          ...prev,
          `[${now}] 🛑 Step '${event.step_name}' REJECTED: ${event.data?.message || 'Aborted by operator'}`,
        ]);
        setRun((prev) => {
          if (!prev) return prev;
          const updated = prev.steps.map((s) =>
            s.name === event.step_name
              ? {
                  ...s,
                  status: 'rejected' as const,
                  approved_by: event.data?.approved_by,
                  approval_notes: event.data?.approval_notes,
                }
              : s
          );
          return {
            ...prev,
            status: 'failed' as const,
            success: false,
            steps: updated,
          };
        });
      } else if (event.event_type === 'step_log') {
        const line = event.data?.line || '';
        if (line) {
          setLogs((prev) => {
            const updated = [...prev, line];
            return updated.length > 2000 ? updated.slice(-2000) : updated;
          });
        }
      } else if (event.event_type === 'run_cancelled') {
        setActiveStep(null);
        setLogs((prev) => [...prev, `[${now}] ⚠ Workflow cancelled by operator`]);
        setRun((prev) => (prev ? { ...prev, status: 'cancelled', success: false } : null));
      }
    });

    return () => {
      isMounted = false;
      if (retryTimer) clearTimeout(retryTimer);
      unsubscribe();
    };
  }, [runId]);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalContainerRef.current) {
      terminalContainerRef.current.scrollTop = terminalContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleCancel = async () => {
    setIsCancelling(true);
    try {
      await cancelRun(runId);
      setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ⚠ Cancellation requested by user`]);
      setRun((prev) => (prev ? { ...prev, status: 'cancelled', success: false } : null));
    } catch (e) {
      console.error(e);
    } finally {
      setIsCancelling(false);
    }
  };

  const handleResume = async (stepName?: string) => {
    if (!run) return;
    setIsResuming(true);
    try {
      const res = await resumeRun(run.id, stepName);
      if (res.run_id) {
        const params = new URLSearchParams(window.location.search);
        params.set('tab', 'live');
        params.set('run_id', res.run_id);
        window.history.pushState({}, '', `${window.location.pathname}?${params.toString()}`);
        window.location.reload();
      }
    } catch (e: any) {
      alert(e.message || 'Failed to resume workflow run');
    } finally {
      setIsResuming(false);
    }
  };

  const handleCopyJson = () => {
    if (run) {
      navigator.clipboard.writeText(JSON.stringify(run, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const [approvalNotes, setApprovalNotes] = useState('');
  const [approverName, setApproverName] = useState('sre_operator');
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  const waitingApprovalStep = run?.steps?.find((s) => s.status === 'waiting_approval');
  const isWaitingApproval = run?.status === 'waiting_approval' || Boolean(waitingApprovalStep);
  const isRunning = (run?.status === 'running' || activeStep !== null) && !isWaitingApproval;
  const isFailed = !isRunning && !isWaitingApproval && (run?.status === 'failed' || (run?.status === 'completed' && !run.success));
  const failedStep = run?.steps?.find((s) => s.status === 'failed' || !s.success);

  const handleApproveStep = async (stepName: string) => {
    setIsApproving(true);
    try {
      await approveStep(runId, stepName, { notes: approvalNotes, approver: approverName }, run?.environment);
      setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] 🛡️ Step '${stepName}' approved by ${approverName}`]);
      const fresh = await getRun(runId, run?.environment);
      setRun(fresh);
    } catch (e: any) {
      alert(e.message || 'Failed to approve step');
    } finally {
      setIsApproving(false);
    }
  };

  const handleRejectStep = async (stepName: string) => {
    setIsRejecting(true);
    try {
      await rejectStep(runId, stepName, { reason: approvalNotes || 'Rejected by operator', approver: approverName }, run?.environment);
      setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] 🛑 Step '${stepName}' rejected by ${approverName}`]);
      const fresh = await getRun(runId, run?.environment);
      setRun(fresh);
    } catch (e: any) {
      alert(e.message || 'Failed to reject step');
    } finally {
      setIsRejecting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <button
            onClick={onBackToWorkflows}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-sm font-bold text-sky-400">{runId}</span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${
                  isWaitingApproval
                    ? 'bg-amber-950/70 text-amber-300 border-amber-500 animate-pulse font-bold'
                    : run?.status === 'completed' && run?.success
                    ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800'
                    : isFailed
                    ? 'bg-rose-950/60 text-rose-400 border-rose-800'
                    : isRunning
                    ? 'bg-sky-950/60 text-sky-400 border-sky-800 animate-pulse'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {isWaitingApproval ? 'WAITING APPROVAL' : run?.status || 'INITIALIZING'}
              </span>
              {run?.environment && (
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase border ${
                    run.environment === 'prod'
                      ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                      : run.environment === 'uat'
                      ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                      : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                  }`}
                >
                  {run.environment}
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold text-slate-100 mt-0.5">
              {run?.workflow_name || 'Loading Workflow...'}
            </h2>

            {/* Parent Run Indicator if Resumed */}
            {run?.parent_run_id && (
              <div className="flex items-center space-x-1.5 text-[11px] font-mono text-cyan-400 mt-1">
                <span className="px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/60 flex items-center space-x-1">
                  <Sparkles className="h-3 w-3" />
                  <span>Resumed from</span>
                  <span
                    className="font-bold underline cursor-pointer hover:text-cyan-300"
                    onClick={() => {
                      const params = new URLSearchParams(window.location.search);
                      params.set('tab', 'live');
                      params.set('run_id', run.parent_run_id!);
                      window.history.pushState({}, '', `${window.location.pathname}?${params.toString()}`);
                      window.location.reload();
                    }}
                  >
                    {run.parent_run_id}
                  </span>
                  {run.resumed_from_step && <span>at "{run.resumed_from_step}"</span>}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          {/* Smart Resume Button if Run Encountered Failure */}
          {isFailed && (
            <button
              onClick={() => handleResume(failedStep?.name)}
              disabled={isResuming}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 shadow-lg shadow-sky-500/30 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
              title="Skip previously completed steps and resume pipeline directly from failure"
            >
              <RotateCcw className={`h-4 w-4 ${isResuming ? 'animate-spin' : ''}`} />
              <span>
                {isResuming
                  ? 'Resuming...'
                  : `Smart Resume from ${failedStep?.name || 'Failure'}`}
              </span>
            </button>
          )}

          {isRunning && (
            <button
              onClick={handleCancel}
              disabled={isCancelling}
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-rose-300 bg-rose-950/60 hover:bg-rose-900/60 border border-rose-800/80 transition-colors disabled:opacity-50"
            >
              <StopCircle className="h-4 w-4" />
              <span>{isCancelling ? 'Cancelling...' : 'Cancel Run'}</span>
            </button>
          )}

          <button
            onClick={handleCopyJson}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-colors"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
            <span>{copied ? 'Copied' : 'Export JSON'}</span>
          </button>

          <div className="inline-flex rounded-xl border border-cyan-800/80 bg-cyan-950/60 shadow-sm overflow-hidden">
            <a
              href={getRunReportUrl(runId, false, run?.environment)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/60 transition-colors"
              title="Open standalone interactive HTML report in a new tab"
            >
              <FileText className="h-4 w-4" />
              <span>HTML Report</span>
            </a>
            <a
              href={getRunReportUrl(runId, true, run?.environment)}
              download={`valiant-report-${runId}-${run?.environment || 'dev'}.html`}
              className="inline-flex items-center px-2.5 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/60 border-l border-cyan-800/60 transition-colors"
              title="Download standalone HTML report file directly to disk"
            >
              <Download className="h-3.5 w-3.5" />
            </a>
          </div>

          {/* Dedicated Per-Run Raw Log File (.log) */}
          <div className="inline-flex rounded-xl border border-slate-700 bg-slate-900 shadow-sm overflow-hidden">
            <a
              href={getRunLogUrl(runId, false, run?.environment)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
              title="View full raw execution log file in a new tab"
            >
              <Terminal className="h-4 w-4 text-emerald-400" />
              <span>Raw Log</span>
            </a>
            <a
              href={getRunLogUrl(runId, true, run?.environment)}
              download={`valiant-run-${runId}-${run?.environment || 'dev'}.log`}
              className="inline-flex items-center px-2.5 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 border-l border-slate-700 transition-colors"
              title="Download full raw execution log (.log) file"
            >
              <Download className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </div>

      {/* Human-in-the-Loop Breakpoint Action Banner */}
      {waitingApprovalStep && (
        <div className="p-5 rounded-2xl bg-amber-950/50 border-2 border-amber-500/70 shadow-2xl shadow-amber-500/25 backdrop-blur-md space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-amber-500/30">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40">
                <ShieldAlert className="h-6 w-6 animate-bounce" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-wider">
                    Breakpoint Action Required
                  </span>
                  <span className="text-xs font-mono text-slate-400">Step: {waitingApprovalStep.name}</span>
                </div>
                <h3 className="text-base font-bold text-amber-100 mt-1">
                  {waitingApprovalStep.approval_prompt || 'Manual Human Approval Gate reached. Authorization required to proceed.'}
                </h3>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-xs text-amber-400 font-mono">Target Env:</span>
              <span className="text-xs font-bold font-mono px-2.5 py-0.5 rounded bg-slate-900 text-amber-300 border border-amber-500/40 uppercase">
                {run?.environment || 'DEV'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">Approver Identity</label>
              <input
                type="text"
                value={approverName}
                onChange={(e) => setApproverName(e.target.value)}
                placeholder="operator / sre_lead"
                className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-amber-400 font-mono"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-[11px] font-medium text-slate-400 mb-1">Decision Justification / Audit Notes</label>
              <input
                type="text"
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="e.g., Verified cloud quota and approved change request CR-8942"
                className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-amber-400"
              />
            </div>
          </div>

          <div className="flex items-center justify-end space-x-3 pt-1">
            <button
              onClick={() => handleRejectStep(waitingApprovalStep.name)}
              disabled={isRejecting || isApproving}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-rose-300 bg-rose-950/70 hover:bg-rose-900/80 border border-rose-800 transition-all flex items-center space-x-1.5 disabled:opacity-50"
            >
              <XCircle className="h-4 w-4" />
              <span>{isRejecting ? 'Rejecting...' : 'Reject & Abort'}</span>
            </button>
            <button
              onClick={() => handleApproveStep(waitingApprovalStep.name)}
              disabled={isRejecting || isApproving}
              className="px-5 py-2 rounded-xl text-xs font-bold text-slate-950 bg-gradient-to-r from-amber-400 to-amber-300 hover:from-amber-300 hover:to-amber-200 shadow-lg shadow-amber-500/30 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center space-x-1.5 disabled:opacity-50"
            >
              <ShieldCheck className="h-4 w-4" />
              <span>{isApproving ? 'Authorizing & Resuming...' : 'Approve & Resume Execution'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Execution View: Pipeline on Left, Terminal on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Step Pipeline */}
        <div className="lg:col-span-8 space-y-4">
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div className="flex items-center space-x-2">
                <Activity className="h-4 w-4 text-sky-400" />
                <h3 className="text-sm font-semibold text-slate-200">Execution Pipeline</h3>
                {run && (
                  <span className="text-xs font-mono text-slate-400 ml-1">
                    ({run.successful_steps}/{run.total_steps} Passed)
                  </span>
                )}
              </div>

              {/* View Toggle */}
              <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => setViewMode('dag')}
                  className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    viewMode === 'dag'
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Network className="h-3.5 w-3.5" />
                  <span>DAG Topology</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('timeline')}
                  className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    viewMode === 'timeline'
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ListOrdered className="h-3.5 w-3.5" />
                  <span>Linear Timeline</span>
                </button>
              </div>
            </div>

            {run?.steps && run.steps.length > 0 ? (
              viewMode === 'dag' ? (
                <WorkflowDAG
                  steps={run.steps}
                  activeStepName={activeStep}
                  onSelectNode={(name) => setSelectedDagStep(name === selectedDagStep ? null : name)}
                  selectedNodeName={selectedDagStep}
                  onResumeFromStep={handleResume}
                  runId={run.id || runId}
                  env={run.environment}
                />
              ) : (
                <StepTimeline
                  steps={run.steps}
                  activeStepName={activeStep}
                  onResumeFromStep={handleResume}
                />
              )
            ) : (
              <div className="py-12 text-center text-slate-500">
                <RotateCw className="h-6 w-6 animate-spin mx-auto mb-2 text-sky-500" />
                <p className="text-sm">Initializing pipeline steps...</p>
              </div>
            )}
          </div>

          {/* Shared Context Box */}
          {run?.context && Object.keys(run.context).length > 0 && (
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Shared Runtime Context
              </h4>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80 font-mono text-xs text-sky-300 max-h-48 overflow-y-auto">
                <pre className="whitespace-pre-wrap">{JSON.stringify(run.context, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>

        {/* Right: Real-time Terminal */}
        <div className="lg:col-span-4 space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 flex flex-col h-[640px] overflow-hidden shadow-xl">
            <div className="px-4 py-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Terminal className="h-4 w-4 text-emerald-400" />
                <span className="text-xs font-mono font-semibold text-slate-200">
                  Console Output Stream
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-500">{logs.length} lines</span>
            </div>

            <div
              ref={terminalContainerRef}
              className="flex-1 p-4 font-mono text-xs overflow-y-auto space-y-1.5 text-slate-300 selection:bg-sky-500 selection:text-white"
            >
              {logs.length === 0 ? (
                <p className="text-slate-600 italic">Waiting for execution logs...</p>
              ) : (
                logs.map((log, index) => {
                  let colorClass = 'text-slate-300';
                  if (log.includes('✔') || log.includes('Success')) colorClass = 'text-emerald-400';
                  if (log.includes('✖') || log.includes('Error') || log.includes('Failure'))
                    colorClass = 'text-rose-400 font-semibold';
                  if (log.includes('⏳') || log.includes('started')) colorClass = 'text-sky-300';
                  if (log.includes('⚠') || log.includes('Cancelled')) colorClass = 'text-amber-400';
                  if (log.includes('⚡') || log.includes('Reused')) colorClass = 'text-cyan-300 font-semibold';

                  return (
                    <div key={index} className={`leading-relaxed break-all ${colorClass}`}>
                      {log}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
