/**
 * 节点颜色映射工具
 * 根据关系类型推断节点维度并分配颜色
 */

import { getEntityTypeColor, normalizeEntityType } from './entityTypeColors';

// 关系类型 → 维度映射
const RELATION_TO_DIMENSION = {
    // 维度1：工程信息（红色系）
    '典型坝高': 'engineering',
    '所属环境': 'engineering',
    '所属地质': 'engineering',

    // 维度2：典型病害（绿色系）
    '常见缺陷': 'defect',
    '发生于': 'defect',

    // 维度3：病害成因（蓝色系）
    '主要病因': 'cause',
    '典型病因': 'cause',

    // 维度4：病害处置（灰色系）
    '处置措施': 'treatment',
};

const getEdgeSourceId = (edge) =>
    edge?.source_id ?? edge?.sourceId ?? edge?.source ?? edge?.from ?? edge?.start;

const getEdgeTargetId = (edge) =>
    edge?.target_id ?? edge?.targetId ?? edge?.target ?? edge?.to ?? edge?.end;

const getEdgeRelationType = (edge) =>
    edge?.type ?? edge?.r ?? edge?.relation ?? edge?.label ?? edge?.name ?? '';

const getNodeExplicitType = (node) => node?.type ?? node?.entity_type ?? node?.entityType;

const hasExplicitNodeTypes = (nodes = []) =>
    nodes.some((node) => node && getNodeExplicitType(node) !== undefined);

// 维度 → 颜色映射
export const DIMENSION_COLORS = {
    engineering: {
        key: 'engineering',
        label: '工程信息',
        main: '#ef4444',    // 红
        light: '#fca5a5',
        dark: '#b91c1c'
    },
    defect: {
        key: 'defect',
        label: '典型病害',
        main: '#22c55e',    // 绿
        light: '#86efac',
        dark: '#15803d'
    },
    cause: {
        key: 'cause',
        label: '病害成因',
        main: '#3b82f6',    // 蓝
        light: '#93c5fd',
        dark: '#1d4ed8'
    },
    treatment: {
        key: 'treatment',
        label: '病害处置',
        main: '#fbbf24',    // 黄
        light: '#fde68a',
        dark: '#f59e0b'
    },
    default: {
        key: 'default',
        label: '其他',
        main: '#f59e0b',    // 橙
        light: '#fcd34d',
        dark: '#b45309'
    },
};

const DIMENSION_PRIORITY = {
    treatment: 1,
    cause: 2,
    defect: 3,
    engineering: 4,
    default: 5,
};

const pickHigherPriorityDimension = (currentDimension, candidateDimension) => {
    const currentPriority = DIMENSION_PRIORITY[currentDimension] || DIMENSION_PRIORITY.default;
    const candidatePriority = DIMENSION_PRIORITY[candidateDimension] || DIMENSION_PRIORITY.default;
    return candidatePriority < currentPriority ? candidateDimension : currentDimension;
};

const inferNodeDimensionsFromEdges = (edges = []) => {
    const nodeDimensionMap = new Map();

    const applyNodeDimension = (nodeId, dimension) => {
        if (nodeId == null || !dimension || dimension === 'default') return;
        const key = String(nodeId);
        const prev = nodeDimensionMap.get(key) || 'default';
        nodeDimensionMap.set(key, pickHigherPriorityDimension(prev, dimension));
    };

    for (const edge of edges) {
        const relationType = getEdgeRelationType(edge);
        const dimension = getDimensionByRelation(relationType);
        if (dimension === 'default') continue;

        const sourceId = getEdgeSourceId(edge);
        const targetId = getEdgeTargetId(edge);

        // 与旧逻辑保持一致：源节点默认作为 defect 参与
        applyNodeDimension(sourceId, 'defect');

        // 目标节点根据关系维度赋予更具体类型
        if (dimension === 'treatment') {
            applyNodeDimension(targetId, 'treatment');
        } else if (dimension === 'cause') {
            applyNodeDimension(targetId, 'cause');
        } else if (dimension === 'engineering') {
            applyNodeDimension(targetId, 'engineering');
        }
    }

    return nodeDimensionMap;
};

