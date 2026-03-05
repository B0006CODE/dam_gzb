<template>
  <div class="g6-graph-container" ref="rootEl">
    <div class="g6-canvas" ref="container"></div>
    <div class="slots">
      <div v-if="$slots.top" class="overlay top">
        <slot name="top" />
      </div>
      <div class="content">
        <slot name="content" />
      </div>
      <div v-if="$slots.bottom" class="overlay bottom">
        <slot name="bottom" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { Graph } from '@antv/g6';
import { buildNodeColorMap, filterByDimensions } from '@/utils/nodeColorMapper';

const props = defineProps({
  graphData: { type: Object, required: true, default: () => ({ nodes: [], edges: [] }) },
  labelField: { type: String, default: 'name' },
  autoFit: { type: Boolean, default: true },
  autoResize: { type: Boolean, default: true },
  layoutOptions: { type: Object, default: () => ({}) },
  nodeStyleOptions: { type: Object, default: () => ({}) },
  edgeStyleOptions: { type: Object, default: () => ({}) },
  enableFocusNeighbor: { type: Boolean, default: true },
  sizeByDegree: { type: Boolean, default: true },
  highlightKeywords: { type: Array, default: () => [] },
  hiddenDimensions: { type: Array, default: () => [] }
});

const emit = defineEmits(['ready', 'node-click', 'edge-click', 'canvas-click', 'data-rendered']);

const container = ref(null);
const rootEl = ref(null);
let graphInstance = null;
let initTimer = null;
let renderQueued = false;
let queuedForceRelayout = false;
let lastTopologyKey = '';

const selectedSeedNodeIds = new Set();
const highlightedNodeIds = new Set();
const highlightedEdgeIds = new Set();
const inactiveNodeIds = new Set();
const inactiveEdgeIds = new Set();

const normalizedKeywords = computed(() =>
  (props.highlightKeywords || [])
    .filter(Boolean)
    .map((kw) => String(kw).toLowerCase())
);

const getEdgeSourceId = (edge) =>
  edge?.source_id ?? edge?.sourceId ?? edge?.source ?? edge?.from ?? edge?.start;

const getEdgeTargetId = (edge) =>
  edge?.target_id ?? edge?.targetId ?? edge?.target ?? edge?.to ?? edge?.end;

const hasElement = (id) => {
  if (!graphInstance || id == null) return false;
  try {
    return !!graphInstance.getElementData?.(String(id));
  } catch {
    return false;
  }
};

