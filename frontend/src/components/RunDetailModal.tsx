import React, { useState } from 'react';
import { WorkflowRun } from '../types';
import { StepTimeline } from './StepTimeline';
import { WorkflowDAG } from './WorkflowDAG';
import { getRunReportUrl, getRunLogUrl } from '../api';
import {
  X,
  Copy,
  Check,
  Download,
  Activity,
  Layers,
  Network,
  ListOrdered,
  RotateCcw,
  Sparkles,
  ArrowRightLeft,
  FileText,
  Terminal,
} from 'lucide-react';

interface RunDetailModalProps {
  run: WorkflowRun | null;
  onClose: () => void;
  onResumeRun?: (runId: string, fromStep?: string) => void;
  onOpenComparator?: (runId: string, env?: string) => void;
}

export const RunDetailModal: React.FC<RunDetailModalProps> = ({
  run,
  onClose,
  onResumeRun,
  onOpenComparator,
}) => {
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState<'dag' | 'timeline'>('dag');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  if (!run) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(run, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(run, null, 2));
    const dl = document.createElement('a');
    dl.setAttribute('href', dataStr);
    dl.setAttribute('download', `${run.id}_summary.json`);
    dl.click();
  };

  const isFailed = run.status === 'failed' || !run.success;
  const failedStep = run.steps?.find((s) => s.status === 'failed' || !s.success);

  const handleResume = (stepName?: string) => {
    if (onResumeRun) {
      onClose();
      onResumeRun(run.id, stepName || failedStep?.name);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className={`relative w-full transition-all duration-300 max-h-[92vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden ${
        viewMode === 'dag' ? 'max-w-7xl 2xl:max-w-[92vw]' : 'max-w-4xl'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div>
            <div className="flex items-center space-x-3">
              <span className="font-mono text-sm font-bold text-sky-400">{run.id}</span>
              <span
                className={`px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full border ${
                  run.status === 'waiting_approval'
                    ? 'bg-amber-950/70 text-amber-300 border-amber-500 font-bold animate-pulse'
                    : run.success
                    ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800'
                    : 'bg-rose-950/60 text-rose-400 border-rose-800'
                }`}
              >
                {run.status}
              </span>
              {run.environment && (
                <span
                  className={`px-2 py-0.5 text-[10px] font-mono font-semibold uppercase rounded-full border ${
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
              <span className="px-2 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800/80 rounded-full border border-slate-700/60">
                by {run.triggered_by || 'anonymous'}
              </span>
              {run.parent_run_id && (
                <span className="px-2 py-0.5 text-[10px] font-mono text-cyan-300 bg-cyan-950/60 rounded-full border border-cyan-800/60 flex items-center space-x-1">
                  <Sparkles className="h-3 w-3" />
                  <span>Resumed from {run.parent_run_id}</span>
                </span>
              )}
            </div>
            <h3 className="text-base font-bold text-slate-100 mt-1">{run.workflow_name}</h3>
          </div>

          <div className="flex items-center space-x-2">
            {/* Smart Resume Button */}
            {isFailed && onResumeRun && (
              <button
                onClick={() => handleResume(failedStep?.name)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 shadow-md shadow-sky-500/20 transition-all hover:scale-105 active:scale-95"
                title={`Smart resume from ${failedStep?.name || 'failure'}`}
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Smart Resume</span>
              </button>
            )}

            {/* Compare Button */}
            {onOpenComparator && (
              <button
                onClick={() => {
                  onClose();
                  onOpenComparator(run.id, run.environment);
                }}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white border border-slate-700 transition-colors"
                title="Compare this run against another execution"
              >
                <ArrowRightLeft className="h-3.5 w-3.5 text-sky-400" />
                <span>Compare</span>
              </button>
            )}

            <div className="inline-flex rounded-lg border border-cyan-800/80 bg-cyan-950/60 overflow-hidden text-xs">
              <a
                href={getRunReportUrl(run.id, false, run.environment)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-1 px-2.5 py-1.5 font-semibold text-cyan-300 hover:bg-cyan-900/60 transition-colors"
                title="Open standalone interactive HTML report in a new tab"
              >
                <FileText className="h-3.5 w-3.5" />
                <span>Report</span>
              </a>
              <a
                href={getRunReportUrl(run.id, true, run.environment)}
                download={`valiant-report-${run.id}-${run.environment || 'dev'}.html`}
                className="inline-flex items-center px-2 py-1.5 text-cyan-300 hover:bg-cyan-900/60 border-l border-cyan-800/60 transition-colors"
                title="Download standalone HTML report file directly to disk"
              >
                <Download className="h-3 w-3" />
              </a>
            </div>

            {/* Dedicated Per-Run Raw Log File (.log) */}
            <div className="inline-flex rounded-lg border border-slate-700 bg-slate-900 overflow-hidden text-xs">
              <a
                href={getRunLogUrl(run.id, false, run.environment)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-1 px-2.5 py-1.5 font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
                title="View full raw execution log file in a new tab"
              >
                <Terminal className="h-3.5 w-3.5 text-emerald-400" />
                <span>Log</span>
              </a>
              <a
                href={getRunLogUrl(run.id, true, run.environment)}
                download={`valiant-run-${run.id}-${run.environment || 'dev'}.log`}
                className="inline-flex items-center px-2 py-1.5 text-slate-300 hover:bg-slate-800 border-l border-slate-700 transition-colors"
                title="Download full raw execution log (.log) file"
              >
                <Download className="h-3 w-3" />
              </a>
            </div>

            <button
              onClick={handleCopy}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
              title="Copy JSON"
            >
              {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
            </button>
            <button
              onClick={handleDownload}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
              title="Download JSON Report"
            >
              <Download className="h-4 w-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Metadata Summary Banner */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-950/50 border border-slate-800/80">
            <div>
              <p className="text-[11px] font-medium text-slate-400">Total Steps</p>
              <p className="text-lg font-bold text-slate-100">{run.total_steps}</p>
            </div>
            <div>
              <p className="text-[11px] font-medium text-slate-400">Passed / Failed</p>
              <p className="text-lg font-bold text-slate-100">
                <span className="text-emerald-400">{run.successful_steps}</span> /{' '}
                <span className="text-rose-400">{run.failed_steps}</span>
              </p>
            </div>
            <div>
              <p className="text-[11px] font-medium text-slate-400">Duration</p>
              <p className="text-lg font-bold text-slate-100 font-mono">
                {run.total_time ? `${run.total_time.toFixed(2)}s` : '-'}
              </p>
            </div>
            <div>
              <p className="text-[11px] font-medium text-slate-400">Started</p>
              <p className="text-sm font-semibold text-slate-200 font-mono mt-0.5">
                {run.started_at ? new Date(run.started_at).toLocaleTimeString() : '-'}
              </p>
            </div>
          </div>

          {/* Workflow Inputs */}
          {run.inputs && Object.keys(run.inputs).length > 0 && (
            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Execution Input Parameters
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                {Object.entries(run.inputs).map(([k, v]) => (
                  <div key={k} className="p-2 rounded bg-slate-900 border border-slate-800/80 flex items-center justify-between">
                    <span className="text-slate-400">{k}:</span>
                    <span className="text-slate-200 font-medium truncate max-w-[200px]">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Visual Execution Pipeline Tabs */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Activity className="h-4 w-4 text-sky-400" />
                <h4 className="text-sm font-semibold text-slate-200">Execution Pipeline Topology</h4>
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
                  <span>Interactive DAG</span>
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

            {viewMode === 'dag' ? (
              <WorkflowDAG
                steps={run.steps}
                onSelectNode={(name) => setSelectedNode(name === selectedNode ? null : name)}
                selectedNodeName={selectedNode}
                onResumeFromStep={handleResume}
                runId={run.id}
                env={run.environment}
              />
            ) : (
              <StepTimeline
                steps={run.steps}
                onResumeFromStep={handleResume}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
