import { StepSchema, StepResult } from '../types';

export interface DAGNode {
  id: string;
  name: string;
  order: number;
  parallel_group?: string;
  requires: string[];
  tags: string[];
  condition?: string;
  requires_approval?: boolean;
  approval_prompt?: string;
  // Layout computed positions
  x: number;
  y: number;
  width: number;
  height: number;
  layer: number;
  // Runtime status (optional if viewing schema or live run)
  result?: StepResult;
  status: 'pending' | 'running' | 'waiting_approval' | 'rejected' | 'success' | 'failed' | 'skipped';
}

export interface DAGEdge {
  id: string;
  sourceId: string;
  targetId: string;
  // Edge path coordinates
  path: string;
  active?: boolean;
  failed?: boolean;
}

export interface DAGTier {
  layer: number;
  title: string;
  isParallel: boolean;
  parallelGroup?: string;
  nodeCount: number;
  x: number;
}

export interface DAGLayoutResult {
  nodes: DAGNode[];
  edges: DAGEdge[];
  tiers: DAGTier[];
  width: number;
  height: number;
}

const NODE_WIDTH = 220;
const NODE_HEIGHT = 82;
const HORIZONTAL_GAP = 96;
const VERTICAL_GAP = 32;
const PADDING = 48;

/**
 * Computes layered topological positions for steps based on `requires`, `order`, and `parallel_group`.
 * Guarantees that parallel steps occupy the same vertical tier and fan-out/fan-in Bézier curves are drawn.
 */
