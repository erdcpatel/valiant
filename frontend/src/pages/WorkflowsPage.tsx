import React, { useState, useEffect } from 'react';
import { WorkflowSchema, WorkflowRun } from '../types';
import { DynamicInputForm } from '../components/DynamicInputForm';
import { WorkflowDAG } from '../components/WorkflowDAG';
import {
  Layers,
  Play,
  Clock,
  Tag,
  X,
  Search,
  CheckCircle2,
  TrendingUp,
  Activity,
  Network,
  SlidersHorizontal,
} from 'lucide-react';

interface WorkflowsPageProps {
  workflows: Record<string, WorkflowSchema>;
  recentRuns: WorkflowRun[];
  onTriggerRun: (workflowName: string, inputs: Record<string, any>, meta?: { environment?: string; profile?: string }) => void;
  activeEnvironment?: string;
  isLoading?: boolean;
}

export const WorkflowsPage: React.FC<WorkflowsPageProps> = ({
  workflows,
  recentRuns,
  onTriggerRun,
  activeEnvironment = 'dev',
  isLoading = false,
}) => {
  const urlParams = new URLSearchParams(window.location.search);
  const initialModalWf = urlParams.get('modal_wf');

  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowSchema | null>(null);
  const [modalTab, setModalTab] = useState<'inputs' | 'dag'>('inputs');
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  useEffect(() => {
    if (initialModalWf && workflows[initialModalWf]) {
      setSelectedWorkflow(workflows[initialModalWf]);
    }
  }, [initialModalWf, workflows]);

  const workflowList = Object.values(workflows);

  // Compute summary stats
  const totalRuns = recentRuns.length;
  const successfulRuns = recentRuns.filter((r) => r.status === 'completed' && r.success).length;
  const successRate = totalRuns > 0 ? Math.round((successfulRuns / totalRuns) * 100) : 100;

  // Filter workflows
  const filteredWorkflows = workflowList.filter((wf) => {
    const matchesSearch =
      wf.name.toLowerCase().includes(search.toLowerCase()) ||
      wf.description.toLowerCase().includes(search.toLowerCase()) ||
      wf.id.toLowerCase().includes(search.toLowerCase());
    const matchesTag = !selectedTag || wf.tags?.includes(selectedTag);
    return matchesSearch && matchesTag;
  });

  const allTags = Array.from(new Set(workflowList.flatMap((w) => w.tags || [])));

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-gradient-to-b from-slate-900 to-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Available Workflows
            </p>
            <p className="text-3xl font-bold text-white mt-1">{workflowList.length}</p>
          </div>
          <div className="h-12 w-12 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Layers className="h-6 w-6" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-gradient-to-b from-slate-900 to-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Recorded Runs
            </p>
            <p className="text-3xl font-bold text-white mt-1">{totalRuns}</p>
          </div>
          <div className="h-12 w-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Activity className="h-6 w-6" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-gradient-to-b from-slate-900 to-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Success Rate
            </p>
            <p className="text-3xl font-bold text-white mt-1">
              <span className="text-emerald-400">{successRate}%</span>
            </p>
          </div>
          <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <TrendingUp className="h-6 w-6" />
          </div>
        </div>
      </div>

      {/* Catalog Search & Filter Header */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search workflows by name or keyword..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm bg-slate-900 border border-slate-800 rounded-xl text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
          />
        </div>

        {allTags.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
            <button
              onClick={() => setSelectedTag(null)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                selectedTag === null
                  ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                  : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
              }`}
            >
              All
            </button>
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  selectedTag === tag
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                    : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
                }`}
              >
                #{tag}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Workflow Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredWorkflows.map((wf) => (
          <div
            key={wf.id}
            className="group relative flex flex-col justify-between p-6 rounded-2xl bg-slate-900/60 hover:bg-slate-900/90 border border-slate-800/80 hover:border-sky-500/40 transition-all duration-200 hover:shadow-xl hover:shadow-sky-500/5"
          >
            <div>
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2">
                  <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
                    <Layers className="h-4 w-4" />
                  </div>
                  <span className="text-xs font-mono font-semibold text-slate-500">v{wf.version}</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  {Object.keys(wf.profiles || {}).length > 0 && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono text-indigo-300 bg-indigo-500/10 border border-indigo-500/20">
                      ⚡ {Object.keys(wf.profiles || {}).length} Profiles
                    </span>
                  )}
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono text-slate-400 bg-slate-800/80 border border-slate-700/60">
                    {wf.step_count} Steps
                  </span>
                </div>
              </div>

              <h3 className="text-lg font-bold text-slate-100 group-hover:text-sky-300 transition-colors mt-3">
                {wf.name}
              </h3>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                {wf.description}
              </p>

              {/* Steps preview pills */}
              <div className="mt-4 space-y-1">
                <p className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">
                  Pipeline Steps
                </p>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {wf.steps?.slice(0, 4).map((s, idx) => (
                    <span
                      key={s.name}
                      className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950/70 border border-slate-800 text-slate-300"
                    >
                      {idx + 1}. {s.name}
                    </span>
                  ))}
                  {wf.steps && wf.steps.length > 4 && (
                    <span className="text-[10px] px-1.5 py-0.5 text-slate-500">
                      +{wf.steps.length - 4} more
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800/60 flex items-center justify-between gap-2">
              <div className="flex items-center space-x-1.5 text-xs text-slate-500 truncate">
                <Tag className="h-3 w-3 flex-shrink-0" />
                <span className="truncate">{wf.tags?.slice(0, 2).join(', ') || 'general'}</span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedWorkflow(wf);
                    setModalTab('dag');
                  }}
                  className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white border border-slate-700/80 transition-colors"
                  title="Inspect validation rules and pipeline topology without running"
                >
                  <Network className="h-3.5 w-3.5 text-sky-400" />
                  <span>Review DAG</span>
                </button>

                <button
                  onClick={() => {
                    setSelectedWorkflow(wf);
                    setModalTab('inputs');
                  }}
                  className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all active:scale-95"
                >
                  <Play className="h-3.5 w-3.5 fill-white" />
                  <span>Run</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Run Configuration & Topology Modal */}
      {selectedWorkflow && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
          <div className={`relative w-full transition-all duration-300 max-h-[92vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden ${
            modalTab === 'dag' ? 'max-w-7xl 2xl:max-w-[92vw]' : 'max-w-4xl'
          }`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-6 py-4 border-b border-slate-800 bg-slate-950/60">
              <div>
                <span className="text-xs font-mono uppercase text-sky-400 font-semibold">
                  Launch Execution
                </span>
                <h3 className="text-lg font-bold text-slate-100">{selectedWorkflow.name}</h3>
              </div>

              <div className="flex items-center space-x-2">
                {/* Modal View Tabs */}
                <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                  <button
                    type="button"
                    onClick={() => setModalTab('inputs')}
                    className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium transition-colors ${
                      modalTab === 'inputs'
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <SlidersHorizontal className="h-3.5 w-3.5" />
                    <span>Inputs & Parameters</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setModalTab('dag')}
                    className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium transition-colors ${
                      modalTab === 'dag'
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Network className="h-3.5 w-3.5" />
                    <span>Pipeline Topology DAG</span>
                  </button>
                </div>

                <button
                  onClick={() => {
                    setSelectedWorkflow(null);
                    setModalTab('inputs');
                  }}
                  className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors ml-2"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {modalTab === 'inputs' ? (
                <DynamicInputForm
                  fields={selectedWorkflow.inputs || []}
                  profiles={selectedWorkflow.profiles}
                  activeEnvironment={activeEnvironment}
                  onSubmit={(values, meta) => {
                    onTriggerRun(selectedWorkflow.id, values, meta);
                    setSelectedWorkflow(null);
                    setModalTab('inputs');
                  }}
                  isLoading={isLoading}
                />
              ) : (
                <div className="space-y-4">
                  <p className="text-xs text-slate-400">
                    Pre-flight dependency graph for <span className="text-slate-200 font-semibold">{selectedWorkflow.name}</span>. Review parallel tiers and dependency paths before starting.
                  </p>
                  <WorkflowDAG steps={selectedWorkflow.steps || []} />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
