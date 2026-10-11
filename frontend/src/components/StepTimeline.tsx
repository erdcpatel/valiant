import React, { useState, useMemo } from 'react';
import { StepResult } from '../types';
import { ContextDiffViewer } from './ContextDiffViewer';
import { DataLineageViewer } from './DataLineageViewer';
import {
  CheckCircle2,
  XCircle,
  Clock,
  RotateCw,
  FastForward,
  ChevronDown,
  ChevronRight,
  Activity,
  Terminal,
  Code2,
  Search,
  RotateCcw,
  Sparkles,
  Compass,
  ChevronsUpDown,
  ShieldAlert,
} from 'lucide-react';

interface StepTimelineProps {
  steps: StepResult[];
  activeStepName?: string | null;
  onResumeFromStep?: (stepName: string) => void;
}

export const StepTimeline: React.FC<StepTimelineProps> = ({ steps, activeStepName, onResumeFromStep }) => {
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});
  const [stepTabs, setStepTabs] = useState<Record<string, 'diff' | 'lineage' | 'payload'>>({});
  const [stepSearch, setStepSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  // Extract all unique categories/tags across steps
  const allTags = useMemo(() => {
    const tagsSet = new Set<string>();
    steps.forEach((s) => s.tags?.forEach((t) => tagsSet.add(t)));
    return Array.from(tagsSet);
  }, [steps]);

  // Filter steps by category and search
  const filteredSteps = useMemo(() => {
    return steps.filter((step) => {
      const matchesSearch =
        stepSearch === '' ||
        step.name.toLowerCase().includes(stepSearch.toLowerCase()) ||
        (step.message && step.message.toLowerCase().includes(stepSearch.toLowerCase()));
      const matchesTag = !categoryFilter || step.tags?.includes(categoryFilter);
      return matchesSearch && matchesTag;
    });
  }, [steps, stepSearch, categoryFilter]);

  const toggleExpand = (stepName: string) => {
    setExpandedSteps((prev) => ({ ...prev, [stepName]: !prev[stepName] }));
  };

  const expandAll = () => {
    const all: Record<string, boolean> = {};
    steps.forEach((s) => (all[s.name] = true));
    setExpandedSteps(all);
  };

  const collapseAll = () => {
    setExpandedSteps({});
  };

  const allExpanded = steps.length > 0 && steps.every((s) => !!expandedSteps[s.name]);

  const getStatusIcon = (step: StepResult) => {
    if (step.reused) {
      return <Sparkles className="h-5 w-5 text-cyan-400" />;
    }
    if (step.status === 'waiting_approval') {
      return <ShieldAlert className="h-5 w-5 text-amber-400 animate-bounce" />;
    }
    if (step.status === 'rejected') {
      return <XCircle className="h-5 w-5 text-rose-500" />;
    }
    if (step.name === activeStepName || step.status === 'running') {
      return <RotateCw className="h-5 w-5 text-sky-400 animate-spin" />;
    }
    if (step.status === 'success') {
      return <CheckCircle2 className="h-5 w-5 text-emerald-400" />;
    }
    if (step.status === 'failed') {
      return <XCircle className="h-5 w-5 text-rose-400" />;
    }
    if (step.status === 'skipped') {
      return <FastForward className="h-5 w-5 text-amber-400" />;
    }
    return <Clock className="h-5 w-5 text-slate-600" />;
  };

  const getBorderColor = (step: StepResult) => {
    if (step.reused) {
      return 'border-cyan-500/40 bg-cyan-950/15 hover:border-cyan-500/60';
    }
    if (step.status === 'waiting_approval') {
      return 'border-amber-400 ring-1 ring-amber-400/40 shadow-lg shadow-amber-500/25 bg-amber-950/25 animate-pulse';
    }
    if (step.status === 'rejected') {
      return 'border-rose-500/50 bg-rose-950/20 hover:border-rose-500/70';
    }
    if (step.name === activeStepName || step.status === 'running') {
      return 'border-sky-500 shadow-md shadow-sky-500/20 bg-sky-950/20';
    }
    if (step.status === 'success') {
      return 'border-emerald-500/30 bg-emerald-950/10 hover:border-emerald-500/50';
    }
    if (step.status === 'failed') {
      return 'border-rose-500/40 bg-rose-950/15 hover:border-rose-500/60';
    }
    if (step.status === 'skipped') {
      return 'border-slate-800 bg-slate-900/30 opacity-75';
    }
    return 'border-slate-800/80 bg-slate-900/20';
  };

  return (
    <div className="space-y-4">
      {/* Category filter & Step Search Controls (Essential for 20-30 step workflows) */}
      {steps.length > 3 && (
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder={`Search across ${steps.length} steps...`}
                value={stepSearch}
                onChange={(e) => setStepSearch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
              />
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={allExpanded ? collapseAll : expandAll}
                className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-colors whitespace-nowrap"
              >
                <ChevronsUpDown className="h-3.5 w-3.5 text-sky-400" />
                <span>{allExpanded ? 'Collapse All' : 'Expand All'}</span>
              </button>
            </div>
          </div>

          {allTags.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-slate-900">
              <span className="text-[10px] font-mono text-slate-500 uppercase mr-1">Categories:</span>
              <button
                type="button"
                onClick={() => setCategoryFilter(null)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                  categoryFilter === null
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                    : 'bg-slate-900 text-slate-400 border border-slate-800/80 hover:text-slate-200'
                }`}
              >
                All ({steps.length})
              </button>
              {allTags.map((tag) => {
                const count = steps.filter((s) => s.tags?.includes(tag)).length;
                return (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => setCategoryFilter(categoryFilter === tag ? null : tag)}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                      categoryFilter === tag
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                        : 'bg-slate-900 text-slate-400 border border-slate-800/80 hover:text-slate-200'
                    }`}
                  >
                    #{tag} ({count})
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Steps Pipeline Timeline */}
      <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
        {filteredSteps.length === 0 ? (
          <div className="p-6 text-center text-slate-500 bg-slate-900/30 rounded-xl border border-slate-800/50">
            <p className="text-xs">No steps match the filter criteria</p>
          </div>
        ) : (
          filteredSteps.map((step, idx) => {
            const isExpanded = !!expandedSteps[step.name];
            const isRunning = step.name === activeStepName || step.status === 'running';

          return (
            <div key={step.name || idx} className="relative group">
              {/* Timeline Indicator Dot */}
              <div className="absolute -left-6 top-3.5 -translate-x-1/2 flex items-center justify-center bg-slate-950 p-1">
                {getStatusIcon(step)}
              </div>

              {/* Step Card */}
              <div
                className={`border rounded-xl p-4 transition-all ${getBorderColor(step)} cursor-pointer`}
                onClick={() => toggleExpand(step.name)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-xs font-mono font-semibold text-slate-500">
                      #{idx + 1}
                    </span>
                    <h4 className="text-sm font-semibold text-slate-100 flex items-center space-x-2">
                      <span>{step.name}</span>
                      {step.reused && (
                        <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                          ⚡ Reused (Skipped)
                        </span>
                      )}
                      {isRunning && (
                        <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded-full bg-sky-500/20 text-sky-400 animate-pulse">
                          Running
                        </span>
                      )}
                      {step.context_delta && (Object.keys(step.context_delta.added || {}).length > 0 || Object.keys(step.context_delta.modified || {}).length > 0) && (
                        <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold rounded bg-slate-950 text-slate-300 border border-slate-800">
                          {Object.keys(step.context_delta.added || {}).length > 0 && <span className="text-emerald-400">+{Object.keys(step.context_delta.added || {}).length} </span>}
                          {Object.keys(step.context_delta.modified || {}).length > 0 && <span className="text-amber-400">~{Object.keys(step.context_delta.modified || {}).length}</span>}
                        </span>
                      )}
                    </h4>
                  </div>

                  <div className="flex items-center space-x-2 text-xs">
                    {step.status === 'failed' && onResumeFromStep && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onResumeFromStep(step.name);
                        }}
                        className="px-2 py-1 rounded-lg text-xs font-semibold bg-sky-500 hover:bg-sky-400 text-slate-950 flex items-center space-x-1 shadow-sm transition-all active:scale-95 mr-1"
                        title={`Resume workflow from ${step.name}`}
                      >
                        <RotateCcw className="h-3 w-3" />
                        <span>Resume from Here</span>
                      </button>
                    )}
                    {step.time_taken > 0 ? (
                      <span className="font-mono text-slate-400 bg-slate-800/60 px-2 py-0.5 rounded">
                        {step.time_taken.toFixed(2)}s
                      </span>
                    ) : step.reused ? (
                      <span className="font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-900/60 text-[10px]">
                        0.00s (Cached)
                      </span>
                    ) : null}
                    {step.attempts > 1 && (
                      <span className="text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        {step.attempts} attempts
                      </span>
                    )}
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-slate-400" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-slate-400" />
                    )}
                  </div>
                </div>

                {/* Short message snippet */}
                {step.message && (
                  <p className="mt-2 text-xs text-slate-400 line-clamp-1">
                    {step.message}
                  </p>
                )}

                {/* Metrics Badges */}
                {step.metrics && Object.keys(step.metrics).length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {Object.entries(step.metrics).map(([k, v]) => (
                      <span
                        key={k}
                        className="inline-flex items-center space-x-1 text-[11px] font-mono px-2 py-0.5 rounded bg-sky-950/60 border border-sky-800/40 text-sky-300"
                      >
                        <Activity className="h-3 w-3 text-sky-400" />
                        <span>{k}:</span>
                        <span className="font-semibold text-white">{String(v)}</span>
                      </span>
                    ))}
                  </div>
                )}

                {/* Expanded Details Pane */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-slate-800 space-y-4" onClick={(e) => e.stopPropagation()}>
                    {/* Sub-tab Switcher */}
                    <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                      <button
                        type="button"
                        onClick={() => setStepTabs((prev) => ({ ...prev, [step.name]: 'diff' }))}
                        className={`flex-1 py-1 rounded text-xs font-medium transition-colors ${
                          (stepTabs[step.name] || 'diff') === 'diff'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        ⚡ Context Diff
                      </button>
                      <button
                        type="button"
                        onClick={() => setStepTabs((prev) => ({ ...prev, [step.name]: 'lineage' }))}
                        className={`flex-1 py-1 rounded text-xs font-medium transition-colors flex items-center justify-center space-x-1 ${
                          stepTabs[step.name] === 'lineage'
                            ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        <Compass className="h-3 w-3" />
                        <span>Data Lineage</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setStepTabs((prev) => ({ ...prev, [step.name]: 'payload' }))}
                        className={`flex-1 py-1 rounded text-xs font-medium transition-colors flex items-center justify-center space-x-1 ${
                          stepTabs[step.name] === 'payload'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        <Terminal className="h-3 w-3" />
                        <span>Logs & Payload</span>
                      </button>
                    </div>

                    {(stepTabs[step.name] || 'diff') === 'diff' && (
                      <ContextDiffViewer
                        delta={step.context_delta}
                        contextBefore={step.context_before}
                        contextAfter={step.context_snapshot}
                      />
                    )}

                    {stepTabs[step.name] === 'lineage' && (
                      <DataLineageViewer
                        currentStep={step}
                        allSteps={steps}
                      />
                    )}

                    {stepTabs[step.name] === 'payload' && (
                      <div className="space-y-3">
                        {step.error && (
                          <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/50 text-xs font-mono text-rose-200 overflow-x-auto">
                            <p className="font-semibold mb-1 text-rose-300">Error Details:</p>
                            <pre className="whitespace-pre-wrap">{step.error}</pre>
                          </div>
                        )}

                        {step.logs && step.logs.length > 0 && (
                          <div className="space-y-1">
                            <div className="flex items-center space-x-1 text-xs font-semibold text-slate-400">
                              <Terminal className="h-3.5 w-3.5" />
                              <span>Execution Logs</span>
                            </div>
                            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 max-h-48 overflow-y-auto space-y-1">
                              {step.logs.map((log, i) => (
                                <div key={i}>{log}</div>
                              ))}
                            </div>
                          </div>
                        )}

                        {step.data !== undefined && step.data !== null && (
                          <div className="space-y-1">
                            <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
                              <div className="flex items-center space-x-1.5">
                                <Code2 className="h-3.5 w-3.5 text-sky-400" />
                                <span>Step Output / Payload</span>
                              </div>
                              <button
                                onClick={() => navigator.clipboard.writeText(JSON.stringify(step.data, null, 2))}
                                className="text-[10px] text-sky-400 hover:text-sky-300 font-mono transition-colors"
                              >
                                Copy Payload
                              </button>
                            </div>
                            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-emerald-300 max-h-60 overflow-y-auto">
                              <pre className="whitespace-pre-wrap">{JSON.stringify(step.data, null, 2)}</pre>
                            </div>
                          </div>
                        )}

                        {step.tags && step.tags.length > 0 && (
                          <div className="flex items-center space-x-1.5 text-xs text-slate-500">
                            <span>Tags:</span>
                            {step.tags.map((t) => (
                              <span key={t} className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 text-[10px]">
                                #{t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        }))}
      </div>
    </div>
  );
};