export function computeDAGLayout(
  steps: (StepSchema | StepResult)[],
  activeStepName?: string | null
): DAGLayoutResult {
  if (!steps || steps.length === 0) {
    return { nodes: [], edges: [], tiers: [], width: 400, height: 200 };
  }

  // 1. Normalize steps into DAG nodes
  const nodeMap = new Map<string, DAGNode>();
  const normalizedNodes: DAGNode[] = [];

  steps.forEach((s, idx) => {
    const isResult = 'status' in s;
    const result = isResult ? (s as StepResult) : undefined;
    const schema = !isResult ? (s as StepSchema) : undefined;

    let status: DAGNode['status'] = 'pending';
    if (result) {
      status = result.status;
    }
    if (s.name === activeStepName && status !== 'waiting_approval') {
      status = 'running';
    }

    const requires = (s as any).requires ? [...(s as any).requires] : (schema?.requires ? [...schema.requires] : []);
    const parallel_group = (s as any).parallel_group ?? schema?.parallel_group;
    const order = (s as any).order ?? schema?.order ?? (idx + 1);
    const condition = (s as any).condition ?? schema?.condition;
    const tags = s.tags || [];
    const requires_approval = Boolean((s as any).requires_approval ?? schema?.requires_approval);
    const approval_prompt = (s as any).approval_prompt ?? schema?.approval_prompt;

    const node: DAGNode = {
      id: s.name,
      name: s.name,
      order,
      parallel_group,
      requires,
      tags,
      condition,
      requires_approval,
      approval_prompt,
      x: 0,
      y: 0,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      layer: 0,
      result,
      status,
    };

    nodeMap.set(s.name, node);
    normalizedNodes.push(node);
  });

  // 2. Assign layers (tiers) matching Valiant's batch execution model:
  // Step A: Consecutive steps sharing the same parallel_group form a parallel tier
  let currentLayer = 0;
  let currentGroup: string | null = null;

  normalizedNodes.forEach((node, idx) => {
    if (idx === 0) {
      node.layer = 0;
      currentGroup = node.parallel_group || null;
      return;
    }

    if (node.parallel_group && currentGroup === node.parallel_group) {
      // Same parallel group -> sits in the exact same layer!
      node.layer = currentLayer;
    } else {
      currentLayer++;
      node.layer = currentLayer;
      currentGroup = node.parallel_group || null;
    }
  });

  // Step B: Topologically enforce explicit dependencies and unify parallel groups
  let changed = true;
  let iterations = 0;
  while (changed && iterations < 25) {
    changed = false;
    iterations++;

    // Unify all nodes with the same parallel_group to the max layer of that group
    const groupMaxLayer = new Map<string, number>();
    normalizedNodes.forEach((node) => {
      if (node.parallel_group) {
        const cur = groupMaxLayer.get(node.parallel_group) ?? 0;
        groupMaxLayer.set(node.parallel_group, Math.max(cur, node.layer));
      }
    });

    normalizedNodes.forEach((node) => {
      if (node.parallel_group && groupMaxLayer.has(node.parallel_group)) {
        const maxL = groupMaxLayer.get(node.parallel_group)!;
        if (node.layer !== maxL) {
          node.layer = maxL;
          changed = true;
        }
      }
    });

    // Enforce dependency ordering: if target requires source, target.layer must be > source.layer
    normalizedNodes.forEach((targetNode) => {
      targetNode.requires.forEach((sourceName) => {
        const sourceNode = nodeMap.get(sourceName);
        if (sourceNode && targetNode.layer <= sourceNode.layer) {
          targetNode.layer = sourceNode.layer + 1;
          changed = true;
        }
      });
    });
  }

  // Group nodes into column layers
  const rawLayers: DAGNode[][] = [];
  normalizedNodes.forEach((node) => {
    while (rawLayers.length <= node.layer) {
      rawLayers.push([]);
    }
    rawLayers[node.layer].push(node);
  });

  // Filter out any accidentally empty layers and normalize layer indices
  const activeLayers: DAGNode[][] = rawLayers.filter((col) => col.length > 0);
  activeLayers.forEach((col, newIdx) => {
    col.forEach((node) => {
      node.layer = newIdx;
    });
  });

  // 3. Coordinate Assignment (Left-to-Right with generous vertical lane spacing)
  let maxColHeight = 0;

  activeLayers.forEach((column, colIdx) => {
    const colX = PADDING + colIdx * (NODE_WIDTH + HORIZONTAL_GAP);
    const totalHeight = column.length * NODE_HEIGHT + (column.length - 1) * VERTICAL_GAP;
    maxColHeight = Math.max(maxColHeight, totalHeight);

    column.forEach((node, rowIdx) => {
      node.x = colX;
      node.y = PADDING + rowIdx * (NODE_HEIGHT + VERTICAL_GAP);
    });
  });

  // Vertically center columns so single sequential steps align right at the midpoint of parallel tiers
  activeLayers.forEach((column) => {
    const colHeight = column.length * NODE_HEIGHT + (column.length - 1) * VERTICAL_GAP;
    const yOffset = (maxColHeight - colHeight) / 2;
    column.forEach((node) => {
      node.y += yOffset;
    });
  });

  // 4. Construct Edges
  const edges: DAGEdge[] = [];
  const edgeSet = new Set<string>();

  const addEdge = (sourceNode: DAGNode, targetNode: DAGNode) => {
    const edgeKey = `${sourceNode.name}->${targetNode.name}`;
    if (edgeSet.has(edgeKey)) return;
    edgeSet.add(edgeKey);

    const x1 = sourceNode.x + sourceNode.width;
    const y1 = sourceNode.y + sourceNode.height / 2;
    const x2 = targetNode.x;
    const y2 = targetNode.y + targetNode.height / 2;

    const deltaX = Math.max((x2 - x1) / 2, 40);
    const path = `M ${x1} ${y1} C ${x1 + deltaX} ${y1}, ${x2 - deltaX} ${y2}, ${x2} ${y2}`;

    const isSourceRunning = sourceNode.status === 'running';
    const isTargetRunning = targetNode.status === 'running';
    const hasFailed = sourceNode.status === 'failed';

    edges.push({
      id: edgeKey,
      sourceId: sourceNode.name,
      targetId: targetNode.name,
      path,
      active: isSourceRunning || isTargetRunning,
      failed: hasFailed,
    });
  };

  // Connect explicit dependencies first
  normalizedNodes.forEach((targetNode) => {
    targetNode.requires.forEach((sourceName) => {
      const sourceNode = nodeMap.get(sourceName);
      if (sourceNode) {
        addEdge(sourceNode, targetNode);
      }
    });
  });

  // For nodes without incoming edges: connect from the preceding tier (Fan-out / Fan-in)
  activeLayers.forEach((currentCol, colIdx) => {
    if (colIdx === 0) return;
    const prevCol = activeLayers[colIdx - 1];

    currentCol.forEach((targetNode) => {
      const hasIncoming = edges.some((e) => e.targetId === targetNode.name);
      if (!hasIncoming) {
        prevCol.forEach((sourceNode) => {
          addEdge(sourceNode, targetNode);
        });
      }
    });
  });

  // 5. Build Tier Metadata
  const tiers: DAGTier[] = activeLayers.map((column, layerIdx) => {
    const isParallel = column.length > 1;
    const parallelGroup = column.find((n) => n.parallel_group)?.parallel_group;
    const title = isParallel
      ? `Tier ${layerIdx + 1} • ${column.length} Parallel Lanes`
      : `Tier ${layerIdx + 1} • Sequential`;

    return {
      layer: layerIdx,
      title,
      isParallel,
      parallelGroup,
      nodeCount: column.length,
      x: PADDING + layerIdx * (NODE_WIDTH + HORIZONTAL_GAP),
    };
  });

  const totalWidth = PADDING * 2 + Math.max(activeLayers.length, 1) * (NODE_WIDTH + HORIZONTAL_GAP) - HORIZONTAL_GAP;
  const totalHeight = PADDING * 2 + Math.max(maxColHeight, NODE_HEIGHT);

  return {
    nodes: normalizedNodes,
    edges,
    tiers,
    width: Math.max(totalWidth, 780),
    height: Math.max(totalHeight, 460),
  };
}
