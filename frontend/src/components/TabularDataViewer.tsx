import React, { useState, useEffect, useMemo, useTransition } from 'react';
import { 
  Table, 
  Download, 
  Search, 
  ArrowUpDown, 
  ArrowUp, 
  ArrowDown, 
  ChevronLeft, 
  ChevronRight, 
  ChevronsLeft, 
  ChevronsRight, 
  Sparkles, 
  Database, 
  HardDrive, 
  RefreshCw,
  FileSpreadsheet,
  FileCode,
  File
} from 'lucide-react';
import { TabularDataPayload, TabularColumn } from '../types';
import { fetchStepTabularData, getTabularExportUrl, TabularQueryResponse } from '../api';

interface TabularDataViewerProps {
  runId: string;
  stepName: string;
  initialPayload?: TabularDataPayload;
  env?: string;
}

export const TabularDataViewer: React.FC<TabularDataViewerProps> = ({
  runId,
  stepName,
  initialPayload,
  env,
}) => {
  const [data, setData] = useState<TabularQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Query state
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [sortBy, setSortBy] = useState<string | undefined>(undefined);
  const [sortDesc, setSortDesc] = useState<boolean>(false);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [exportMenuOpen, setExportMenuOpen] = useState(false);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1); // reset to first page on search change
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  // Load data via lazy Parquet query API if artifact exists, or fallback to initialPayload
  useEffect(() => {
    let isCancelled = false;

    async function loadData() {
      // If we don't have artifact or failed to fetch, fallback
      setLoading(true);
      setError(null);
      try {
        const res = await fetchStepTabularData(
          runId,
          stepName,
          {
            page,
            pageSize,
            sortBy,
            sortDesc,
            search: debouncedSearch.trim() || undefined,
          },
          env
        );
        if (!isCancelled) {
          setData(res);
        }
      } catch (err: any) {
        if (!isCancelled) {
          // If the backend artifact isn't queryable, use initial preview payload
          if (initialPayload) {
            setData({
              step_name: stepName,
              total_rows: initialPayload.total_rows,
              page: 1,
              page_size: initialPayload.preview_limit,
              total_pages: Math.max(1, Math.ceil(initialPayload.total_rows / initialPayload.preview_limit)),
              columns: initialPayload.columns,
              rows: initialPayload.preview_rows,
              has_artifact: initialPayload.has_artifact,
              formatted_size: initialPayload.formatted_size,
            });
          } else {
            setError(err.message || 'Failed to query tabular data');
          }
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadData();
    return () => {
      isCancelled = true;
    };
  }, [runId, stepName, page, pageSize, sortBy, sortDesc, debouncedSearch, env, initialPayload]);

  const handleSort = (colName: string) => {
    if (sortBy === colName) {
      if (!sortDesc) {
        setSortDesc(true);
      } else {
        // clear sort
        setSortBy(undefined);
        setSortDesc(false);
      }
    } else {
      setSortBy(colName);
      setSortDesc(false);
    }
    setPage(1);
  };

  const activeColumns: TabularColumn[] = useMemo(() => {
    if (data?.columns) return data.columns as TabularColumn[];
    if (initialPayload?.columns) return initialPayload.columns;
    return [];
  }, [data, initialPayload]);

  const rows = data?.rows || initialPayload?.preview_rows || [];
  const totalRows = data?.total_rows ?? initialPayload?.total_rows ?? rows.length;
  const totalPages = data?.total_pages ?? Math.max(1, Math.ceil(totalRows / pageSize));
  const formattedSize = data?.formatted_size || initialPayload?.formatted_size || 'In-Memory';

  const getTypeBadge = (col: TabularColumn) => {
    switch (col.category) {
      case 'numeric':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">{col.type}</span>;
      case 'string':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-sky-500/15 text-sky-400 border border-sky-500/30">{col.type}</span>;
      case 'datetime':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-purple-500/15 text-purple-400 border border-purple-500/30">{col.type}</span>;
      case 'boolean':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-amber-500/15 text-amber-400 border border-amber-500/30">{col.type}</span>;
      default:
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-800 text-slate-400 border border-slate-700">{col.type}</span>;
    }
  };

  const renderCellValue = (val: any) => {
    if (val === null || val === undefined) {
      return <span className="text-slate-500 italic text-xs">null</span>;
    }
    if (typeof val === 'boolean') {
      return (
        <span className={`text-[11px] px-1.5 py-0.5 rounded font-semibold font-mono ${val ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
          {val ? 'true' : 'false'}
        </span>
      );
    }
    if (typeof val === 'number') {
      return <span className="font-mono text-emerald-300/90 tabular-nums">{val.toLocaleString()}</span>;
    }
    if (typeof val === 'object') {
      return <span className="font-mono text-xs text-slate-300 truncate max-w-xs">{JSON.stringify(val)}</span>;
    }
    return <span className="truncate max-w-sm">{String(val)}</span>;
  };

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* Top Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/80 p-3 rounded-lg border border-slate-800">
        {/* Left: Summary Badges */}
        <div className="flex items-center flex-wrap gap-2">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-medium">
            <Database className="w-3.5 h-3.5" />
            <span>Polars DataFrame</span>
          </div>

          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700 text-xs font-mono">
            <Table className="w-3.5 h-3.5 text-sky-400" />
            <span>{totalRows.toLocaleString()} rows × {activeColumns.length} cols</span>
          </div>

          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-800 text-slate-400 border border-slate-700 text-xs font-mono">
            <HardDrive className="w-3.5 h-3.5 text-amber-400" />
            <span>{formattedSize}</span>
          </div>

          {loading && (
            <div className="flex items-center space-x-1 text-xs text-sky-400 animate-pulse">
              <RefreshCw className="w-3 h-3 animate-spin" />
              <span>Scanning...</span>
            </div>
          )}
        </div>

        {/* Right: Search + PageSize + Export */}
        <div className="flex items-center space-x-2">
          {/* Quick Filter */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search table..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1 bg-slate-950 border border-slate-800 rounded text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 w-36 sm:w-48 transition-colors"
            />
          </div>

          {/* Rows per page */}
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
            className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-sky-500"
          >
            <option value={25}>25 / page</option>
            <option value={50}>50 / page</option>
            <option value={100}>100 / page</option>
          </select>

          {/* Export Dropdown */}
          <div className="relative">
            <button
              onClick={() => setExportMenuOpen(!exportMenuOpen)}
              className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 text-xs font-medium transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-emerald-400" />
              <span>Export</span>
            </button>

            {exportMenuOpen && (
              <div 
                className="absolute right-0 mt-1 w-44 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100"
                onClick={() => setExportMenuOpen(false)}
              >
                <a
                  href={getTabularExportUrl(runId, stepName, 'csv', env)}
                  download={`${stepName}.csv`}
                  className="flex items-center space-x-2 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 hover:text-emerald-400 transition-colors"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                  <span>Download CSV</span>
                </a>
                <a
                  href={getTabularExportUrl(runId, stepName, 'parquet', env)}
                  download={`${stepName}.parquet`}
                  className="flex items-center space-x-2 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 hover:text-sky-400 transition-colors"
                >
                  <HardDrive className="w-4 h-4 text-sky-400" />
                  <span>Download Parquet</span>
                </a>
                <a
                  href={getTabularExportUrl(runId, stepName, 'json', env)}
                  download={`${stepName}.json`}
                  className="flex items-center space-x-2 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 hover:text-amber-400 transition-colors"
                >
                  <FileCode className="w-4 h-4 text-amber-400" />
                  <span>Download JSON</span>
                </a>
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded text-xs">
          {error}
        </div>
      )}

      {/* Main Table Grid */}
      <div className="flex-1 min-h-0 border border-slate-800 rounded-lg bg-slate-950 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-x-auto overflow-y-auto max-h-[520px]">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-900 sticky top-0 z-10 border-b border-slate-800 shadow-sm">
              <tr>
                <th className="py-2.5 px-3 text-slate-500 font-mono text-[11px] w-12 text-center border-r border-slate-800/80 bg-slate-900 sticky left-0 z-20">
                  #
                </th>
                {activeColumns.map((col) => {
                  const isSorted = sortBy === col.name;
                  return (
                    <th
                      key={col.name}
                      onClick={() => handleSort(col.name)}
                      className="py-2 px-3.5 text-slate-300 font-semibold cursor-pointer hover:bg-slate-800/70 transition-colors whitespace-nowrap select-none border-r border-slate-800/50"
                    >
                      <div className="flex items-center justify-between space-x-2">
                        <div className="flex items-center space-x-1.5">
                          <span className="text-slate-200">{col.name}</span>
                          {getTypeBadge(col)}
                        </div>
                        <div className="text-slate-500">
                          {isSorted ? (
                            sortDesc ? (
                              <ArrowDown className="w-3.5 h-3.5 text-sky-400" />
                            ) : (
                              <ArrowUp className="w-3.5 h-3.5 text-sky-400" />
                            )
                          ) : (
                            <ArrowUpDown className="w-3 h-3 opacity-30 hover:opacity-100" />
                          )}
                        </div>
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={activeColumns.length + 1} className="py-12 text-center text-slate-500 italic">
                    {loading ? 'Executing Polars query...' : 'No matching tabular records found'}
                  </td>
                </tr>
              ) : (
                rows.map((row, rowIdx) => {
                  const absoluteRowIdx = (page - 1) * pageSize + rowIdx + 1;
                  return (
                    <tr
                      key={rowIdx}
                      className="hover:bg-slate-900/70 transition-colors group"
                    >
                      <td className="py-2 px-3 text-slate-600 group-hover:text-slate-400 text-center text-[11px] border-r border-slate-800/80 bg-slate-950/80 sticky left-0 z-10">
                        {absoluteRowIdx}
                      </td>
                      {activeColumns.map((col) => (
                        <td
                          key={col.name}
                          className="py-2 px-3.5 border-r border-slate-800/40 whitespace-nowrap text-xs"
                        >
                          {renderCellValue(row[col.name])}
                        </td>
                      ))}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Bottom Pagination & Count Ribbon */}
        <div className="bg-slate-900/90 border-t border-slate-800 px-3 py-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
          <div>
            {totalRows > 0 ? (
              <span>
                Showing rows <span className="font-mono text-slate-200">{((page - 1) * pageSize) + 1}</span> to{' '}
                <span className="font-mono text-slate-200">{Math.min(page * pageSize, totalRows)}</span> of{' '}
                <span className="font-mono text-slate-200">{totalRows.toLocaleString()}</span>
              </span>
            ) : (
              <span>0 rows</span>
            )}
          </div>

          <div className="flex items-center space-x-1.5">
            <button
              onClick={() => setPage(1)}
              disabled={page <= 1 || loading}
              className="p-1 rounded hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed text-slate-300"
              title="First page"
            >
              <ChevronsLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="p-1 rounded hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed text-slate-300"
              title="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <span className="px-2 font-mono text-slate-300">
              Page {page} of {totalPages}
            </span>

            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="p-1 rounded hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed text-slate-300"
              title="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={page >= totalPages || loading}
              className="p-1 rounded hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed text-slate-300"
              title="Last page"
            >
              <ChevronsRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