const applyCumulativeHighlights = async () => {
  if (!graphInstance) return;

  const prevSelected = new Set(selectedSeedNodeIds);
  const prevHighlightedNodes = new Set(highlightedNodeIds);
  const prevHighlightedEdges = new Set(highlightedEdgeIds);
  const prevInactiveNodes = new Set(inactiveNodeIds);
  const prevInactiveEdges = new Set(inactiveEdgeIds);

  const existingSeeds = Array.from(prevSelected).filter((id) => {
    try {
      return !!graphInstance.getNodeData?.(id);
    } catch {
      return false;
    }
  });

  selectedSeedNodeIds.clear();
  existingSeeds.forEach((id) => selectedSeedNodeIds.add(id));

  const getNodeStateCode = (id, selectedSet, activeSet, inactiveSet) => {
    if (selectedSet.has(id)) return 2;
    if (activeSet.has(id)) return 1;
    if (inactiveSet.has(id)) return -1;
    return 0;
  };

  const getEdgeStateCode = (id, activeSet, inactiveSet) => {
    if (activeSet.has(id)) return 1;
    if (inactiveSet.has(id)) return -1;
    return 0;
  };

  const nodeStateFromCode = (code) => {
    if (code === 2) return ['selected'];
    if (code === 1) return ['active'];
    if (code === -1) return ['inactive'];
    return [];
  };

  const edgeStateFromCode = (code) => {
    if (code === 1) return ['active'];
    if (code === -1) return ['inactive'];
    return [];
  };

  if (selectedSeedNodeIds.size === 0) {
    const updates = {};
    [...prevSelected, ...prevHighlightedNodes, ...prevHighlightedEdges, ...prevInactiveNodes, ...prevInactiveEdges].forEach(
      (id) => {
        if (hasElement(id)) updates[id] = [];
      }
    );

    highlightedNodeIds.clear();
    highlightedEdgeIds.clear();
    inactiveNodeIds.clear();
    inactiveEdgeIds.clear();

    if (Object.keys(updates).length > 0) {
      await graphInstance.setElementState(updates, false);
    }
    return;
  }

  const nextHighlightedNodes = new Set();
  const nextHighlightedEdges = new Set();

  selectedSeedNodeIds.forEach((seedId) => {
    const edges = graphInstance.getRelatedEdgesData?.(seedId, 'both') || [];
    edges.forEach((edge) => {
      const edgeId = edge?.id != null ? String(edge.id) : '';
      if (edgeId) nextHighlightedEdges.add(edgeId);
      const sourceId = edge?.source != null ? String(edge.source) : '';
      const targetId = edge?.target != null ? String(edge.target) : '';
      if (sourceId && !selectedSeedNodeIds.has(sourceId)) nextHighlightedNodes.add(sourceId);
      if (targetId && !selectedSeedNodeIds.has(targetId)) nextHighlightedNodes.add(targetId);
    });
  });

  const graphData = graphInstance.getData?.() || {};
  const allNodeIds = (graphData.nodes || []).map((n) => String(n.id));
  const allEdgeIds = (graphData.edges || []).map((e) => String(e.id));

  const focusNodeIds = new Set([...selectedSeedNodeIds, ...nextHighlightedNodes]);
  const nextInactiveNodes = new Set(allNodeIds.filter((id) => !focusNodeIds.has(id)));
  const nextInactiveEdges = new Set(allEdgeIds.filter((id) => !nextHighlightedEdges.has(id)));

  const updates = {};

  const candidateNodeIds = new Set([...allNodeIds, ...prevSelected, ...prevHighlightedNodes, ...prevInactiveNodes]);
  candidateNodeIds.forEach((id) => {
    const prevCode = getNodeStateCode(id, prevSelected, prevHighlightedNodes, prevInactiveNodes);
    const nextCode = getNodeStateCode(id, selectedSeedNodeIds, nextHighlightedNodes, nextInactiveNodes);
    if (prevCode === nextCode) return;
    if (!hasElement(id)) return;
    updates[id] = nodeStateFromCode(nextCode);
  });

  const candidateEdgeIds = new Set([...allEdgeIds, ...prevHighlightedEdges, ...prevInactiveEdges]);
  candidateEdgeIds.forEach((id) => {
    const prevCode = getEdgeStateCode(id, prevHighlightedEdges, prevInactiveEdges);
    const nextCode = getEdgeStateCode(id, nextHighlightedEdges, nextInactiveEdges);
    if (prevCode === nextCode) return;
    if (!hasElement(id)) return;
    updates[id] = edgeStateFromCode(nextCode);
  });

  highlightedNodeIds.clear();
  highlightedEdgeIds.clear();
  nextHighlightedNodes.forEach((id) => highlightedNodeIds.add(id));
  nextHighlightedEdges.forEach((id) => highlightedEdgeIds.add(id));

  inactiveNodeIds.clear();
  inactiveEdgeIds.clear();
  nextInactiveNodes.forEach((id) => inactiveNodeIds.add(id));
  nextInactiveEdges.forEach((id) => inactiveEdgeIds.add(id));

  if (Object.keys(updates).length > 0) {
    await graphInstance.setElementState(updates, false);
  }
};

const addSeedHighlight = async (id) => {
  if (!graphInstance || id == null) return;
  const seedId = String(id);
  if (!seedId) return;
  selectedSeedNodeIds.add(seedId);
  await applyCumulativeHighlights();
};

const clearSeedHighlights = async () => {
  const updates = {};
  [
    ...selectedSeedNodeIds,
    ...highlightedNodeIds,
    ...highlightedEdgeIds,
    ...inactiveNodeIds,
    ...inactiveEdgeIds,
  ].forEach((id) => {
    if (hasElement(id)) updates[id] = [];
  });
  selectedSeedNodeIds.clear();
  highlightedNodeIds.clear();
  highlightedEdgeIds.clear();
  inactiveNodeIds.clear();
  inactiveEdgeIds.clear();
  if (graphInstance && Object.keys(updates).length > 0) {
    await graphInstance.setElementState(updates, false);
  }
};

const textMeasureCtx = (() => {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  return canvas.getContext('2d');
})();

const measureTextWidth = (text, font) => {
  if (!textMeasureCtx) return text.length * 12;
  textMeasureCtx.font = font;
  return textMeasureCtx.measureText(text || '').width;
};