// 获取所有维度列表（用于筛选器）
export function getDimensionList() {
    return Object.values(DIMENSION_COLORS);
}

/**
 * 根据关系类型获取维度
 * @param {string} relationType - 关系类型
 * @returns {string} 维度 key
 */
export function getDimensionByRelation(relationType) {
    return RELATION_TO_DIMENSION[relationType] || 'default';
}

/**
 * 获取维度对应的颜色
 * @param {string} dimension - 维度 key
 * @returns {object} 颜色对象 { main, light, dark }
 */
export function getDimensionColor(dimension) {
    return DIMENSION_COLORS[dimension] || DIMENSION_COLORS.default;
}

/**
 * 根据节点在边中的角色推断节点维度
 * 规则：
 * - 如果节点作为 "处置措施" 的尾节点 -> treatment
 * - 如果节点作为 "病因" 相关关系的尾节点 -> cause
 * - 如果节点作为 "缺陷/发生于" 的头节点 -> defect
 * - 如果节点作为 "典型坝高/所属环境/地质" 的尾节点 -> engineering
 * - 默认 -> default
 * 
 * @param {string} nodeId - 节点ID
 * @param {Array} edges - 边列表 [{ source_id, target_id, type }]
 * @returns {string} 维度 key
 */
export function inferNodeDimension(nodeId, edges) {
    const map = inferNodeDimensionsFromEdges(edges);
    return map.get(String(nodeId)) || 'default';
}

/**
 * 为所有节点构建颜色映射
 * @param {Array} nodes - 节点列表 [{ id, name, ... }]
 * @param {Array} edges - 边列表 [{ source_id, target_id, type }]
 * @returns {Map<string, { dimension: string, color: string }>}
 */
export function buildNodeColorMap(nodes, edges) {
    const colorMap = new Map();
    const useExplicitType = hasExplicitNodeTypes(nodes);
    const inferredNodeDimensions = useExplicitType ? null : inferNodeDimensionsFromEdges(edges);

    for (const node of nodes) {
        const nodeId = String(node.id);

        if (useExplicitType) {
            const typeKey = normalizeEntityType(getNodeExplicitType(node));
            const color = getEntityTypeColor(typeKey);

            colorMap.set(nodeId, {
                dimension: typeKey,
                color,
                lightColor: color,
            });
            continue;
        }

        const dimension = inferredNodeDimensions?.get(nodeId) || 'default';
        const colors = getDimensionColor(dimension);

        colorMap.set(nodeId, {
            dimension,
            color: colors.main,
            lightColor: colors.light,
        });
    }

    return colorMap;
}

/**
 * 根据维度过滤节点
 * @param {Array} nodes - 节点列表
 * @param {Array} edges - 边列表
 * @param {Array} hiddenDimensions - 要隐藏的维度列表
 * @returns {{ nodes: Array, edges: Array }} 过滤后的图数据
 */
export function filterByDimensions(nodes, edges, hiddenDimensions = []) {
    if (!hiddenDimensions.length) {
        return { nodes, edges };
    }

    const colorMap = buildNodeColorMap(nodes, edges);
    const hiddenSet = new Set(hiddenDimensions);

    // 过滤节点
    const filteredNodes = nodes.filter(node => {
        const nodeId = String(node.id);
        const info = colorMap.get(nodeId);
        return !info || !hiddenSet.has(info.dimension);
    });

    // 获取保留的节点ID集合
    const remainingNodeIds = new Set(filteredNodes.map(n => String(n.id)));

    // 过滤边（两端节点都需要保留）
    const filteredEdges = edges.filter(edge => {
        const s = getEdgeSourceId(edge);
        const t = getEdgeTargetId(edge);
        if (s == null || t == null) return false;
        return remainingNodeIds.has(String(s)) && remainingNodeIds.has(String(t));
    });

    return { nodes: filteredNodes, edges: filteredEdges };
}
