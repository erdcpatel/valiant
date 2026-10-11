import React from 'react';
import { StepResult, StepLineage, StepContextDelta } from '../types';
import {
  GitFork,
  ArrowRight,
  Database,
  Layers,
  Sparkles,
  Workflow,
  CheckCircle2,
  Clock,
  Compass,
} from 'lucide-react';

interface DataLineageViewerProps {
  currentStep: StepResult;
  allSteps?: StepResult[];
  onSelectStep?: (stepName: string) => void;
}

export const DataLineageViewer: React.FC<DataLineageViewerProps> = ({
  currentStep,
  allSteps = [],
  onSelectStep,
}) => {
  const lineage = currentStep.lineage;
  const delta = currentStep.context_delta;

  const upstreamSources = lineage?.upstream_sources || {};
  const downstreamTargets = lineage?.downstream_targets || {};

  const upstreamEntries = Object.entries(upstreamSources);
  const downstreamEntries = Object.entries(downstreamTargets);

  // Group upstream keys by origin step
  const groupedUpstream: Record<string, string[]> = {};
  upstreamEntries.forEach(([key, origin]) => {
    if (!groupedUpstream[origin]) groupedUpstream[origin] = [];
    groupedUpstream[origin].push(key);
  });

  const producedKeys = [
    ...Object.keys(delta?.added || {}),
    ...Object.keys(delta?.modified || {}),
  ];

  return (
    <div className="space-y-5 text-xs">
      {/* Visual Pipeline Stage Ribbon */}
      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
        <div className="flex items-center justify-between text-slate-400 text-[11px]">
          <span className="font-semibold uppercase tracking-wider text-slate-500">
            End-to-End Data Flow
          </span>
          <span className="font-mono text-sky-400 font-bold">
            {upstreamEntries.length} Ingested ➔ {producedKeys.length} Emitted
          </span>
        </div>

        {/* Mini 3-Stage Diagram */}
        <div className="grid grid-cols-3 gap-2 items-center text-center">
          <div className="p-2 rounded-lg bg-sky-950/30 border border-sky-800/40 text-sky-300">
            <span className="text-[10px] uppercase font-bold block text-sky-400">Upstream</span>
            <span className="text-xs font-semibold">{Object.keys(groupedUpstream).length} Producer(s)</span>
          </div>

          <div className="p-2 rounded-lg bg-indigo-950/50 border border-indigo-500/50 text-indigo-200 shadow-sm shadow-indigo-500/20">
            <span className="text-[10px] uppercase font-bold block text-indigo-400">Active Step</span>
            <span className="text-xs font-bold truncate block">{currentStep.name}</span>
          </div>

          <div className="p-2 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-emerald-300">
            <span className="text-[10px] uppercase font-bold block text-emerald-400">Downstream</span>
            <span className="text-xs font-semibold">{downstreamEntries.length} Consumer(s)</span>
          </div>
        </div>
      </div>

      {/* 1. UPSTREAM INGESTION (PROVENANCE) */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1.5 text-sky-400 font-semibold">
            <Compass className="h-3.5 w-3.5" />
            <span>Ingested Inputs & Origins ({upstreamEntries.length})</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Upstream Data Sources</span>
        </div>

        {upstreamEntries.length === 0 ? (
          <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 text-slate-500 text-center">
            <p className="font-semibold text-slate-400">Self-Contained Step</p>
            <p className="text-[11px] mt-0.5">This step does not consume variables from upstream predecessors.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {Object.entries(groupedUpstream).map(([origin, keys]) => {
              const isWorkflowInput = origin === 'Workflow Inputs' || origin === 'Default Parameter';
              return (
                <div
                  key={origin}
                  className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div
                        className={`p-1 rounded ${
                          isWorkflowInput ? 'bg-amber-500/10 text-amber-400' : 'bg-sky-500/10 text-sky-400'
                        }`}
                      >
                        {isWorkflowInput ? <Workflow className="h-3.5 w-3.5" /> : <Layers className="h-3.5 w-3.5" />}
                      </div>
                      <span className="font-bold text-slate-200">{origin}</span>
                    </div>

                    {!isWorkflowInput && onSelectStep && (
                      <button
                        onClick={() => onSelectStep(origin)}
                        className="text-[10px] text-sky-400 hover:text-sky-300 transition-colors font-mono"
                      >
                        Inspect Producer ↗
                      </button>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-1 border-t border-slate-900">
                    {keys.map((k) => (
                      <span
                        key={k}
                        className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-lg bg-sky-950/50 border border-sky-800/40 text-sky-300 font-mono text-[11px]"
                      >
                        <ArrowRight className="h-3 w-3 text-sky-500 shrink-0" />
                        <span>{k}</span>
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 2. DOWNSTREAM CONSUMERS (IMPACT ANALYSIS) */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1.5 text-emerald-400 font-semibold">
            <GitFork className="h-3.5 w-3.5" />
            <span>Downstream Consumers ({downstreamEntries.length})</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Future Impact</span>
        </div>

        {downstreamEntries.length === 0 ? (
          <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 text-slate-500 text-center">
            <p className="font-semibold text-slate-400">Terminal Output / Leaf Step</p>
            <p className="text-[11px] mt-0.5">
              Variables produced by this step are not ingested by any subsequent steps.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {downstreamEntries.map(([key, consumers]) => (
              <div
                key={key}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2"
              >
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-bold text-emerald-300 text-[11px]">
                    Variable: {key}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    ➔ Ingested by {consumers.length} step(s)
                  </span>
                </div>

                <div className="flex flex-wrap gap-1.5 pt-1 border-t border-slate-900">
                  {consumers.map((c) => (
                    <button
                      key={c}
                      onClick={() => onSelectStep && onSelectStep(c)}
                      className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-800/40 text-emerald-200 text-[11px] font-medium transition-colors"
                    >
                      <ArrowRight className="h-3 w-3 text-emerald-400 shrink-0" />
                      <span>{c}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