const wrapText = (text, maxWidth, font) => {
  if (!text) return [''];
  if (!textMeasureCtx) return [text];

  textMeasureCtx.font = font;
  const lines = [];
  let current = '';

  for (const ch of text) {
    const tentative = current + ch;
    if (textMeasureCtx.measureText(tentative).width <= maxWidth || !current) {
      current = tentative;
    } else {
      lines.push(current);
      current = ch;
    }
  }
  if (current) lines.push(current);
  return lines;
};

// 自适应尺寸与包裹的边界参数
const MIN_NODE_SIZE = 52;
const MAX_NODE_SIZE = 240;
const WRAP_MIN_WIDTH = 32;
const WRAP_MAX_WIDTH = 260;
const TEXT_PADDING = 14;
const FONT_SIZE_MAX = 14;
const FONT_SIZE_MIN = 11;

const HASH_OFFSET_BASIS = 2166136261;
const HASH_PRIME = 16777619;

const hashInto = (hash, value) => {
  const text = String(value ?? '');
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, HASH_PRIME);
  }
  hash ^= 124;
  return Math.imul(hash, HASH_PRIME);
};

const buildTopologyKey = (data) => {
  const nodes = data?.nodes || [];
  const edges = data?.edges || [];
  let hash = HASH_OFFSET_BASIS;

  nodes.forEach((node) => {
    hash = hashInto(hash, node?.id);
  });
  hash = hashInto(hash, '::');
  edges.forEach((edge) => {
    hash = hashInto(hash, edge?.id);
    hash = hashInto(hash, edge?.source);
    hash = hashInto(hash, edge?.target);
  });

  return `${nodes.length}:${edges.length}:${hash >>> 0}`;
};

const resolveLayoutType = () => {
  const rawType = String(props.layoutOptions?.type || 'force').toLowerCase();
  const supportedLayoutTypes = new Set(['force', 'radial', 'concentric', 'circular']);
  return supportedLayoutTypes.has(rawType) ? rawType : 'force';
};

const isRingLikeLayoutType = (layoutType) => layoutType === 'concentric' || layoutType === 'circular';

const getLayoutViewport = () => {
  const [graphWidth = 0, graphHeight = 0] = graphInstance?.getSize?.() || [];
  const rawWidth = container.value?.offsetWidth || graphWidth || 960;
  const rawHeight = container.value?.offsetHeight || graphHeight || 640;
  const safeWidth = Math.max(320, rawWidth);
  const safeHeight = Math.max(320, rawHeight);
  const shortSide = Math.min(safeWidth, safeHeight);
  const layoutSide = Math.max(320, shortSide * 0.9);

  return {
    width: safeWidth,
    height: safeHeight,
    side: layoutSide,
    center: [safeWidth / 2, safeHeight / 2],
  };
};

const inferRadialFocusNodeId = () => {
  const explicitFocusNode = props.layoutOptions?.focusNode ?? props.layoutOptions?.focusNodeId;
  if (explicitFocusNode != null && String(explicitFocusNode).trim()) {
    return String(explicitFocusNode);
  }

  const { nodes = [], edges = [] } = filterByDimensions(
    props.graphData.nodes || [],
    props.graphData.edges || [],
    props.hiddenDimensions
  );
  if (!nodes.length) return undefined;

  const degrees = new Map(nodes.map((node) => [String(node.id), 0]));
  edges.forEach((edge) => {
    const sourceRaw = getEdgeSourceId(edge);
    const targetRaw = getEdgeTargetId(edge);
    if (sourceRaw == null || targetRaw == null) return;
    const sourceId = String(sourceRaw);
    const targetId = String(targetRaw);
    if (degrees.has(sourceId)) degrees.set(sourceId, (degrees.get(sourceId) || 0) + 1);
    if (degrees.has(targetId)) degrees.set(targetId, (degrees.get(targetId) || 0) + 1);
  });

  let focusNodeId = String(nodes[0].id);
  let maxDegree = -1;
  degrees.forEach((degree, nodeId) => {
    if (degree > maxDegree) {
      maxDegree = degree;
      focusNodeId = nodeId;
    }
  });

  return focusNodeId;
};

