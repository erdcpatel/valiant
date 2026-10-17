import React, { useState } from 'react';
import { WorkflowRun } from '../types';
import { getRunReportUrl } from '../api';
import {
  CheckCircle2,
  XCircle,
  RotateCw,
  Search,
  ExternalLink,
  Trash2,
  Play,
  Clock,
  Layers,
  Sparkles,
  RotateCcw,
  SlidersHorizontal,
  ArrowRightLeft,
  ShieldAlert,
  FileText,
} from 'lucide-react';

interface RunHistoryTableProps {
  runs: WorkflowRun[];
  activeEnvironment?: string;
  onSelectRun: (run: WorkflowRun) => void;
  onRerun: (workflowName: string, inputs: Record<string, any>) => void;
  onResume?: (runId: string, fromStep?: string) => void;
  onDeleteRun: (runId: string) => void;
  onPruneRuns?: (keepCount: number) => void;
  onClearAllRuns?: () => void;
  onCompareRuns?: (runAId: string, runBId: string, envA?: string, envB?: string) => void;
}

export const RunHistoryTable: React.FC<RunHistoryTableProps> = ({
  runs,
  activeEnvironment = 'dev',
  onSelectRun,
  onRerun,
  onResume,
  onDeleteRun,
  onPruneRuns,
  onClearAllRuns,
  onCompareRuns,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showPruneMenu, setShowPruneMenu] = useState(false);
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);

  const handleToggleSelect = (runId: string) => {
    setSelectedRunIds((prev) => {
      if (prev.includes(runId)) {
        return prev.filter((id) => id !== runId);
      }
      if (prev.length >= 2) {
        return [prev[1], runId];
      }
      return [...prev, runId];
    });
  };

  const filteredRuns = runs.filter((r) => {
    const matchesSearch =
      r.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.workflow_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-4">
      {/* Comparator Selection Banner */}
      {selectedRunIds.length > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between p-3 rounded-xl bg-sky-950/40 border border-sky-800/60 text-xs animate-fadeIn gap-3">
          <div className="flex items-center space-x-2">
            <ArrowRightLeft className="h-4 w-4 text-sky-400 shrink-0" />
            <span className="text-slate-200">
              {selectedRunIds.length === 1 ? (
                <span>
                  <strong className="text-sky-300 font-mono">{selectedRunIds[0]}</strong> selected. Check a 2nd run to compare regression & latency drift.
                </span>
              ) : (
                <span>
                  Ready to compare <strong className="text-sky-300 font-mono">{selectedRunIds[0]}</strong> (Baseline) vs{' '}
                  <strong className="text-purple-300 font-mono">{selectedRunIds[1]}</strong> (Target)
                </span>
              )}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            {selectedRunIds.length === 2 && onCompareRuns && (
              <button
                onClick={() => {
                  const runA = runs.find((r) => r.id === selectedRunIds[0]);
                  const runB = runs.find((r) => r.id === selectedRunIds[1]);
                  onCompareRuns(
                    selectedRunIds[0],
                    selectedRunIds[1],
                    runA?.environment,
                    runB?.environment
                  );
                }}
                className="px-3 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold flex items-center space-x-1.5 shadow-lg shadow-sky-500/20 transition-colors"
              >
                <ArrowRightLeft className="h-3.5 w-3.5" />
                <span>Launch Comparator</span>
              </button>
            )}
            <button
              onClick={() => setSelectedRunIds([])}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search runs by ID or name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 text-sm bg-slate-900 border border-slate-800 rounded-lg text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
            />
          </div>
          <div className="hidden md:flex items-center space-x-1.5 text-xs font-mono text-slate-400 bg-slate-900/80 px-3 py-2 rounded-lg border border-slate-800">
            <span className="h-2 w-2 rounded-full bg-sky-400"></span>
            <span>valiant_{activeEnvironment}.db</span>
          </div>
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-medium text-slate-300 focus:outline-none focus:border-sky-500"
          >
            <option value="all">All Statuses</option>
            <option value="waiting_approval">Waiting Approval</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
            <option value="cancelled">Cancelled</option>
          </select>

          {/* Cross-Environment Compare Button */}
          {onCompareRuns && (
            <button
              onClick={() => {
                const targetEnv = activeEnvironment === 'prod' ? 'dev' : 'prod';
                onCompareRuns('', '', activeEnvironment, targetEnv);
              }}
              className="px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-400 hover:text-sky-300 border border-slate-700/80 flex items-center space-x-1.5 transition-colors"
              title="Compare runs across environments (DEV vs UAT vs PROD)"
            >
              <ArrowRightLeft className="h-3.5 w-3.5 text-sky-400" />
              <span>Cross-Env Diff</span>
            </button>
          )}

          {/* Database Maintenance / Prune Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowPruneMenu(!showPruneMenu)}
              className="px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/80 flex items-center space-x-1.5 transition-colors"
              title="Database cleanup & vacuum storage"
            >
              <SlidersHorizontal className="h-3.5 w-3.5 text-slate-400" />
              <span>Clean DB</span>
            </button>

            {showPruneMenu && (
              <div
                className="absolute right-0 mt-2 w-56 rounded-xl bg-slate-900 border border-slate-700/80 shadow-2xl py-1 z-30 animate-fadeIn text-xs"
                onMouseLeave={() => setShowPruneMenu(false)}
              >
                <div className="px-3 py-2 border-b border-slate-800 text-[11px] text-slate-400 font-medium">
                  SQLite Storage & Retention ({activeEnvironment.toUpperCase()})
                </div>
                <button
                  onClick={() => {
                    setShowPruneMenu(false);
                    onPruneRuns?.(30);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                >
                  Keep latest 30 runs (Prune + Vacuum)
                </button>
                <button
                  onClick={() => {
                    setShowPruneMenu(false);
                    onPruneRuns?.(10);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                >
                  Keep latest 10 runs (Aggressive Prune)
                </button>
                <div className="border-t border-slate-800/80 my-1"></div>
                <button
                  onClick={() => {
                    setShowPruneMenu(false);
                    onClearAllRuns?.();
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-rose-500/20 text-rose-400 font-medium transition-colors"
                >
                  Clear all run history (Full Vacuum)
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/50">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <th className="py-3 px-3 w-8 text-center">
                <span className="sr-only">Select</span>
              </th>
              <th className="py-3 px-4">Run ID</th>
              <th className="py-3 px-4">Workflow</th>
              <th className="py-3 px-4 text-center">Env</th>
              <th className="py-3 px-4">Operator</th>
              <th className="py-3 px-4 text-center">Status</th>
              <th className="py-3 px-4 text-center">Steps</th>
              <th className="py-3 px-4 text-right">Duration</th>
              <th className="py-3 px-4">Started</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-xs">
            {filteredRuns.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-12 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <Clock className="h-6 w-6 text-slate-600" />
                    <p>No executions found matching your criteria</p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredRuns.map((r) => {
                const isWaitingApproval = r.status === 'waiting_approval';
                const isSuccess = r.status === 'completed' && r.success;
                const isFailed = r.status === 'failed';
                const isRunning = r.status === 'running';
                const isSelected = selectedRunIds.includes(r.id);

                return (
                  <tr
                    key={r.id}
                    className={`hover:bg-slate-800/40 transition-colors group cursor-pointer ${
                      isSelected ? 'bg-sky-950/20' : ''
                    }`}
                    onClick={() => onSelectRun(r)}
                  >
                    <td className="py-3 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleSelect(r.id)}
                        className="rounded bg-slate-800 border-slate-700 text-sky-500 focus:ring-sky-500 focus:ring-offset-slate-900 cursor-pointer h-3.5 w-3.5"
                        title="Select run for regression comparison"
                      />
                    </td>
                    <td className="py-3 px-4 font-mono">
                      <div className="text-sky-400 font-semibold">{r.id}</div>
                      {r.parent_run_id && (
                        <div className="text-[10px] text-cyan-400 flex items-center space-x-1 mt-0.5">
                          <Sparkles className="h-2.5 w-2.5" />
                          <span>Resumed ({r.resumed_from_step || 'failure'})</span>
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-4 font-medium text-slate-200">
                      <div className="flex items-center space-x-2">
                        <Layers className="h-3.5 w-3.5 text-slate-500" />
                        <span>{r.workflow_name}</span>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                          r.environment === 'prod'
                            ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                            : r.environment === 'uat'
                            ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                            : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                        }`}
                      >
                        {(r.environment || activeEnvironment).toUpperCase()}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-slate-300 font-mono text-[11px]">
                      <span
                        className="inline-block px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/60 text-slate-300 max-w-[170px] truncate align-middle whitespace-nowrap"
                        title={r.triggered_by || 'anonymous'}
                      >
                        {r.triggered_by || 'anonymous'}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide border ${
                          isWaitingApproval
                            ? 'bg-amber-950/70 text-amber-300 border-amber-500/70 animate-pulse font-bold'
                            : isSuccess
                            ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/50'
                            : isFailed
                            ? 'bg-rose-950/60 text-rose-400 border-rose-800/50'
                            : isRunning
                            ? 'bg-sky-950/60 text-sky-400 border-sky-800/50 animate-pulse'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {isWaitingApproval ? (
                          <ShieldAlert className="h-3 w-3 text-amber-400" />
                        ) : isSuccess ? (
                          <CheckCircle2 className="h-3 w-3" />
                        ) : isFailed ? (
                          <XCircle className="h-3 w-3" />
                        ) : isRunning ? (
                          <RotateCw className="h-3 w-3 animate-spin" />
                        ) : null}
                        <span>{isWaitingApproval ? 'WAITING APPROVAL' : r.status}</span>
                      </span>
                    </td>

                    <td className="py-3 px-4 text-center font-mono text-slate-300">
                      {(isRunning || isWaitingApproval) && r.total_steps === 0 ? (
                        <span className="text-slate-500">—</span>
                      ) : (
                        `${r.successful_steps}/${r.total_steps}`
                      )}
                    </td>

                    <td className="py-3 px-4 text-right font-mono text-slate-400">
                      {r.total_time ? `${r.total_time.toFixed(2)}s` : '-'}
                    </td>

                    <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                      {r.started_at ? new Date(r.started_at).toLocaleTimeString() : '-'}
                    </td>

                    <td className="py-3 px-4 text-right space-x-2" onClick={(e) => e.stopPropagation()}>
                      {isWaitingApproval && (
                        <button
                          title="Review breakpoint approval gate"
                          onClick={() => onSelectRun(r)}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-[10px] font-mono font-bold transition-all shadow-sm shadow-amber-500/20"
                        >
                          <ShieldAlert className="h-3 w-3" />
                          <span>Review</span>
                        </button>
                      )}

                      {isFailed && onResume && (
                        <button
                          title="Smart Resume from failed step"
                          onClick={() => onResume(r.id)}
                          className="p-1.5 rounded-md hover:bg-amber-500/20 text-amber-400 hover:text-amber-300 transition-colors"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                        </button>
                      )}

                      <button
                        title="Re-run with same inputs"
                        onClick={() => onRerun(r.workflow_name, r.inputs)}
                        className="p-1.5 rounded-md hover:bg-sky-500/20 text-slate-400 hover:text-sky-400 transition-colors"
                      >
                        <Play className="h-3.5 w-3.5 fill-current" />
                      </button>

                      {onCompareRuns && (
                        <button
                          title="Compare with adjacent run"
                          onClick={() => {
                            const idx = runs.findIndex((x) => x.id === r.id);
                            const otherRun = idx > 0 ? runs[idx - 1] : runs[idx + 1];
                            if (otherRun) {
                              onCompareRuns(otherRun.id, r.id, otherRun.environment, r.environment);
                            } else {
                              handleToggleSelect(r.id);
                            }
                          }}
                          className="p-1.5 rounded-md hover:bg-purple-500/20 text-slate-400 hover:text-purple-400 transition-colors"
                        >
                          <ArrowRightLeft className="h-3.5 w-3.5" />
                        </button>
                      )}

                      <a
                        title="View Standalone HTML Report"
                        href={getRunReportUrl(r.id, false, r.environment)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-block p-1.5 rounded-md hover:bg-cyan-500/20 text-slate-400 hover:text-cyan-300 transition-colors"
                      >
                        <FileText className="h-3.5 w-3.5" />
                      </a>

                      <button
                        title="Inspect Run"
                        onClick={() => onSelectRun(r)}
                        className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </button>

                      <button
                        title="Delete Run Record"
                        onClick={() => onDeleteRun(r.id)}
                        className="p-1.5 rounded-md hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
