import React, { useState } from 'react';
import { StepSchema, StepResult } from '../types';
import { ContextDiffViewer } from './ContextDiffViewer';
import { DataLineageViewer } from './DataLineageViewer';
import { TabularDataViewer } from './TabularDataViewer';
import {
  X,
  ShieldAlert,
  RotateCcw,
  Sparkles,
  Compass,
  SlidersHorizontal,
  Terminal,
  ArrowRight,
  Code2,
  Database,
  Table,
  Maximize2,
  Minimize2,
} from 'lucide-react';

interface StepDetailDrawerProps {
  step: StepSchema | StepResult | null;
  onClose: () => void;
  onResumeFromStep?: (stepName: string) => void;
  allSteps?: (StepSchema | StepResult)[];
  onSelectStep?: (stepName: string) => void;
  runId?: string;
  env?: string;
}

export const StepDetailDrawer: React.FC<StepDetailDrawerProps> = ({
  step,
  onClose,
  onResumeFromStep,
  allSteps = [],
  onSelectStep,
  runId,
  env,
}) => {
  const urlParams = new URLSearchParams(window.location.search);
  const isResult = step && 'status' in step;
  const result = isResult ? (step as StepResult) : undefined;
  const schema = !isResult ? (step as StepSchema) : undefined;

  const hasTabularData = Boolean(result?.tabular_data);

  const initialDrawerTab = (urlParams.get('drawer_tab') as 'overview' | 'diff' | 'lineage' | 'logs' | 'tabular') || (hasTabularData ? 'tabular' : 'diff');
  const [activeTab, setActiveTab] = useState<'overview' | 'diff' | 'lineage' | 'logs' | 'tabular'>(initialDrawerTab);
  const [isExpanded, setIsExpanded] = useState<boolean>(hasTabularData);

  // Automatically switch to tabular tab when inspected step contains tabular data
  React.useEffect(() => {
    if (hasTabularData) {
      setActiveTab('tabular');
      setIsExpanded(true);
    }
  }, [step?.name, hasTabularData]);

  if (!step) return null;

  const isFailed = result?.status === 'failed';
  const isReused = Boolean(result?.reused);

  const delta = result?.context_delta;
  const addedCount = Object.keys(delta?.added || {}).length;
  const modifiedCount = Object.keys(delta?.modified || {}).length;

  return (
    <div
      className={`absolute top-0 right-0 bottom-0 bg-slate-900/95 backdrop-blur-md border-l border-slate-800 shadow-2xl flex flex-col z-30 animate-fadeIn overflow-hidden transition-all duration-300 ${
        isExpanded || activeTab === 'tabular'
          ? 'w-full sm:w-[680px] lg:w-[860px] xl:w-[960px]'
          : 'w-full sm:w-[480px] lg:w-[540px]'
      }`}
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-950/70 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-500/20 text-sky-400 border border-sky-500/30">
            STEP #{schema?.order ?? result?.order ?? 'INFO'}
          </span>
          <span
            className={`text-xs font-mono font-semibold uppercase ${
              isReused
                ? 'text-cyan-400'
                : result?.status === 'waiting_approval'
                ? 'text-amber-400 animate-pulse font-bold'
                : result?.status === 'rejected'
                ? 'text-rose-500 font-bold'
                : result?.status === 'success'
                ? 'text-emerald-400'
                : isFailed
                ? 'text-rose-400'
                : 'text-slate-400'
            }`}
          >
            {isReused ? 'REUSED (CACHED)' : result ? result.status.replace('_', ' ').toUpperCase() : 'CONFIGURED'}
          </span>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Collapse width' : 'Expand width for data inspection'}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Title & Quick Status Subheader */}
      <div className="px-5 pt-4 pb-3 border-b border-slate-800/60 bg-slate-900/50">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-slate-100">{step.name}</h3>
            {schema?.description && (
              <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{schema.description}</p>
            )}
          </div>
          {result && result.time_taken > 0 && (
            <span className="font-mono text-slate-300 bg-slate-800 px-2 py-0.5 rounded text-xs shrink-0">
              {result.time_taken.toFixed(3)}s
            </span>
          )}
        </div>

        {/* Tab Navigation Ribbon */}
        {result && (
          <div className="flex items-center space-x-1 mt-3 bg-slate-950 p-1 rounded-xl border border-slate-800">
            {hasTabularData && (
              <button
                onClick={() => setActiveTab('tabular')}
                className={`flex-1 flex items-center justify-center space-x-1.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === 'tabular'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Table className="h-3.5 w-3.5 text-emerald-400" />
                <span>Tabular</span>
                {result?.tabular_data?.total_rows !== undefined && (
                  <span className="px-1.5 py-0.2 rounded-full text-[9px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {result.tabular_data.total_rows}
                  </span>
                )}
              </button>
            )}

            <button
              onClick={() => setActiveTab('diff')}
              className={`flex-1 flex items-center justify-center space-x-1.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'diff'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>⚡ Diff</span>
              {(addedCount > 0 || modifiedCount > 0) && (
                <span className="px-1.5 py-0.2 rounded-full text-[9px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  +{addedCount}/~{modifiedCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('lineage')}
              className={`flex-1 flex items-center justify-center space-x-1.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'lineage'
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Compass className="h-3.5 w-3.5" />
              <span>Lineage</span>
            </button>

            <button
              onClick={() => setActiveTab('overview')}
              className={`flex-1 flex items-center justify-center space-x-1.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'overview'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              <span>Overview</span>
            </button>

            <button
              onClick={() => setActiveTab('logs')}
              className={`flex-1 flex items-center justify-center space-x-1.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'logs'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Terminal className="h-3.5 w-3.5" />
              <span>Payload</span>
            </button>
          </div>
        )}
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Smart Resume Action if Failed */}
        {isFailed && onResumeFromStep && (
          <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-800/60 space-y-2.5">
            <div className="flex items-center space-x-2 text-rose-300 text-xs font-semibold">
              <ShieldAlert className="h-4 w-4 text-rose-400" />
              <span>Step Failure Detected</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Skip previously successful steps and resume execution directly from this point.
            </p>
            <button
              onClick={() => onResumeFromStep(step.name)}
              className="w-full py-2 px-3 rounded-lg text-xs font-semibold bg-sky-500 hover:bg-sky-400 text-slate-950 flex items-center justify-center space-x-2 shadow-lg shadow-sky-500/20 transition-all active:scale-[0.98]"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Smart Resume from this Step</span>
            </button>
          </div>
        )}

        {/* Reused Banner */}
        {isReused && (
          <div className="p-3 rounded-xl bg-cyan-950/40 border border-cyan-800/50 text-xs text-cyan-300 flex items-start space-x-2">
            <Sparkles className="h-4 w-4 text-cyan-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-semibold block">Pre-seeded from Parent Run</span>
              <span className="text-[11px] text-cyan-400/80">
                This step was verified in the previous execution. Outputs and context were safely reused without re-running.
              </span>
            </div>
          </div>
        )}

        {/* TAB 0: TABULAR DATA */}
        {activeTab === 'tabular' && result && (
          <div className="h-full">
            <TabularDataViewer
              runId={runId || ''}
              stepName={step.name}
              initialPayload={result.tabular_data}
              env={env}
            />
          </div>
        )}

        {/* TAB 1: CONTEXT DIFF */}
        {activeTab === 'diff' && result && (
          <ContextDiffViewer
            delta={result.context_delta}
            contextBefore={result.context_before}
            contextAfter={result.context_snapshot}
          />
        )}

        {/* TAB 2: DATA LINEAGE */}
        {activeTab === 'lineage' && result && (
          <DataLineageViewer
            currentStep={result}
            allSteps={allSteps.filter((s): s is StepResult => 'status' in s)}
            onSelectStep={onSelectStep}
          />
        )}

        {/* TAB 3: OVERVIEW */}
        {(activeTab === 'overview' || !result) && (
          <div className="space-y-4">
            {/* Approval Breakpoint Status Card */}
            {(schema?.requires_approval || result?.requires_approval) && (
              <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-500/40 space-y-2 text-xs">
                <div className="flex items-center space-x-2 text-amber-300 font-semibold">
                  <ShieldAlert className="h-4 w-4 text-amber-400" />
                  <span>Human-in-the-Loop Breakpoint</span>
                </div>
                {(schema?.approval_prompt || result?.approval_prompt) && (
                  <p className="text-[11px] text-amber-200/90 leading-relaxed font-medium">
                    "{schema?.approval_prompt || result?.approval_prompt}"
                  </p>
                )}
                {result?.approved_by && (
                  <div className="pt-2 border-t border-amber-500/20 text-[11px] space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Decision Operator:</span>
                      <span className="font-mono text-emerald-400 font-bold">{result.approved_by}</span>
                    </div>
                    {result.approved_at && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">Authorized At:</span>
                        <span className="font-mono text-slate-300">{new Date(result.approved_at).toLocaleTimeString()}</span>
                      </div>
                    )}
                    {result.approval_notes && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">Audit Notes:</span>
                        <span className="text-slate-200 italic">{result.approval_notes}</span>
                      </div>
                    )}
                  </div>
                )}
                {result?.status === 'waiting_approval' && (
                  <div className="p-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px]">
                    ⏳ Execution is currently paused at this breakpoint awaiting operator sign-off.
                  </div>
                )}
              </div>
            )}

            {/* Configuration Metadata */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5 text-xs">
              <p className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">
                Configuration & Topology
              </p>

              <div className="flex items-center justify-between">
                <span className="text-slate-400">Parallel Group:</span>
                <span className="font-mono text-slate-200">
                  {schema?.parallel_group || result?.parallel_group ? (
                    <span className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/40">
                      ⚡ {schema?.parallel_group || result?.parallel_group}
                    </span>
                  ) : (
                    'None (Sequential)'
                  )}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-400">Prerequisites (Requires):</span>
                <span className="font-mono text-slate-300">
                  {(schema?.requires || result?.requires || []).length > 0
                    ? `${(schema?.requires || result?.requires || []).length} step(s)`
                    : 'Entry Node (None)'}
                </span>
              </div>

              {(schema?.requires || result?.requires || []).length > 0 && (
                <div className="pt-1.5 space-y-1">
                  {(schema?.requires || result?.requires || []).map((req) => (
                    <div
                      key={req}
                      className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-400 bg-slate-900 px-2 py-1 rounded border border-slate-800"
                    >
                      <ArrowRight className="h-3 w-3 text-sky-400" />
                      <span className="truncate">{req}</span>
                    </div>
                  ))}
                </div>
              )}

              {(schema?.condition || result?.condition) && (
                <div className="flex items-center justify-between pt-1 border-t border-slate-900">
                  <span className="text-slate-400">Execution Condition:</span>
                  <span className="font-mono text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-900/60">
                    {schema?.condition || result?.condition}
                  </span>
                </div>
              )}
            </div>

            {/* Performance Card */}
            {result && (
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <p className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">
                  Execution Metrics & Performance
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-400 block">Duration</span>
                    <span className="font-mono text-slate-100 font-semibold">
                      {result.time_taken ? `${result.time_taken.toFixed(3)}s` : isReused ? '0.000s (Cached)' : '-'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Attempts</span>
                    <span className="font-mono text-slate-100">{result.attempts || 1}</span>
                  </div>
                </div>
                {result.message && (
                  <p className="text-xs text-slate-300 pt-2 border-t border-slate-900 leading-relaxed">
                    {result.message}
                  </p>
                )}
              </div>
            )}

            {/* Metrics */}
            {result?.metrics && Object.keys(result.metrics).length > 0 && (
              <div className="space-y-1.5">
                <p className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">
                  Validation Metrics
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(result.metrics).map(([k, v]) => (
                    <div key={k} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                      <span className="text-slate-400 text-[10px] truncate block font-mono">{k}</span>
                      <span className="font-mono font-bold text-sky-400">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: LOGS & PAYLOAD */}
        {activeTab === 'logs' && result && (
          <div className="space-y-4">
            {/* Error View */}
            {result.error && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/60 text-xs font-mono text-rose-200 space-y-1">
                <div className="flex items-center space-x-1.5 text-rose-300 font-semibold">
                  <ShieldAlert className="h-4 w-4" />
                  <span>Failure Diagnostics:</span>
                </div>
                <pre className="whitespace-pre-wrap max-h-48 overflow-y-auto">{result.error}</pre>
              </div>
            )}

            {/* Step Output Payload */}
            {result.data !== undefined && result.data !== null && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
                  <div className="flex items-center space-x-1.5">
                    <Code2 className="h-3.5 w-3.5 text-sky-400" />
                    <span>Step Output / Payload</span>
                  </div>
                  <button
                    onClick={() => navigator.clipboard.writeText(JSON.stringify(result.data, null, 2))}
                    className="text-[10px] text-sky-400 hover:text-sky-300 font-mono transition-colors"
                  >
                    Copy
                  </button>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-emerald-300 max-h-56 overflow-y-auto">
                  <pre className="whitespace-pre-wrap">{JSON.stringify(result.data, null, 2)}</pre>
                </div>
              </div>
            )}

            {/* Logs View */}
            {result.logs && result.logs.length > 0 && (
              <div className="space-y-1.5">
                <div className="flex items-center space-x-1 text-xs font-semibold text-slate-400">
                  <Terminal className="h-3.5 w-3.5 text-sky-400" />
                  <span>Step Execution Logs ({result.logs.length})</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 max-h-48 overflow-y-auto space-y-1">
                  {result.logs.map((log, i) => (
                    <div key={i}>{log}</div>
                  ))}
                </div>
              </div>
            )}

            {/* Raw Context Snapshot */}
            {result.context_snapshot && Object.keys(result.context_snapshot).length > 0 && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
                  <div className="flex items-center space-x-1.5">
                    <Database className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Complete Context Snapshot</span>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {Object.keys(result.context_snapshot).length} keys
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-indigo-300 max-h-48 overflow-y-auto">
                  <pre className="whitespace-pre-wrap">{JSON.stringify(result.context_snapshot, null, 2)}</pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