const getLayoutConfig = (nodeSizeById) => {
  const { type: _ignoredType, ...userOptions } = props.layoutOptions || {};
  const layoutType = resolveLayoutType();
  const isRingLayout = isRingLikeLayoutType(layoutType);
  const nodeCount = nodeSizeById?.size || 0;
  const dynamicMaxIteration = Math.max(240, Math.min(1200, Math.max(nodeCount, 40) * 8));
  const { side, center } = getLayoutViewport();
  const nodeSizeValues = nodeSizeById ? Array.from(nodeSizeById.values()) : [];
  const avgNodeSize = nodeSizeValues.length
    ? nodeSizeValues.reduce((sum, size) => sum + Number(size || 0), 0) / nodeSizeValues.length
    : 64;

  const getNodeSize = (node, fallbackId) => {
    if (fallbackId != null && nodeSizeById?.get?.(String(fallbackId))) {
      return nodeSizeById.get(String(fallbackId));
    }
    const dataSize = node?.data?.size ?? node?.data?.style?.size;
    if (typeof dataSize === 'number') return dataSize;
    if (Array.isArray(dataSize)) return Math.max(...dataSize);
    if (dataSize && typeof dataSize === 'object' && dataSize.width && dataSize.height) {
      return Math.max(dataSize.width, dataSize.height);
    }
    return 64;
  };

  const defaultLinkDistance = (edge, source, target) => {
    const sourceId = source?.id ?? edge?.source;
    const targetId = target?.id ?? edge?.target;
    const sourceSize = getNodeSize(source, sourceId);
    const targetSize = getNodeSize(target, targetId);
    const min = (sourceSize + targetSize) / 2 + 220;
    return Math.max(300, min);
  };

  if (layoutType === 'radial') {
    const focusNode = inferRadialFocusNodeId();
    const radialStep = Math.max(92, Math.min(220, Math.round(side * 0.19)));
    return {
      type: 'radial',
      center,
      width: side,
      height: side,
      unitRadius: radialStep,
      preventOverlap: true,
      strictRadial: false,
      maxIteration: dynamicMaxIteration,
      nodeSize: (node) => node?.data?.size ?? node?.data?.style?.size ?? 32,
      animation: false,
      ...userOptions,
      type: 'radial',
      ...(focusNode ? { focusNode } : {}),
      animation: false,
    };
  }

  if (layoutType === 'concentric') {
    const ringNodeSpacing = Math.max(
      10,
      Math.min(30, Math.round(avgNodeSize * (nodeCount > 180 ? 0.16 : 0.2)))
    );
    return {
      type: 'concentric',
      center,
      width: side,
      height: side,
      preventOverlap: true,
      equidistant: true,
      nodeSize: (node) => node?.data?.size ?? node?.data?.style?.size ?? 32,
      nodeSpacing: ringNodeSpacing,
      startAngle: -Math.PI / 2,
      clockwise: true,
      sortBy: '__degree',
      maxLevelDiff: nodeCount > 220 ? 3 : 2,
      animation: false,
      ...userOptions,
      type: 'concentric',
      animation: false,
    };
  }

  if (layoutType === 'circular') {
    const circleRadius = Math.max(120, Math.min(side * 0.44, 560));
    const circularNodeSpacing = Math.max(
      8,
      Math.min(24, Math.round(avgNodeSize * (nodeCount > 180 ? 0.14 : 0.18)))
    );
    return {
      type: 'circular',
      center,
      width: side,
      height: side,
      radius: circleRadius,
      ordering: 'topology',
      nodeSize: (node) => node?.data?.size ?? node?.data?.style?.size ?? 32,
      nodeSpacing: circularNodeSpacing,
      angleRatio: nodeCount > 160 ? 0.95 : 1,
      startAngle: -Math.PI / 2,
      clockwise: true,
      animation: false,
      ...userOptions,
      type: 'circular',
      animation: false,
    };
  }

  return {
    type: 'force',
    linkDistance: defaultLinkDistance,
    nodeStrength: 2200,
    edgeStrength: 35,
    preventOverlap: true,
    collideStrength: 1,
    nodeSize: (node) => node?.data?.size ?? node?.data?.style?.size ?? 32,
    nodeSpacing: isRingLayout ? 60 : 48,
    damping: 0.9,
    maxSpeed: 120,
    gravity: 2,
    factor: 2,
    coulombDisScale: 0.004,
    interval: 0.02,
    maxIteration: dynamicMaxIteration,
    minMovement: 0.1,
    animation: false,
    ...userOptions,
    type: 'force',
    animation: false,
  };
};

