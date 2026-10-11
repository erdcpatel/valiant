import React, { useState, useEffect } from 'react';
import { WorkflowRun, RunComparisonResult, StepComparison } from '../types';
import { compareRuns, getRuns } from '../api';
import {
  X,
  ArrowRightLeft,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Layers,
  Sparkles,
  Zap,
  TrendingDown,
  TrendingUp,
  RotateCw,
  ChevronDown,
  ChevronUp,
  FileText,
} from 'lucide-react';

interface RunComparatorModalProps {
  runAId: string;
  runBId: string;
  envA?: string;
  envB?: string;
  availableRuns?: WorkflowRun[];
  onClose: () => void;
  onSelectRunDetail?: (run: WorkflowRun) => void;
}

export const RunComparatorModal: React.FC<RunComparatorModalProps> = ({
  runAId: initialRunAId,
  runBId: initialRunBId,
  envA: initialEnvA = 'dev',
  envB: initialEnvB = 'dev',
  availableRuns = [],
  onClose,
  onSelectRunDetail,
}) => {
  const [runAId, setRunAId] = useState(initialRunAId);
  const [runBId, setRunBId] = useState(initialRunBId);
  const [envA, setEnvA] = useState(initialEnvA);
  const [envB, setEnvB] = useState(initialEnvB);

  const [runsA, setRunsA] = useState<WorkflowRun[]>(availableRuns);
  const [runsB, setRunsB] = useState<WorkflowRun[]>(availableRuns);

  const urlParams = new URLSearchParams(window.location.search);
  const initialDiffTab = (urlParams.get('diff_tab') as 'matrix' | 'context' | 'meta') || 'matrix';
  const [activeTab, setActiveTab] = useState<'matrix' | 'context' | 'meta'>(initialDiffTab);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<RunComparisonResult | null>(null);
  const [expandedErrors, setExpandedErrors] = useState<Record<string, boolean>>({});

  // Fetch runs for Environment A when envA changes
  useEffect(() => {
    getRuns(50, undefined, undefined, envA)
      .then((data) => {
        setRunsA(data);
        if (data.length > 0 && (!runAId || !data.some((r) => r.id === runAId))) {
          setRunAId(data[0].id);
        }
      })
      .catch(console.error);
  }, [envA]);

  // Fetch runs for Environment B when envB changes
  useEffect(() => {
    getRuns(50, undefined, undefined, envB)
      .then((data) => {
        setRunsB(data);
        if (data.length > 0 && (!runBId || !data.some((r) => r.id === runBId))) {
          if (envA === envB && data.length > 1 && data[0].id === runAId) {
            setRunBId(data[1].id);
          } else {
            setRunBId(data[0].id);
          }
        }
      })
      .catch(console.error);
  }, [envB]);

  const loadComparison = async (aId: string, bId: string, eA: string, eB: string) => {
    if (!aId || !bId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await compareRuns(aId, bId, eA, eB);
      setComparison(data);
    } catch (err: any) {
      setError(err.message || 'Failed to compare runs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (runAId && runBId) {
      loadComparison(runAId, runBId, envA, envB);
    }
  }, [runAId, runBId, envA, envB]);

  const handleSwap = () => {
    const nextA = runBId;
    const nextB = runAId;
    const nextEnvA = envB;
    const nextEnvB = envA;
    setRunAId(nextA);
    setRunBId(nextB);
    setEnvA(nextEnvA);
    setEnvB(nextEnvB);
  };

  const toggleError = (stepName: string) => {
    setExpandedErrors((prev) => ({ ...prev, [stepName]: !prev[stepName] }));
  };

  const summary = comparison?.summary;
  const isRegression = summary?.outcome === 'regression' || (summary?.regressed_steps_count ?? 0) > 0;
  const isImproved = summary?.outcome === 'improved';
  const isSlower = (summary?.time_delta ?? 0) > 0.1 && (summary?.time_ratio ?? 1) > 1.2;
  const isFaster = (summary?.time_delta ?? 0) < -0.1 && (summary?.time_ratio ?? 1) < 0.8;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-6xl max-h-[92vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/70 gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <ArrowRightLeft className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base font-semibold text-slate-100">Run Comparator & Regression Diff</h2>
                {summary && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                    {summary.workflow_name}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Compare baseline vs target execution latency, step status changes, and data drift.
              </p>
            </div>
          </div>

          {/* Quick Selectors & Close */}
          <div className="flex items-center space-x-2 w-full sm:w-auto justify-between sm:justify-end">
            <button
              onClick={handleSwap}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs flex items-center space-x-1.5 transition-colors"
              title="Swap Baseline and Target"
            >
              <ArrowRightLeft className="h-3.5 w-3.5" />
              <span className="hidden md:inline">Swap</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Run Selector Bar with Cross-Environment Pickers */}
        <div className="px-6 py-3 bg-slate-950/40 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-4 text-xs">
          {/* Baseline (Run A) */}
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-sky-400 uppercase tracking-wider text-[11px]">Baseline (A):</span>
            <select
              value={envA}
              onChange={(e) => setEnvA(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs font-mono font-bold text-emerald-400 focus:outline-none focus:border-sky-500 uppercase"
              title="Select Baseline Environment"
            >
              <option value="dev">DEV</option>
              <option value="uat">UAT</option>
              <option value="prod">PROD</option>
            </select>
            {runsA.length > 0 ? (
              <select
                value={runAId}
                onChange={(e) => setRunAId(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-sky-500 max-w-[280px] truncate"
              >
                {runsA.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id} ({r.workflow_name} • {r.status} • {r.total_time?.toFixed(2)}s)
                  </option>
                ))}
              </select>
            ) : (
              <span className="font-mono text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                No runs in {envA.toUpperCase()}
              </span>
            )}
          </div>

          <div className="text-slate-500 font-bold hidden sm:inline">⇄</div>

          {/* Target (Run B) */}
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-purple-400 uppercase tracking-wider text-[11px]">Target (B):</span>
            <select
              value={envB}
              onChange={(e) => setEnvB(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs font-mono font-bold text-purple-400 focus:outline-none focus:border-purple-500 uppercase"
              title="Select Target Environment"
            >
              <option value="dev">DEV</option>
              <option value="uat">UAT</option>
              <option value="prod">PROD</option>
            </select>
            {runsB.length > 0 ? (
              <select
                value={runBId}
                onChange={(e) => setRunBId(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-purple-500 max-w-[280px] truncate"
              >
                {runsB.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id} ({r.workflow_name} • {r.status} • {r.total_time?.toFixed(2)}s)
                  </option>
                ))}
              </select>
            ) : (
              <span className="font-mono text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                No runs in {envB.toUpperCase()}
              </span>
            )}
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-3">
              <RotateCw className="h-8 w-8 text-sky-400 animate-spin" />
              <p className="text-sm text-slate-400">Comparing execution profiles and computing diff matrix...</p>
            </div>
          ) : error ? (
            <div className="p-6 rounded-xl bg-rose-950/30 border border-rose-800 text-rose-300 text-center space-y-2">
              <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto" />
              <div className="font-semibold">Unable to compare runs</div>
              <p className="text-xs text-rose-400/80">{error}</p>
            </div>
          ) : comparison && summary ? (
            <>
              {/* Macro Verdict Summary Cards (3-Second Root-Cause Diagnosis) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* 1. Verdict Card */}
                <div
                  className={`p-4 rounded-xl border flex flex-col justify-between ${
                    isRegression
                      ? 'bg-rose-950/20 border-rose-800/60'
                      : isImproved
                      ? 'bg-emerald-950/20 border-emerald-800/60'
                      : 'bg-slate-950/40 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                      Outcome Verdict
                    </span>
                    {isRegression ? (
                      <XCircle className="h-4 w-4 text-rose-400" />
                    ) : isImproved ? (
                      <Sparkles className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    )}
                  </div>
                  <div className="mt-2">
                    <div
                      className={`text-base font-bold ${
                        isRegression
                          ? 'text-rose-400'
                          : isImproved
                          ? 'text-emerald-400'
                          : 'text-slate-200'
                      }`}
                    >
                      {isRegression
                        ? 'Regression Detected'
                        : isImproved
                        ? 'Target Run Improved'
                        : 'Matching Outcomes'}
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      {isRegression
                        ? `${summary.regressed_steps_count} step(s) failed in target that passed in baseline.`
                        : isImproved
                        ? 'Target run succeeded where baseline had failed.'
                        : 'Both executions reached the same macro completion state.'}
                    </p>
                  </div>
                </div>

                {/* 2. Latency Drift Card */}
                <div className="p-4 rounded-xl border bg-slate-950/40 border-slate-800 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                      Execution Time Drift
                    </span>
                    <Clock className="h-4 w-4 text-sky-400" />
                  </div>
                  <div className="mt-2">
                    <div className="flex items-baseline space-x-2">
                      <span className="text-xl font-bold font-mono text-slate-100">
                        {summary.time_b.toFixed(2)}s
                      </span>
                      <span className="text-xs font-mono text-slate-500">
                        vs {summary.time_a.toFixed(2)}s baseline
                      </span>
                    </div>
                    <div className="flex items-center space-x-2 mt-1">
                      <span
                        className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold ${
                          summary.time_delta > 0.05
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : summary.time_delta < -0.05
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {summary.time_delta > 0 ? (
                          <TrendingUp className="h-3 w-3" />
                        ) : summary.time_delta < 0 ? (
                          <TrendingDown className="h-3 w-3" />
                        ) : null}
                        <span>
                          {summary.time_delta > 0 ? `+${summary.time_delta.toFixed(2)}s` : `${summary.time_delta.toFixed(2)}s`}{' '}
                          ({summary.time_ratio}x)
                        </span>
                      </span>
                      {isSlower && (
                        <span className="text-[10px] text-amber-400 font-medium">⚠️ Latency spike</span>
                      )}
                      {isFaster && (
                        <span className="text-[10px] text-cyan-400 font-medium">⚡ Speedup</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* 3. Steps & Data Drift Card */}
                <div className="p-4 rounded-xl border bg-slate-950/40 border-slate-800 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                      Data & Step Divergence
                    </span>
                    <Layers className="h-4 w-4 text-purple-400" />
                  </div>
                  <div className="mt-2 space-y-1 text-xs">
                    <div className="flex justify-between items-center text-slate-300">
                      <span>Step Count:</span>
                      <span className="font-mono font-medium">
                        A: {comparison.run_a.successful_steps}/{comparison.run_a.total_steps} ➔ B:{' '}
                        {comparison.run_b.successful_steps}/{comparison.run_b.total_steps}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-slate-300">
                      <span>Inputs Differ:</span>
                      <span
                        className={`font-mono font-semibold ${
                          summary.inputs_differ_count > 0 ? 'text-amber-400' : 'text-slate-400'
                        }`}
                      >
                        {summary.inputs_differ_count} key(s)
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-slate-300">
                      <span>Context Values Differ:</span>
                      <span
                        className={`font-mono font-semibold ${
                          summary.context_differ_count > 0 ? 'text-purple-400' : 'text-slate-400'
                        }`}
                      >
                        {summary.context_differ_count} key(s)
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="flex border-b border-slate-800 space-x-6 text-xs">
                <button
                  onClick={() => setActiveTab('matrix')}
                  className={`pb-3 font-semibold transition-colors flex items-center space-x-2 border-b-2 ${
                    activeTab === 'matrix'
                      ? 'border-sky-500 text-sky-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Clock className="h-4 w-4" />
                  <span>Step Execution Matrix</span>
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-slate-800 font-mono">
                    {comparison.step_comparisons.length}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab('context')}
                  className={`pb-3 font-semibold transition-colors flex items-center space-x-2 border-b-2 ${
                    activeTab === 'context'
                      ? 'border-sky-500 text-sky-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Zap className="h-4 w-4" />
                  <span>Inputs & Context Diff</span>
                  {(summary.inputs_differ_count > 0 || summary.context_differ_count > 0) && (
                    <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-amber-500/20 text-amber-300 font-mono">
                      {summary.inputs_differ_count + summary.context_differ_count}
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setActiveTab('meta')}
                  className={`pb-3 font-semibold transition-colors flex items-center space-x-2 border-b-2 ${
                    activeTab === 'meta'
                      ? 'border-sky-500 text-sky-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="h-4 w-4" />
                  <span>Execution Metadata</span>
                </button>
              </div>

              {/* Tab 1: Step Matrix */}
              {activeTab === 'matrix' && (
                <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950/30">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/80 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                      <tr>
                        <th className="py-3 px-4">Step Name</th>
                        <th className="py-3 px-4">Baseline (A)</th>
                        <th className="py-3 px-4">Target (B)</th>
                        <th className="py-3 px-4 text-center">Latency Drift</th>
                        <th className="py-3 px-4 text-right">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {comparison.step_comparisons.map((sc: StepComparison) => {
                        const isReg = sc.match_type === 'regressed';
                        const isImp = sc.match_type === 'improved';
                        const isSlow = sc.match_type === 'slower';
                        const isFast = sc.match_type === 'faster';
                        const hasErr = Boolean(sc.error_b || sc.error_a || sc.message_b);
                        const isExpanded = Boolean(expandedErrors[sc.name]);

                        return (
                          <React.Fragment key={sc.name}>
                            <tr
                              className={`hover:bg-slate-800/30 transition-colors ${
                                isReg ? 'bg-rose-950/10' : ''
                              }`}
                            >
                              <td className="py-3 px-4 font-mono font-medium text-slate-200">
                                <div className="flex items-center space-x-2">
                                  <span>{sc.name}</span>
                                  {hasErr && (
                                    <button
                                      onClick={() => toggleError(sc.name)}
                                      className="text-slate-500 hover:text-slate-300"
                                      title="Toggle error message details"
                                    >
                                      {isExpanded ? (
                                        <ChevronUp className="h-3 w-3" />
                                      ) : (
                                        <ChevronDown className="h-3 w-3" />
                                      )}
                                    </button>
                                  )}
                                </div>
                              </td>

                              {/* Baseline Status & Time */}
                              <td className="py-3 px-4">
                                <div className="flex items-center space-x-1.5">
                                  {sc.success_a ? (
                                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                                  ) : sc.status_a === 'missing' ? (
                                    <span className="text-slate-600 font-mono">-</span>
                                  ) : (
                                    <XCircle className="h-3.5 w-3.5 text-rose-400" />
                                  )}
                                  <span className="capitalize text-slate-300 font-medium">
                                    {sc.status_a}
                                  </span>
                                  <span className="font-mono text-slate-500 text-[11px]">
                                    ({sc.time_a.toFixed(2)}s)
                                  </span>
                                </div>
                              </td>

                              {/* Target Status & Time */}
                              <td className="py-3 px-4">
                                <div className="flex items-center space-x-1.5">
                                  {sc.success_b ? (
                                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                                  ) : sc.status_b === 'missing' ? (
                                    <span className="text-slate-600 font-mono">-</span>
                                  ) : (
                                    <XCircle className="h-3.5 w-3.5 text-rose-400" />
                                  )}
                                  <span
                                    className={`capitalize font-medium ${
                                      isReg ? 'text-rose-400 font-semibold' : 'text-slate-300'
                                    }`}
                                  >
                                    {sc.status_b}
                                  </span>
                                  <span className="font-mono text-slate-500 text-[11px]">
                                    ({sc.time_b.toFixed(2)}s)
                                  </span>
                                </div>
                              </td>

                              {/* Latency Drift */}
                              <td className="py-3 px-4 text-center font-mono">
                                <span
                                  className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] ${
                                    sc.time_delta > 0.05
                                      ? 'text-rose-400 bg-rose-500/10'
                                      : sc.time_delta < -0.05
                                      ? 'text-emerald-400 bg-emerald-500/10'
                                      : 'text-slate-500'
                                  }`}
                                >
                                  <span>
                                    {sc.time_delta > 0
                                      ? `+${sc.time_delta.toFixed(2)}s`
                                      : sc.time_delta < 0
                                      ? `${sc.time_delta.toFixed(2)}s`
                                      : '0.00s'}
                                  </span>
                                </span>
                              </td>

                              {/* Match Type Badge */}
                              <td className="py-3 px-4 text-right">
                                <span
                                  className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${
                                    isReg
                                      ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                                      : isImp
                                      ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                                      : isSlow
                                      ? 'bg-amber-950/60 text-amber-300 border-amber-800'
                                      : isFast
                                      ? 'bg-cyan-950/60 text-cyan-300 border-cyan-800'
                                      : sc.match_type === 'missing_in_target'
                                      ? 'bg-slate-800 text-slate-400 border-slate-700'
                                      : 'bg-slate-800 text-slate-300 border-slate-700/60'
                                  }`}
                                >
                                  {isReg
                                    ? 'Regressed ❌'
                                    : isImp
                                    ? 'Improved ✅'
                                    : isSlow
                                    ? 'Slower ⏱️'
                                    : isFast
                                    ? 'Faster ⚡'
                                    : sc.match_type === 'missing_in_target'
                                    ? 'Missing in Target'
                                    : 'Matched ✓'}
                                </span>
                              </td>
                            </tr>

                            {/* Expandable Error Row */}
                            {(isExpanded || isReg) && (sc.error_b || sc.message_b || sc.error_a) && (
                              <tr className="bg-slate-950/80">
                                <td colSpan={5} className="py-2.5 px-6 font-mono text-xs">
                                  {sc.error_b && (
                                    <div className="text-rose-400 flex items-start space-x-2">
                                      <span className="font-semibold text-rose-500">[Target Error]:</span>
                                      <span>{sc.error_b}</span>
                                    </div>
                                  )}
                                  {sc.message_b && (
                                    <div className="text-slate-400 flex items-start space-x-2 mt-0.5">
                                      <span className="text-slate-500">[Target Message]:</span>
                                      <span>{sc.message_b}</span>
                                    </div>
                                  )}
                                  {sc.error_a && (
                                    <div className="text-amber-400/80 flex items-start space-x-2 mt-0.5">
                                      <span className="text-amber-500">[Baseline Error]:</span>
                                      <span>{sc.error_a}</span>
                                    </div>
                                  )}
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Tab 2: Inputs & Context Diff */}
              {activeTab === 'context' && (
                <div className="space-y-6">
                  {/* Inputs Diff Section */}
                  <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950/30">
                    <div className="px-4 py-3 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between">
                      <span className="font-semibold text-slate-200 text-xs">Input Parameter Diffs</span>
                      <span className="text-[11px] font-mono text-slate-400">
                        {Object.keys(comparison.inputs_diff).length} difference(s)
                      </span>
                    </div>

                    {Object.keys(comparison.inputs_diff).length === 0 ? (
                      <div className="p-6 text-center text-slate-500 text-xs">
                        Input parameters are identical between both runs.
                      </div>
                    ) : (
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900/40 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                          <tr>
                            <th className="py-2.5 px-4">Parameter Key</th>
                            <th className="py-2.5 px-4">Baseline (A)</th>
                            <th className="py-2.5 px-4">Target (B)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {Object.entries(comparison.inputs_diff).map(([key, diff]) => (
                            <tr key={key} className="hover:bg-slate-800/20">
                              <td className="py-2.5 px-4 text-sky-400 font-semibold">{key}</td>
                              <td className="py-2.5 px-4 text-slate-400">
                                <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                                  {JSON.stringify(diff.a)}
                                </span>
                              </td>
                              <td className="py-2.5 px-4 text-purple-300">
                                <span className="bg-purple-950/30 px-2 py-0.5 rounded border border-purple-800/50">
                                  {JSON.stringify(diff.b)}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* Context State Diff Section */}
                  <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950/30">
                    <div className="px-4 py-3 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between">
                      <span className="font-semibold text-slate-200 text-xs">Final Execution Context Diffs</span>
                      <span className="text-[11px] font-mono text-slate-400">
                        {Object.keys(comparison.context_diff).length} difference(s)
                      </span>
                    </div>

                    {Object.keys(comparison.context_diff).length === 0 ? (
                      <div className="p-6 text-center text-slate-500 text-xs">
                        Final context variable states are identical between both runs.
                      </div>
                    ) : (
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900/40 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                          <tr>
                            <th className="py-2.5 px-4">Context Key</th>
                            <th className="py-2.5 px-4">Baseline (A)</th>
                            <th className="py-2.5 px-4">Target (B)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {Object.entries(comparison.context_diff).map(([key, diff]) => (
                            <tr key={key} className="hover:bg-slate-800/20">
                              <td className="py-2.5 px-4 text-amber-400 font-semibold">{key}</td>
                              <td className="py-2.5 px-4 text-slate-400 max-w-xs truncate">
                                <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                                  {typeof diff.a === 'object' ? JSON.stringify(diff.a) : String(diff.a)}
                                </span>
                              </td>
                              <td className="py-2.5 px-4 text-cyan-300 max-w-xs truncate">
                                <span className="bg-cyan-950/30 px-2 py-0.5 rounded border border-cyan-800/50">
                                  {typeof diff.b === 'object' ? JSON.stringify(diff.b) : String(diff.b)}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              )}

              {/* Tab 3: Execution Metadata */}
              {activeTab === 'meta' && (
                <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950/30 p-6 space-y-4 text-xs font-mono">
                  <div className="grid grid-cols-2 gap-6">
                    {/* Baseline */}
                    <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                      <div className="font-bold text-sky-400 pb-2 border-b border-slate-800 flex items-center justify-between">
                        <span>Baseline Execution (Run A)</span>
                        <button
                          onClick={() => onSelectRunDetail && onSelectRunDetail(comparison.run_a)}
                          className="text-[11px] text-sky-400 underline hover:text-sky-300"
                        >
                          View Full Run
                        </button>
                      </div>
                      <div className="space-y-1.5 text-slate-300">
                        <div>ID: <span className="text-slate-100">{comparison.run_a.id}</span></div>
                        <div>Environment: <span className="text-emerald-400 uppercase">{comparison.run_a.environment || 'dev'}</span></div>
                        <div>Triggered By: <span className="text-slate-100">{comparison.run_a.triggered_by || 'anonymous'}</span></div>
                        <div>Profile: <span className="text-slate-100">{comparison.run_a.profile || 'default'}</span></div>
                        <div>Started: <span className="text-slate-400">{new Date(comparison.run_a.started_at).toLocaleString()}</span></div>
                        <div>Finished: <span className="text-slate-400">{comparison.run_a.completed_at ? new Date(comparison.run_a.completed_at).toLocaleString() : '-'}</span></div>
                      </div>
                    </div>

                    {/* Target */}
                    <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                      <div className="font-bold text-purple-400 pb-2 border-b border-slate-800 flex items-center justify-between">
                        <span>Target Execution (Run B)</span>
                        <button
                          onClick={() => onSelectRunDetail && onSelectRunDetail(comparison.run_b)}
                          className="text-[11px] text-purple-400 underline hover:text-purple-300"
                        >
                          View Full Run
                        </button>
                      </div>
                      <div className="space-y-1.5 text-slate-300">
                        <div>ID: <span className="text-slate-100">{comparison.run_b.id}</span></div>
                        <div>Environment: <span className="text-purple-400 uppercase">{comparison.run_b.environment || 'dev'}</span></div>
                        <div>Triggered By: <span className="text-slate-100">{comparison.run_b.triggered_by || 'anonymous'}</span></div>
                        <div>Profile: <span className="text-slate-100">{comparison.run_b.profile || 'default'}</span></div>
                        <div>Started: <span className="text-slate-400">{new Date(comparison.run_b.started_at).toLocaleString()}</span></div>
                        <div>Finished: <span className="text-slate-400">{comparison.run_b.completed_at ? new Date(comparison.run_b.completed_at).toLocaleString() : '-'}</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <span className="h-2 w-2 rounded-full bg-sky-400"></span>
            <span>Valiant Run Comparator — Partition-Aware Cross-Run Regression Engine</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
