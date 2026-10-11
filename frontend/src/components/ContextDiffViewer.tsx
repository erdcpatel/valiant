import React, { useState, useMemo } from 'react';
import { StepContextDelta } from '../types';
import {
  PlusCircle,
  Edit3,
  Trash2,
  Eye,
  Layers,
  Search,
  Check,
  Copy,
  Lock,
  ArrowRight,
  Maximize2,
  Minimize2,
} from 'lucide-react';

interface ContextDiffViewerProps {
  delta?: StepContextDelta;
  contextBefore?: Record<string, any>;
  contextAfter?: Record<string, any>;
}

export const ContextDiffViewer: React.FC<ContextDiffViewerProps> = ({
  delta,
  contextBefore = {},
  contextAfter = {},
}) => {
  const [filter, setFilter] = useState<'all' | 'modified' | 'added' | 'deleted' | 'reads'>('all');
  const [search, setSearch] = useState('');
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const added = delta?.added || {};
  const modified = delta?.modified || {};
  const deleted = delta?.deleted || [];
  const reads = delta?.reads || [];

  const addedCount = Object.keys(added).length;
  const modifiedCount = Object.keys(modified).length;
  const deletedCount = deleted.length;
  const readsCount = reads.length;

  const totalMutations = addedCount + modifiedCount + deletedCount;

  const handleCopy = (key: string, value: any) => {
    navigator.clipboard.writeText(typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value));
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1800);
  };

  const toggleExpand = (k: string) => {
    setExpandedKeys((prev) => ({ ...prev, [k]: !prev[k] }));
  };

  // Filter keys based on search and selected tab
  const filteredAdded = useMemo(() => {
    return Object.entries(added).filter(([k]) => k.toLowerCase().includes(search.toLowerCase()));
  }, [added, search]);

  const filteredModified = useMemo(() => {
    return Object.entries(modified).filter(([k]) => k.toLowerCase().includes(search.toLowerCase()));
  }, [modified, search]);

  const filteredDeleted = useMemo(() => {
    return deleted.filter((k) => k.toLowerCase().includes(search.toLowerCase()));
  }, [deleted, search]);

  const filteredReads = useMemo(() => {
    return reads.filter((k) => k.toLowerCase().includes(search.toLowerCase()));
  }, [reads, search]);

  const formatValue = (v: any) => {
    if (v === null) return <span className="text-slate-500 italic">null</span>;
    if (v === undefined) return <span className="text-slate-500 italic">undefined</span>;
    if (typeof v === 'boolean') {
      return <span className={v ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>{String(v)}</span>;
    }
    if (typeof v === 'number') {
      return <span className="text-sky-300 font-bold">{v}</span>;
    }
    if (typeof v === 'string') {
      if (v === '********') {
        return (
          <span className="inline-flex items-center space-x-1 text-amber-400 bg-amber-950/60 px-1.5 py-0.5 rounded text-[10px] font-mono border border-amber-800/40">
            <Lock className="h-3 w-3" />
            <span>MASKED SECRET</span>
          </span>
        );
      }
      return <span className="text-emerald-300">"{v}"</span>;
    }
    return <span className="text-slate-300">{JSON.stringify(v)}</span>;
  };

  return (
    <div className="space-y-4 text-xs">
      {/* Metric Summary Ribbon */}
      <div className="grid grid-cols-4 gap-2">
        <button
          onClick={() => setFilter('added')}
          className={`p-2.5 rounded-xl border text-left transition-all ${
            filter === 'added'
              ? 'bg-emerald-950/40 border-emerald-500 shadow-md shadow-emerald-500/10'
              : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between text-emerald-400 mb-1">
            <span className="font-semibold text-[11px]">Added</span>
            <PlusCircle className="h-3.5 w-3.5" />
          </div>
          <span className="text-base font-bold font-mono text-emerald-300">+{addedCount}</span>
        </button>

        <button
          onClick={() => setFilter('modified')}
          className={`p-2.5 rounded-xl border text-left transition-all ${
            filter === 'modified'
              ? 'bg-amber-950/40 border-amber-500 shadow-md shadow-amber-500/10'
              : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between text-amber-400 mb-1">
            <span className="font-semibold text-[11px]">Modified</span>
            <Edit3 className="h-3.5 w-3.5" />
          </div>
          <span className="text-base font-bold font-mono text-amber-300">~{modifiedCount}</span>
        </button>

        <button
          onClick={() => setFilter('reads')}
          className={`p-2.5 rounded-xl border text-left transition-all ${
            filter === 'reads'
              ? 'bg-sky-950/40 border-sky-500 shadow-md shadow-sky-500/10'
              : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between text-sky-400 mb-1">
            <span className="font-semibold text-[11px]">Read</span>
            <Eye className="h-3.5 w-3.5" />
          </div>
          <span className="text-base font-bold font-mono text-sky-300">{readsCount}</span>
        </button>

        <button
          onClick={() => setFilter('deleted')}
          className={`p-2.5 rounded-xl border text-left transition-all ${
            filter === 'deleted'
              ? 'bg-rose-950/40 border-rose-500 shadow-md shadow-rose-500/10'
              : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between text-rose-400 mb-1">
            <span className="font-semibold text-[11px]">Deleted</span>
            <Trash2 className="h-3.5 w-3.5" />
          </div>
          <span className="text-base font-bold font-mono text-rose-300">-{deletedCount}</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setFilter('all')}
            className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
              filter === 'all'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Changes ({totalMutations + readsCount})
          </button>
          <button
            onClick={() => setFilter('modified')}
            className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
              filter === 'modified'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Modified (~{modifiedCount})
          </button>
          <button
            onClick={() => setFilter('added')}
            className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
              filter === 'added'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Added (+{addedCount})
          </button>
        </div>

        <div className="relative flex-1 max-w-[180px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search key..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-2.5 py-1 text-[11px] bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>
      </div>

      {/* Delta Entries Container */}
      <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
        {totalMutations === 0 && readsCount === 0 && (
          <div className="p-6 text-center rounded-xl bg-slate-950/40 border border-slate-800 text-slate-500">
            <Layers className="h-6 w-6 mx-auto mb-2 opacity-50" />
            <p className="font-semibold text-slate-400">No Context Mutations</p>
            <p className="text-[11px] mt-1">This step did not mutate or ingest context variables.</p>
          </div>
        )}

        {/* 1. MODIFIED KEYS (Side-by-Side Diff) */}
        {(filter === 'all' || filter === 'modified') && filteredModified.length > 0 && (
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase font-bold text-amber-400 flex items-center space-x-1">
              <Edit3 className="h-3 w-3" />
              <span>Modified Variables ({filteredModified.length})</span>
            </span>

            {filteredModified.map(([k, diff]) => {
              const isObj = typeof diff.after === 'object' && diff.after !== null;
              const isExpanded = !!expandedKeys[k];

              return (
                <div
                  key={k}
                  className="p-3 rounded-xl bg-amber-950/15 border border-amber-500/30 space-y-2.5 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-amber-300 text-xs">{k}</span>
                      <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        MUTATED
                      </span>
                    </div>

                    <div className="flex items-center space-x-1">
                      {isObj && (
                        <button
                          onClick={() => toggleExpand(k)}
                          className="px-2 py-0.5 rounded text-[10px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 transition-colors flex items-center space-x-1"
                        >
                          {isExpanded ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
                          <span>{isExpanded ? 'Collapse' : 'Diff Details'}</span>
                        </button>
                      )}
                      <button
                        onClick={() => handleCopy(k, diff.after)}
                        className="p-1 text-slate-400 hover:text-slate-200 transition-colors"
                        title="Copy current value"
                      >
                        {copiedKey === k ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>

                  {/* Side-by-side or before/after visual comparison */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div className="p-2.5 rounded-lg bg-rose-950/30 border border-rose-800/40 font-mono text-[11px]">
                      <span className="text-[10px] font-semibold text-rose-400 block mb-1 uppercase tracking-wider">
                        ← Before Step
                      </span>
                      {isObj && !isExpanded ? (
                        <span className="text-slate-400 italic">Object ({Object.keys(diff.before || {}).length} keys)</span>
                      ) : isObj && isExpanded ? (
                        <pre className="text-rose-200 whitespace-pre-wrap max-h-36 overflow-y-auto">
                          {JSON.stringify(diff.before, null, 2)}
                        </pre>
                      ) : (
                        formatValue(diff.before)
                      )}
                    </div>

                    <div className="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-800/40 font-mono text-[11px]">
                      <span className="text-[10px] font-semibold text-emerald-400 block mb-1 uppercase tracking-wider">
                        → After Step
                      </span>
                      {isObj && !isExpanded ? (
                        <span className="text-emerald-300 italic">Object ({Object.keys(diff.after || {}).length} keys)</span>
                      ) : isObj && isExpanded ? (
                        <pre className="text-emerald-200 whitespace-pre-wrap max-h-36 overflow-y-auto">
                          {JSON.stringify(diff.after, null, 2)}
                        </pre>
                      ) : (
                        formatValue(diff.after)
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* 2. ADDED KEYS */}
        {(filter === 'all' || filter === 'added') && filteredAdded.length > 0 && (
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase font-bold text-emerald-400 flex items-center space-x-1">
              <PlusCircle className="h-3 w-3" />
              <span>Created / Added Variables ({filteredAdded.length})</span>
            </span>

            {filteredAdded.map(([k, v]) => {
              const isObj = typeof v === 'object' && v !== null;
              const isExpanded = !!expandedKeys[k];

              return (
                <div
                  key={k}
                  className="p-3 rounded-xl bg-emerald-950/15 border border-emerald-500/30 space-y-1.5 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-emerald-300 text-xs">+{k}</span>
                      <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        NEW
                      </span>
                    </div>

                    <div className="flex items-center space-x-1">
                      {isObj && (
                        <button
                          onClick={() => toggleExpand(k)}
                          className="px-2 py-0.5 rounded text-[10px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 transition-colors"
                        >
                          {isExpanded ? 'Collapse' : 'Expand'}
                        </button>
                      )}
                      <button
                        onClick={() => handleCopy(k, v)}
                        className="p-1 text-slate-400 hover:text-slate-200 transition-colors"
                        title="Copy value"
                      >
                        {copiedKey === k ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px]">
                    {isObj && isExpanded ? (
                      <pre className="text-emerald-200 whitespace-pre-wrap max-h-36 overflow-y-auto">
                        {JSON.stringify(v, null, 2)}
                      </pre>
                    ) : (
                      formatValue(v)
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* 3. READ / INGESTED KEYS */}
        {(filter === 'all' || filter === 'reads') && filteredReads.length > 0 && (
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase font-bold text-sky-400 flex items-center space-x-1">
              <Eye className="h-3 w-3" />
              <span>Read / Ingested Variables ({filteredReads.length})</span>
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {filteredReads.map((k) => (
                <div
                  key={k}
                  className="p-2.5 rounded-xl bg-sky-950/20 border border-sky-800/30 flex items-center justify-between"
                >
                  <div className="truncate mr-2">
                    <span className="font-mono text-sky-300 font-semibold block truncate">{k}</span>
                    <span className="text-[10px] text-slate-400 truncate block">
                      Value: {formatValue(contextBefore[k] !== undefined ? contextBefore[k] : contextAfter[k])}
                    </span>
                  </div>
                  <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-mono font-bold bg-sky-500/10 text-sky-400 border border-sky-500/20 shrink-0">
                    READ
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 4. DELETED KEYS */}
        {(filter === 'all' || filter === 'deleted') && filteredDeleted.length > 0 && (
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase font-bold text-rose-400 flex items-center space-x-1">
              <Trash2 className="h-3 w-3" />
              <span>Removed Variables ({filteredDeleted.length})</span>
            </span>

            <div className="space-y-1.5">
              {filteredDeleted.map((k) => (
                <div
                  key={k}
                  className="p-2 rounded-lg bg-rose-950/20 border border-rose-800/30 flex items-center justify-between text-rose-300 font-mono"
                >
                  <span className="line-through">{k}</span>
                  <span className="text-[10px] text-rose-400">DELETED</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