const buildGraphData = () => {
  const layoutType = resolveLayoutType();
  const isRingLayout = isRingLikeLayoutType(layoutType);
  const { nodes = [], edges = [] } = filterByDimensions(
    props.graphData.nodes || [],
    props.graphData.edges || [],
    props.hiddenDimensions
  );

  const isDenseGraph = edges.length >= 300;
  const shouldCompactEdges = isDenseGraph || isRingLayout;
  const maxNodeSize = isRingLayout ? 136 : MAX_NODE_SIZE;
  const minNodeSize = isRingLayout ? 44 : MIN_NODE_SIZE;

  const colorMap = buildNodeColorMap(nodes, edges);
  const degrees = new Map();
  nodes.forEach((n) => degrees.set(String(n.id), 0));
  edges.forEach((edge) => {
    const s = getEdgeSourceId(edge);
    const t = getEdgeTargetId(edge);
    if (s == null || t == null) return;
    const sId = String(s);
    const tId = String(t);
    if (degrees.has(sId)) degrees.set(sId, (degrees.get(sId) || 0) + 1);
    if (degrees.has(tId)) degrees.set(tId, (degrees.get(tId) || 0) + 1);
  });

  const keywordSet = normalizedKeywords.value;
  const matchedNodes = new Set();

  const normalizeLabel = (node) => {
    const label =
      node?.[props.labelField] ||
      node?.name ||
      node?.label ||
      node?.id ||
      '';
    return String(label);
  };

  const nodeData = nodes.map((node) => {
    const id = String(node.id);
    const label = normalizeLabel(node);
    const isMatched =
      keywordSet.length > 0 &&
      keywordSet.some((kw) => label.toLowerCase().includes(kw));

    if (isMatched) matchedNodes.add(id);

    const degree = degrees.get(id) || 0;

    // 文本驱动的自适应尺寸，必要时缩小字体以适配最大直径
    const computeLayout = (diameter, fontSize, degreeBase) => {
      const wrapWidth = Math.max(WRAP_MIN_WIDTH, Math.min(WRAP_MAX_WIDTH, diameter * 0.72));
      const fontSpec = `700 ${fontSize}px Microsoft YaHei, sans-serif`;
      const lines = wrapText(label, wrapWidth, fontSpec);
      const maxLineWidth = Math.max(...lines.map((l) => measureTextWidth(l, fontSpec)), fontSize);
      const textHeight = lines.length * (fontSize + 4);
      const neededByWidth = maxLineWidth / 0.72 + TEXT_PADDING;
      const neededByHeight = textHeight / 0.72 + TEXT_PADDING;
      const requiredDiameter = Math.max(degreeBase, neededByWidth, neededByHeight);
      return { wrapWidth, lines, requiredDiameter, fontSize };
    };

    let fontSize = FONT_SIZE_MAX;
    let degreeBase = props.sizeByDegree ? Math.min(48 + degree * 1.2, 110) : 60;
    let layout = computeLayout(Math.max(degreeBase, minNodeSize), fontSize, degreeBase);
    if (layout.requiredDiameter > degreeBase + 1) {
      layout = computeLayout(layout.requiredDiameter, fontSize, degreeBase);
    }
    // 如果仍超出最大直径，逐步缩小字体重算，直到适配或到达最小字号
    while (layout.requiredDiameter > maxNodeSize && fontSize > FONT_SIZE_MIN) {
      fontSize -= 1;
      degreeBase = props.sizeByDegree ? Math.min(48 + degree * 1.2, 110) : 60;
      layout = computeLayout(Math.max(degreeBase, minNodeSize), fontSize, degreeBase);
      if (layout.requiredDiameter > degreeBase + 1) {
        layout = computeLayout(layout.requiredDiameter, fontSize, degreeBase);
      }
    }

    const wrappedLabel = layout.lines.join('\n');
    const nodeSize = Math.max(minNodeSize, Math.min(maxNodeSize, layout.requiredDiameter));
    const colorInfo = colorMap.get(id) || { color: '#3b82f6', dimension: 'default' };
    const muted = keywordSet.length > 0 && !isMatched;
    const baseLabelOpacity = isDenseGraph ? 0.88 : 0.98;
    const labelOpacity = muted ? 0.48 : baseLabelOpacity;
    const nodeOpacity = muted ? 0.3 : 1;

    return {
      id,
      data: {
        ...node,
        __degree: degree
      },
      size: nodeSize,
      style: {
        size: nodeSize,
        r: nodeSize / 2,
        fill: colorInfo.color,
        fillOpacity: nodeOpacity,
        stroke: isMatched ? '#e0ecff' : '#c2d7ff',
        lineWidth: isMatched ? 2 : 1.3,
        strokeOpacity: nodeOpacity,
        shadowColor: 'rgba(0, 0, 0, 0.18)',
        shadowBlur: 10,
        shadowOffsetY: 3,
        labelText: wrappedLabel,
        labelPlacement: 'center',
        labelTextAlign: 'center',
        labelFill: '#ffffff',
        labelOpacity,
        labelFillOpacity: labelOpacity,
        labelFontSize: fontSize,
        labelFontWeight: 700,
        labelFontFamily: 'Microsoft YaHei, sans-serif',
        labelIsBillboard: false, // 随缩放缩放，避免缩小时文字溢出
        labelWordWrap: true,
        labelWordWrapWidth: layout.wrapWidth,
        labelMaxWidth: layout.wrapWidth,
        labelMaxLines: Math.max(layout.lines.length, 1),
        labelTextOverflow: 'clip',
        labelLineHeight: fontSize + 4,
        labelPadding: 4,
        labelBackground: false,
        ...props.nodeStyleOptions
      }
    };
  });

  const parallelOffsetByEdgeIdx = new Map();
  const parallelGroups = new Map();
  edges.forEach((edge, idx) => {
    const sourceRaw = getEdgeSourceId(edge);
    const targetRaw = getEdgeTargetId(edge);
    if (sourceRaw == null || targetRaw == null) return;
    const sourceId = String(sourceRaw);
    const targetId = String(targetRaw);
    if (!degrees.has(sourceId) || !degrees.has(targetId)) return;

    const pairKey =
      sourceId < targetId ? `${sourceId}::${targetId}` : `${targetId}::${sourceId}`;
    const group = parallelGroups.get(pairKey) || [];
    group.push(idx);
    parallelGroups.set(pairKey, group);
  });

  parallelGroups.forEach((indices) => {
    if (!Array.isArray(indices) || indices.length <= 1) return;
    const mid = (indices.length - 1) / 2;
    const step = 22;
    indices.forEach((edgeIdx, pos) => {
      parallelOffsetByEdgeIdx.set(edgeIdx, (pos - mid) * step);
    });
  });

  const edgeData = edges
    .map((edge, idx) => {
      const sourceRaw = getEdgeSourceId(edge);
      const targetRaw = getEdgeTargetId(edge);
      if (sourceRaw == null || targetRaw == null) return null;

      const sourceId = String(sourceRaw);
      const targetId = String(targetRaw);
      if (!degrees.has(sourceId) || !degrees.has(targetId)) return null;

      const connectsHighlight =
        keywordSet.length === 0 ||
        matchedNodes.has(sourceId) ||
        matchedNodes.has(targetId);

      // 优先使用 edges.properties 中更可读的关系文本（与旧 Sigma 版本一致）
      const propsLabel = (() => {
        const props = edge?.properties;
        if (!props || typeof props !== 'object') return '';
        return (
          props.keywords ||
          props.relation ||
          props.label ||
          props.name ||
          props.description ||
          ''
        );
      })();

      let clampedLabelText = '';
      if (!shouldCompactEdges) {
        const rawLabel =
          propsLabel || edge.r || edge.relation || edge.label || edge.name || edge.type || '';

        // 优先显示中文；如果没有中文，则回退显示英文/符号（例如 OCCUR_AT -> OCCUR AT）
        const rawLabelText = String(rawLabel || '').trim();
        const chineseOnly = (rawLabelText.match(/[\u4e00-\u9fa5]+/g) || []).join('');
        const fallback = rawLabelText.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
        const labelText = chineseOnly || fallback;
        clampedLabelText = labelText.length > 24 ? `${labelText.slice(0, 24)}…` : labelText;
      }

      const curveOffset = parallelOffsetByEdgeIdx.get(idx) || 0;
      const labelOffsetY = Math.max(-16, Math.min(16, curveOffset * 0.35));

      return {
        id: edge.id ? String(edge.id) : `e-${idx}-${sourceId}-${targetId}`,
        source: sourceId,
        target: targetId,
        type: isRingLayout ? 'quadratic' : 'line',
        data: edge,
        style: {
          stroke: '#ffffff',
          strokeOpacity:
            keywordSet.length === 0
              ? shouldCompactEdges
                ? 0.16
                : 0.32
              : connectsHighlight
                ? (isRingLayout ? 0.46 : 0.65)
                : 0.14,
          lineWidth:
            keywordSet.length === 0
              ? shouldCompactEdges
                ? 1
                : 1.4
              : connectsHighlight
                ? (isRingLayout ? 1.4 : 1.9)
                : 1.2,
          endArrow: false,
          ...(isRingLayout ? { curveOffset: curveOffset || ((idx % 4) - 1.5) * 10 } : {}),
          ...(labelOffsetY ? { labelOffsetY } : {}),
          labelText: clampedLabelText,
          labelPlacement: 'center',
          labelFill: '#ffffff',
          labelFontSize: 10,
          labelOpacity: shouldCompactEdges
            ? 0
            : keywordSet.length === 0
              ? 0.9
              : connectsHighlight
                ? 0.95
                : 0.5,
          labelBackground: false,
          labelBackgroundFill: 'rgba(15, 31, 61, 0.72)',
          labelBackgroundOpacity: 0.35,
          labelPadding: 3,
          labelAutoRotate: false,
          labelTextAlign: 'center',
          labelTextBaseline: 'middle',
          ...props.edgeStyleOptions
        }
      };
    })
    .filter(Boolean);

  return { nodes: nodeData, edges: edgeData };
};

