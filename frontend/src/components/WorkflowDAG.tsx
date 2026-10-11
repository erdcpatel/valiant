import React, { useState, useRef, useMemo, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { StepSchema, StepResult } from '../types';
import { computeDAGLayout, DAGNode } from '../utils/dagLayout';
import { StepDetailDrawer } from './StepDetailDrawer';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  CheckCircle2,
  XCircle,
  Clock,
  RotateCw,
  FastForward,
  Layers,
  Focus,
  RotateCcw,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

interface WorkflowDAGProps {
  steps: (StepSchema | StepResult)[];
  activeStepName?: string | null;
  onSelectNode?: (nodeName: string) => void;
  selectedNodeName?: string | null;
  defaultHeight?: string;
  onResumeFromStep?: (nodeName: string) => void;
  runId?: string;
  env?: string;
}

export const WorkflowDAG: React.FC<WorkflowDAGProps> = ({
  steps,
  activeStepName,
  onSelectNode,
  selectedNodeName,
  defaultHeight = 'h-[620px]',
  onResumeFromStep,
  runId,
  env,
}) => {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fullscreen state
  const [isNativeFullscreen, setIsNativeFullscreen] = useState(false);
  const [isFullscreenPortal, setIsFullscreenPortal] = useState(false);
  const isFullscreen = isNativeFullscreen || isFullscreenPortal;

  const urlParams = new URLSearchParams(window.location.search);
  const initialInspectStep = urlParams.get('inspect_step');

  // Drawer inspection state
  const [inspectedStep, setInspectedStep] = useState<StepSchema | StepResult | null>(null);

  useEffect(() => {
    if (initialInspectStep && steps.length > 0) {
      const found = steps.find(
        (s) => s.name.toLowerCase() === initialInspectStep.toLowerCase() || s.name === initialInspectStep
      );
      if (found) setInspectedStep(found);
    }
  }, [initialInspectStep, steps]);

  // Pan & Zoom transform state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 30, y: 30 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Filtering
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  // Compute Layout
  const layout = useMemo(() => {
    return computeDAGLayout(steps, activeStepName);
  }, [steps, activeStepName]);

  // Extract all categories / tags
  const allTags = useMemo(() => {
    const set = new Set<string>();
    steps.forEach((s) => s.tags?.forEach((t) => set.add(t)));
    return Array.from(set);
  }, [steps]);

  // Reset / Fit to container
  const handleFitView = useCallback(() => {
    if (!containerRef.current) return;
    const { clientWidth, clientHeight } = containerRef.current;
    if (!clientWidth || !clientHeight) return;

    const padX = isFullscreen ? 100 : 60;
    const padY = isFullscreen ? 100 : 60;
    const scaleX = (clientWidth - padX) / Math.max(layout.width, 1);
    const scaleY = (clientHeight - padY) / Math.max(layout.height, 1);
    const fitScale = Math.min(Math.max(Math.min(scaleX, scaleY), 0.35), 1.35);

    setZoom(fitScale);
    setPan({
      x: Math.max((clientWidth - layout.width * fitScale) / 2, 20),
      y: Math.max((clientHeight - layout.height * fitScale) / 2, 20),
    });
  }, [layout.width, layout.height, isFullscreen]);

  // Trigger fit view whenever layout changes or fullscreen status changes
  useEffect(() => {
    const timer = setTimeout(handleFitView, 60);
    return () => clearTimeout(timer);
  }, [handleFitView]);

  // Listen for native browser fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isNative = Boolean(document.fullscreenElement);
      setIsNativeFullscreen(isNative);
      if (!isNative) {
        setIsFullscreenPortal(false);
      }
      setTimeout(handleFitView, 120);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
    };
  }, [handleFitView]);

  // Listen for window resize to adapt to ultrawide / big displays
  useEffect(() => {
    const handleResize = () => {
      if (isFullscreen) {
        handleFitView();
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isFullscreen, handleFitView]);

  // Fullscreen toggle: tries Native Fullscreen API first, falls back to React Portal
  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement && !isFullscreenPortal) {
        if (wrapperRef.current?.requestFullscreen) {
          await wrapperRef.current.requestFullscreen();
        } else if ((wrapperRef.current as any)?.webkitRequestFullscreen) {
          await (wrapperRef.current as any).webkitRequestFullscreen();
        } else {
          // Native API not supported, use direct viewport portal
          setIsFullscreenPortal(true);
        }
      } else {
        if (document.fullscreenElement) {
          if (document.exitFullscreen) {
            await document.exitFullscreen();
          } else if ((document as any)?.webkitExitFullscreen) {
            await (document as any).webkitExitFullscreen();
          }
        }
        setIsFullscreenPortal(false);
      }
    } catch (err) {
      console.warn('Native Fullscreen request was prevented, falling back to full-screen portal:', err);
      setIsFullscreenPortal((prev) => !prev);
    }
  };

  // Keyboard shortcuts (F for fullscreen, 0 for fit view, Esc to exit portal)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === 'INPUT') return;

      if (e.key === 'Escape' && isFullscreenPortal) {
        setIsFullscreenPortal(false);
      } else if (e.key === 'f' || e.key === 'F') {
        toggleFullscreen();
      } else if (e.key === '0' || e.key === 'r' || e.key === 'R') {
        handleFitView();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreenPortal, handleFitView]);

  // Mouse wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.12 : 0.88;
    setZoom((prev) => Math.min(Math.max(prev * zoomFactor, 0.25), 2.5));
  };

  // Drag pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => setIsDragging(false);

  // Status Styling helpers
  const getNodeBorder = (node: DAGNode) => {
    if (node.result?.reused) return 'border-cyan-500/50 bg-cyan-950/25 shadow-md shadow-cyan-500/15';
    if (node.status === 'waiting_approval') return 'border-amber-400 ring-2 ring-amber-400/50 shadow-xl shadow-amber-500/40 bg-amber-950/40 animate-pulse';
    if (node.status === 'rejected') return 'border-rose-500/80 bg-rose-950/40 shadow-md shadow-rose-500/20';
    if (node.status === 'running') return 'border-sky-400 shadow-lg shadow-sky-500/30 bg-sky-950/40';
    if (node.status === 'success') return 'border-emerald-500/40 bg-emerald-950/20 hover:border-emerald-400';
    if (node.status === 'failed') return 'border-rose-500/60 bg-rose-950/30 shadow-md shadow-rose-500/20';
    if (node.status === 'skipped') return 'border-amber-500/40 bg-amber-950/10 border-dashed opacity-75';
    return 'border-slate-800 bg-slate-900/60 hover:border-slate-700';
  };

  const getStatusIcon = (node: DAGNode) => {
    if (node.result?.reused) return <Sparkles className="h-4 w-4 text-cyan-400" />;
    if (node.status === 'waiting_approval') return <ShieldAlert className="h-4 w-4 text-amber-400 animate-bounce" />;
    if (node.status === 'rejected') return <XCircle className="h-4 w-4 text-rose-500" />;
    if (node.status === 'running') return <RotateCw className="h-4 w-4 text-sky-400 animate-spin" />;
    if (node.status === 'success') return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
    if (node.status === 'failed') return <XCircle className="h-4 w-4 text-rose-400" />;
    if (node.status === 'skipped') return <FastForward className="h-4 w-4 text-amber-400" />;
    return <Clock className="h-4 w-4 text-slate-600" />;
  };

  // The complete DAG visual content
  const dagContent = (
    <div
      ref={wrapperRef}
      className={`bg-slate-950 border border-slate-800 overflow-hidden flex flex-col select-none transition-all duration-200 ${
        isFullscreen
          ? 'fixed inset-0 z-[99999] w-screen h-screen rounded-none border-0'
          : `relative rounded-2xl ${defaultHeight}`
      }`}
    >
      {/* Top Toolbar Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 z-10 backdrop-blur-sm">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400">
            <Layers className="h-4 w-4" />
          </div>
          <span className="text-xs font-semibold text-slate-200">Interactive DAG Graph</span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
            {layout.nodes.length} Steps
          </span>
          {layout.tiers.some((t) => t.isParallel) && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 flex items-center space-x-1">
              <span>⚡</span>
              <span>{layout.tiers.filter((t) => t.isParallel).length} Parallel Stages</span>
            </span>
          )}
          {isFullscreen && (
            <span className="hidden sm:inline-flex items-center text-[11px] font-mono px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-300 border border-sky-500/30">
              ⛶ Fullscreen Active • Ultrawide View (Press ESC to exit)
            </span>
          )}
        </div>

        {/* Categories / Search Filter */}
        <div className="flex items-center space-x-2">
          {allTags.length > 0 && (
            <div className="hidden sm:flex items-center space-x-1">
              <button
                type="button"
                onClick={() => setCategoryFilter(null)}
                className={`px-2 py-1 rounded text-[11px] font-mono transition-colors ${
                  categoryFilter === null
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                    : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-slate-200'
                }`}
              >
                All
              </button>
              {allTags.slice(0, 4).map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => setCategoryFilter(categoryFilter === tag ? null : tag)}
                  className={`px-2 py-1 rounded text-[11px] font-mono transition-colors ${
                    categoryFilter === tag
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                      : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  #{tag}
                </button>
              ))}
            </div>
          )}

          {/* Pan / Zoom / Fullscreen Control Buttons */}
          <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800 shadow-inner">
            <button
              onClick={() => setZoom((z) => Math.min(z * 1.2, 2.5))}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
              title="Zoom In (+)"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(z / 1.2, 0.25))}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
              title="Zoom Out (-)"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleFitView}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
              title="Fit Graph to Screen (0 or R)"
            >
              <Focus className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => {
                setZoom(1);
                handleFitView();
              }}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
              title="Reset 100% Zoom"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>

            <div className="h-4 w-px bg-slate-800 mx-0.5" />

            {/* True Fullscreen Toggle Button */}
            <button
              onClick={toggleFullscreen}
              className={`inline-flex items-center space-x-1 px-1.5 py-1 rounded transition-colors ${
                isFullscreen
                  ? 'bg-sky-500/20 text-sky-400 border border-sky-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
              title={isFullscreen ? 'Exit Fullscreen (Esc)' : 'Expand to Fullscreen (F)'}
            >
              {isFullscreen ? (
                <>
                  <Minimize2 className="h-3.5 w-3.5" />
                  <span className="text-[10px] font-mono font-medium hidden md:inline">Exit</span>
                </>
              ) : (
                <>
                  <Maximize2 className="h-3.5 w-3.5" />
                  <span className="text-[10px] font-mono font-medium hidden md:inline">Fullscreen</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div
        ref={containerRef}
        className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing overflow-hidden"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <svg
          className="w-full h-full"
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(51, 65, 85, 0.25) 1px, transparent 1px)',
            backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
            backgroundPosition: `${pan.x}px ${pan.y}px`,
          }}
        >
          <defs>
            {/* Edge Arrowhead Markers */}
            <marker
              id="arrow-default"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#475569" />
            </marker>
            <marker
              id="arrow-active"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
            </marker>
            <marker
              id="arrow-failed"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#f43f5e" />
            </marker>
          </defs>

          {/* Graph Content with Pan & Zoom transform */}
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Render Tier Column Backgrounds & Headers */}
            {layout.tiers.map((tier) => (
              <g key={`tier-${tier.layer}`}>
                {/* Column background lane */}
                <rect
                  x={tier.x - 12}
                  y={10}
                  width={244}
                  height={layout.height - 20}
                  rx={16}
                  fill={tier.isParallel ? 'rgba(99, 102, 241, 0.04)' : 'rgba(30, 41, 59, 0.02)'}
                  stroke={tier.isParallel ? 'rgba(99, 102, 241, 0.25)' : 'rgba(51, 65, 85, 0.15)'}
                  strokeDasharray={tier.isParallel ? '4,4' : undefined}
                  pointerEvents="none"
                />
                {/* Tier Header Badge */}
                <foreignObject
                  x={tier.x}
                  y={16}
                  width={220}
                  height={26}
                  className="pointer-events-none overflow-visible"
                >
                  <div className="flex items-center justify-center">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-wide border shadow-sm ${
                        tier.isParallel
                          ? 'bg-indigo-950/80 text-indigo-300 border-indigo-500/40 shadow-indigo-500/20'
                          : 'bg-slate-900/90 text-slate-400 border-slate-700/60'
                      }`}
                    >
                      {tier.isParallel ? '⚡ ' : '▸ '}
                      {tier.title}
                    </span>
                  </div>
                </foreignObject>
              </g>
            ))}

            {/* Render Bezier Edges */}
            {layout.edges.map((edge) => {
              const strokeColor = edge.active
                ? '#38bdf8'
                : edge.failed
                ? '#f43f5e'
                : '#475569';

              const markerId = edge.active
                ? 'url(#arrow-active)'
                : edge.failed
                ? 'url(#arrow-failed)'
                : 'url(#arrow-default)';

              return (
                <path
                  key={edge.id}
                  d={edge.path}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={edge.active ? 2.5 : 1.75}
                  strokeDasharray={edge.active ? '6,4' : undefined}
                  markerEnd={markerId}
                  className="transition-colors duration-200"
                />
              );
            })}

            {/* Render Nodes as foreignObjects */}
            {layout.nodes.map((node) => {
              const isSelected = selectedNodeName === node.id;
              const matchesFilter =
                !categoryFilter ||
                (node.tags && node.tags.includes(categoryFilter));
              const stepObj = steps.find((s) => s.name === node.name) || node.result;

              return (
                <foreignObject
                  key={node.id}
                  x={node.x}
                  y={node.y}
                  width={node.width}
                  height={node.height}
                  className="overflow-visible"
                >
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      if (stepObj) setInspectedStep(stepObj);
                      if (onSelectNode) onSelectNode(node.id);
                    }}
                    className={`h-full w-full rounded-xl border p-3.5 flex flex-col justify-between transition-all duration-200 cursor-pointer backdrop-blur-md select-none group ${getNodeBorder(
                      node
                    )} ${
                      isSelected
                        ? 'ring-2 ring-sky-400 ring-offset-2 ring-offset-slate-950 scale-[1.02]'
                        : ''
                    } ${matchesFilter ? 'opacity-100' : 'opacity-25'}`}
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between space-x-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-1.5 mb-1">
                          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            STEP #{node.order ?? node.layer + 1}
                          </span>
                          {node.parallel_group && (
                            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                              ⚡ {node.parallel_group}
                            </span>
                          )}
                          {(node.requires_approval || (stepObj as any)?.requires_approval) && (
                            <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded flex items-center space-x-1 ${
                              node.status === 'waiting_approval'
                                ? 'bg-amber-500/30 text-amber-200 border border-amber-400 animate-pulse font-bold'
                                : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                            }`}>
                              <span>🛡️</span>
                              <span>Gate</span>
                            </span>
                          )}
                          {node.result?.reused && (
                            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                              ⚡ Reused
                            </span>
                          )}
                          {((stepObj as any)?.tabular_data || node.result?.tabular_data) && (
                            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center space-x-1">
                              <span>📊</span>
                              <span>Table</span>
                            </span>
                          )}
                        </div>
                        <h4 className="text-xs font-bold text-slate-100 truncate group-hover:text-sky-400 transition-colors">
                          {node.name}
                        </h4>
                      </div>
                      <div className="p-1 rounded bg-slate-950/60 border border-slate-800">
                        {getStatusIcon(node)}
                      </div>
                    </div>

                    {/* Metadata & Quick Actions */}
                    <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
                      <div className="flex items-center space-x-2 truncate">
                        {node.tags && node.tags.length > 0 ? (
                          <span className="truncate text-slate-500 font-mono">
                            #{node.tags.join(' #')}
                          </span>
                        ) : (
                          <span className="text-slate-600 font-mono">Tier {node.layer + 1}</span>
                        )}
                      </div>
                      <div className="flex items-center space-x-1 shrink-0 ml-1">
                        {node.status === 'failed' && onResumeFromStep && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onResumeFromStep(node.name);
                            }}
                            className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-sky-500 hover:bg-sky-400 text-slate-950 text-[9px] font-mono font-bold transition-all hover:scale-105 active:scale-95 shadow-sm shadow-sky-500/40"
                            title={`Smart resume from ${node.name}`}
                          >
                            <RotateCcw className="h-2.5 w-2.5" />
                            <span>Resume</span>
                          </button>
                        )}
                        <span className="text-sky-400 group-hover:underline text-[9px] font-mono">
                          Inspect →
                        </span>
                      </div>
                    </div>
                  </div>
                </foreignObject>
              );
            })}
          </g>
        </svg>

        {/* Bottom Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur border border-slate-800 rounded-lg px-3 py-1.5 flex items-center space-x-3 text-[11px] font-medium text-slate-400 pointer-events-none">
          <div className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
            <span>Success</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-ping"></span>
            <span>Waiting Approval</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-cyan-400"></span>
            <span>Reused</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-sky-400 animate-pulse"></span>
            <span>Running</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-rose-400"></span>
            <span>Failed / Rejected</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-amber-400"></span>
            <span>Skipped</span>
          </div>
        </div>

        {/* Step Inspector Drawer for Deep Step / Validation Review */}
        {inspectedStep && (
          <StepDetailDrawer
            step={inspectedStep}
            onClose={() => setInspectedStep(null)}
            onResumeFromStep={onResumeFromStep}
            allSteps={steps}
            onSelectStep={(targetName) => {
              const found = steps.find((s) => s.name === targetName);
              if (found) setInspectedStep(found);
            }}
            runId={runId}
            env={env}
          />
        )}
      </div>
    </div>
  );

  // If fallback portal mode is activated (when native requestFullscreen was prevented), portal to document.body
  if (isFullscreenPortal) {
    return createPortal(dagContent, document.body);
  }

  return dagContent;
};