const applyGraphData = async ({ forceRelayout = false } = {}) => {
  if (!graphInstance) return;

  const data = buildGraphData();
  const topologyKey = buildTopologyKey(data);
  const topologyChanged = forceRelayout || topologyKey !== lastTopologyKey;
  graphInstance.setData(data);
  const nodeSizeById = new Map(
    (data.nodes || []).map((n) => [String(n.id), n?.size || n?.style?.size || 32])
  );
  if (topologyChanged) {
    graphInstance.setLayout(getLayoutConfig(nodeSizeById));
  }
  await graphInstance.render();
  lastTopologyKey = topologyKey;
  if (selectedSeedNodeIds.size > 0) {
    await applyCumulativeHighlights();
  }
  if (topologyChanged && props.autoFit && typeof graphInstance.fitView === 'function') {
    const fitPadding = isRingLikeLayoutType(resolveLayoutType()) ? 72 : 32;
    await graphInstance.fitView({ padding: fitPadding }, false);
  }
  emit('data-rendered');
};

const queueApplyGraphData = ({ forceRelayout = false } = {}) => {
  if (forceRelayout) queuedForceRelayout = true;
  if (renderQueued) return;
  renderQueued = true;

  nextTick(async () => {
    renderQueued = false;
    const useForceRelayout = queuedForceRelayout;
    queuedForceRelayout = false;
    try {
      await applyGraphData({ forceRelayout: useForceRelayout });
    } catch (error) {
      console.error('applyGraphData failed:', error);
    }
  });
};

const bindEvents = () => {
  if (!graphInstance) return;

  graphInstance.on('node:click', (event) => {
    const id = event?.target?.id;
    if (id == null) return;
    emit('node-click', { id, data: graphInstance.getNodeData(id) });
    if (props.enableFocusNeighbor && graphInstance.focusElement) {
      graphInstance.focusElement(id, { duration: 200 });
    }
    if (props.enableFocusNeighbor) {
      void addSeedHighlight(id);
    }
  });

  graphInstance.on('edge:click', (event) => {
    const id = event?.target?.id;
    if (id == null) return;
    emit('edge-click', { id, data: graphInstance.getEdgeData(id) });
  });

  graphInstance.on('canvas:click', () => {
    emit('canvas-click');
    if (props.enableFocusNeighbor && graphInstance.focusElement) {
      graphInstance.focusElement([], { duration: 150 });
    }
    void clearSeedHighlights();
  });
};

const initGraph = () => {
  if (!container.value) return;
  const { offsetWidth: width, offsetHeight: height } = container.value;

  if (width === 0 || height === 0) {
    initTimer = window.setTimeout(initGraph, 200);
    return;
  }

  if (graphInstance) {
    graphInstance.destroy();
    graphInstance = null;
  }

  graphInstance = new Graph({
    container: container.value,
    width,
    height,
    autoFit: props.autoFit ? 'view' : undefined,
    autoResize: props.autoResize,
    background: '#0f172a',
    animation: false,
    zoomRange: [0.15, 5],
    behaviors: [
      'drag-canvas',
      'zoom-canvas',
      {
        type: 'drag-element',
        key: 'drag-element',
        animation: false,
        dropEffect: 'none',
        hideEdge: 'all',
        state: '__drag_selected__'
      }
    ].filter(Boolean),
    node: {
      type: 'circle',
      state: {
        inactive: {
          fillOpacity: 0.3,
          strokeOpacity: 0.3,
          labelOpacity: 0.4,
          labelFill: '#ffffff',
          labelFillOpacity: 0.4,
        },
        active: {
          fillOpacity: 1,
          strokeOpacity: 1,
          labelOpacity: 1,
          labelFill: '#ffffff',
          labelFillOpacity: 1,
          lineWidth: 2.4,
          stroke: '#ffffff',
        },
        selected: {
          fillOpacity: 1,
          strokeOpacity: 1,
          labelOpacity: 1,
          labelFill: '#ffffff',
          labelFillOpacity: 1,
          lineWidth: 4,
          stroke: '#ffffff',
        },
      },
    },
    edge: {
      type: 'line',
      style: {
        increasedLineWidthForHitTesting: 6,
      },
      state: {
        inactive: {
          stroke: '#ffffff',
          strokeOpacity: 0.22,
          labelFill: '#ffffff',
          labelOpacity: 0.35,
          labelBackground: false,
          endArrow: false,
        },
        active: {
          stroke: '#ffffff',
          strokeOpacity: 0.85,
          lineWidth: 2.2,
          labelFill: '#ffffff',
          labelOpacity: 0.85,
          labelBackground: false,
          zIndex: 1,
        },
        selected: {
          stroke: '#ffffff',
          strokeOpacity: 0.95,
          lineWidth: 3,
          labelFill: '#ffffff',
          labelOpacity: 0.95,
          labelBackground: false,
          zIndex: 2,
        },
      },
    },
    layout: getLayoutConfig()
  });

  bindEvents();
  queueApplyGraphData({ forceRelayout: true });
  emit('ready', { graph: graphInstance });
};

watch(
  () => [props.graphData?.nodes, props.graphData?.edges],
  () => queueApplyGraphData()
);

watch(
  () => [props.hiddenDimensions, props.layoutOptions],
  () => queueApplyGraphData({ forceRelayout: true })
);

watch(
  () => props.highlightKeywords,
  () => queueApplyGraphData()
);

onMounted(() => {
  nextTick(() => initGraph());
});

onUnmounted(() => {
  if (initTimer) window.clearTimeout(initTimer);
  if (graphInstance) {
    graphInstance.destroy();
    graphInstance = null;
  }
});

const refreshGraph = () => queueApplyGraphData({ forceRelayout: true });
const fitView = () => {
  const fitPadding = isRingLikeLayoutType(resolveLayoutType()) ? 72 : 32;
  return graphInstance?.fitView?.({ padding: fitPadding });
};
const fitCenter = () => graphInstance?.fitCenter?.({ duration: 200 });
const getInstance = () => ({ graph: graphInstance });
const focusNode = (id) => graphInstance?.focusElement?.(id, { duration: 200 });
const clearFocus = () => graphInstance?.focusElement?.([], { duration: 150 });
const applyHighlightKeywords = () => queueApplyGraphData();
const clearHighlights = () => queueApplyGraphData();

defineExpose({
  refreshGraph,
  fitView,
  fitCenter,
  getInstance,
  focusNode,
  clearFocus,
  applyHighlightKeywords,
  clearHighlights
});
</script>

<style lang="less" scoped>
.g6-graph-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: radial-gradient(ellipse at 20% 15%, rgba(78, 134, 204, 0.15) 0%, rgba(12, 28, 51, 0) 45%),
    linear-gradient(135deg, #0f1f3d 0%, #0c1730 100%);
  overflow: hidden;

  .g6-canvas {
    width: 100%;
    height: 100%;
  }

  .slots {
    pointer-events: none;
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    z-index: 10;

    .overlay {
      width: 100%;
      flex-shrink: 0;
      flex-grow: 0;
      pointer-events: auto;

      &.top {
        top: 0;
      }
      &.bottom {
        bottom: 0;
      }
    }

    .content {
      pointer-events: none;
      flex: 1;
    }

    .content * {
      pointer-events: none;
    }
  }
}
</style>
