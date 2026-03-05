<template>
  <div class="knowledge-graph-viewer">
    <div class="control-panel" v-if="!props.hideControls">
      <div class="database-section">
        <a-select
          v-if="!props.hideDbSelector"
          v-model:value="selectedDatabase"
          placeholder="选择数据库"
          size="small"
          style="width: 160px; margin-right: 6px"
          :loading="loadingDatabases"
          @change="onDatabaseChange"
        >
          <a-select-option v-for="db in availableDatabases" :key="db.db_id" :value="db.db_id">
            {{ db.name }} ({{ db.row_count || 0 }} 文件)
          </a-select-option>
        </a-select>

        <a-select
          v-model:value="selectedLabel"
          placeholder="选择中心实体"
          size="small"
          style="width: 140px"
          :loading="loadingLabels"
          :disabled="!selectedDatabase"
          allow-clear
          show-search
        >
          <a-select-option value="*">全图</a-select-option>
          <a-select-option v-for="label in availableLabels" :key="label" :value="label">
            {{ label }}
          </a-select-option>
        </a-select>
      </div>

      <div class="search-section">
        <a-input-number
          v-model:value="searchParams.max_nodes"
          :min="10"
          :max="1000"
          :step="10"
          size="small"
          addon-before="limit"
          style="width: 140px"
        />
        <a-input-number
          v-model:value="searchParams.max_depth"
          :min="1"
          :max="5"
          :step="1"
          size="small"
          addon-before="depth"
          style="width: 120px; margin-left: 6px"
        />
        <a-button
          type="primary"
          size="small"
          :loading="loading"
          @click="loadGraphData"
          :disabled="!selectedDatabase"
          style="margin-left: 6px"
        >
          <SearchOutlined v-if="!loading" /> 加载图谱
        </a-button>
      </div>

      <div class="layout-section">
        <a-select
          v-model:value="layoutMode"
          size="small"
          style="width: 120px; margin-right: 6px"
        >
          <a-select-option value="radial">环形布局</a-select-option>
          <a-select-option value="force">力导向</a-select-option>
        </a-select>
        <a-button size="small" @click="reapplyLayout">重新布局</a-button>
      </div>

      <div v-if="!props.hideStats" class="stats-section">
        <a-tag color="blue" size="small">节点: {{ stats.displayed_nodes || 0 }}</a-tag>
        <a-tag color="green" size="small">边: {{ stats.displayed_edges || 0 }}</a-tag>
      </div>
    </div>

    <div class="graph-shell" :class="{ loading }">
      <G6GraphCanvas
        ref="graphRef"
        :graph-data="graphData"
        :layout-options="layoutOptions"
        @node-click="handleNodeClick"
        @edge-click="handleEdgeClick"
        @canvas-click="clearSelection"
      />

      <div v-if="!loading && graphData.nodes.length === 0" class="empty-overlay">
        <a-empty>
          <template #description>
            <span>点击“加载图谱”获取数据</span>
          </template>
        </a-empty>
      </div>

      <div v-if="loading" class="loading-overlay">
        <a-spin tip="加载中..." />
      </div>

      <div v-if="selectedNodeData" class="detail-panel node-panel">
        <div class="detail-header">
          <div class="panel-type-indicator node-indicator"></div>
          <h4>节点: {{ getNodeDisplayName(selectedNodeData) }}</h4>
          <a-button type="text" size="small" @click="clearSelection">
            <CloseOutlined />
          </a-button>
        </div>
        <div class="detail-content">
          <div class="detail-item">
            <span class="detail-label">ID:</span>
            <span class="detail-value">{{ selectedNodeData.id }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">标签:</span>
            <span class="detail-value">
              {{ Array.isArray(selectedNodeData.labels) ? selectedNodeData.labels.join(', ') : 'N/A' }}
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">类型:</span>
            <span class="detail-value">
              {{ selectedNodeData.entity_type || selectedNodeData.type || selectedNodeData?.properties?.entity_type || 'unknown' }}
            </span>
          </div>
          <div v-if="selectedNodeData.properties?.description" class="detail-item">
            <span class="detail-label">描述:</span>
            <span class="detail-value">{{ selectedNodeData.properties.description }}</span>
          </div>
          <div class="detail-actions">
            <a-button
              type="primary"
              size="small"
              @click="expandNode(selectedNodeData.id)"
              :loading="expanding"
              :disabled="!selectedDatabase"
            >
              展开相邻节点
            </a-button>
          </div>
        </div>
      </div>

      <div v-if="selectedEdgeData" class="detail-panel edge-panel">
        <div class="detail-header">
          <div class="panel-type-indicator edge-indicator"></div>
          <h4>边: {{ getEdgeDisplayName(selectedEdgeData) }}</h4>
          <a-button type="text" size="small" @click="clearSelection">
            <CloseOutlined />
          </a-button>
        </div>
        <div class="detail-content">
          <div class="detail-item">
            <span class="detail-label">ID:</span>
            <span class="detail-value">{{ selectedEdgeData.id }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">源:</span>
            <span class="detail-value">{{ selectedEdgeData.source }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">目标:</span>
            <span class="detail-value">{{ selectedEdgeData.target }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">类型:</span>
            <span class="detail-value">{{ selectedEdgeData.type || 'DIRECTED' }}</span>
          </div>
          <div v-if="selectedEdgeData.properties?.weight" class="detail-item">
            <span class="detail-label">权重:</span>
            <span class="detail-value">{{ selectedEdgeData.properties.weight }}</span>
          </div>
          <div v-if="selectedEdgeData.properties?.keywords" class="detail-item">
            <span class="detail-label">关键词:</span>
            <span class="detail-value">{{ selectedEdgeData.properties.keywords }}</span>
          </div>
          <div v-if="selectedEdgeData.properties?.description" class="detail-item">
            <span class="detail-label">描述:</span>
            <span class="detail-value">{{ selectedEdgeData.properties.description }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { message } from 'ant-design-vue';
import { CloseOutlined, SearchOutlined } from '@ant-design/icons-vue';
import G6GraphCanvas from '@/components/G6GraphCanvas.vue';
import { graphApi, lightragApi } from '@/apis/graph_api';

const props = defineProps({
  initialDatabaseId: { type: String, default: '' },
  hideDbSelector: { type: Boolean, default: false },
  hideStats: { type: Boolean, default: false },
  hideControls: { type: Boolean, default: false },
  initialLimit: { type: Number, default: 100 },
  initialDepth: { type: Number, default: 2 }
});

const emit = defineEmits(['update:stats', 'refresh-graph', 'clear-graph']);

const graphRef = ref(null);

const loading = ref(false);
const loadingDatabases = ref(false);
const loadingLabels = ref(false);
const expanding = ref(false);

const selectedDatabase = ref('');
const availableDatabases = ref([]);
const selectedLabel = ref('*');
const availableLabels = ref([]);
const layoutMode = ref('radial');

const layoutOptions = computed(() =>
  layoutMode.value === 'radial'
    ? {
        type: 'radial',
        unitRadius: 180,
        linkDistance: 220,
        maxIteration: 1000
      }
    : { type: 'force' }
);

const searchParams = reactive({
  max_nodes: props.initialLimit,
  max_depth: props.initialDepth
});

const graphData = reactive({
  nodes: [],
  edges: []
});

const stats = reactive({
  displayed_nodes: 0,
  displayed_edges: 0,
  is_truncated: false
});

const selectedNodeData = ref(null);
const selectedEdgeData = ref(null);

const clearSelection = () => {
  selectedNodeData.value = null;
  selectedEdgeData.value = null;
};

const RELATION_TYPE_MAP = {
  OCCUR_AT: '发生于',
  TYPICAL_CAUSE: '典型病因',
  MAIN_CAUSE: '主要病因',
  TREATMENT_MEASURE: '处置措施',
  COMMON_DEFECT: '常见缺陷',
  TYPICAL_DEFECT: '典型缺陷',
  HAS_DEFECT: '存在缺陷',
  HAS_CAUSE: '存在病因',
  LOCATED_AT: '位于',
  BELONGS_TO: '属于',
  RELATED_TO: '相关',
};

const normalizeRelationType = (type) => {
  const raw = (type ?? '').toString().trim();
  if (!raw) return '';
  if (/[\u4e00-\u9fa5]/.test(raw)) return raw;
  const upper = raw.toUpperCase();
  return RELATION_TYPE_MAP[upper] || raw;
};

const nodeLabelOf = (node) => {
  const props = node?.properties || {};
  if (props.entity_id) return String(props.entity_id);
  if (node?.label) return String(node.label);
  if (node?.entity_id) return String(node.entity_id);
  if (Array.isArray(node?.labels) && node.labels.length > 0) return String(node.labels[0]);
  if (node?.id != null) return String(node.id);
  return 'Unknown';
};

const normalizeNode = (node) => {
  const id = node?.id != null ? String(node.id) : '';
  const labels = Array.isArray(node?.labels)
    ? node.labels.map(String)
    : node?.labels
      ? [String(node.labels)]
      : [];
  const properties = node?.properties || {};
  const entityType =
    node?.entity_type ?? node?.entityType ?? node?.type ?? properties?.entity_type ?? 'unknown';

  return {
    ...node,
    id,
    labels,
    properties,
    entity_type: entityType,
    label: nodeLabelOf(node)
  };
};

const normalizeEdge = (edge, fallbackIdx = 0) => {
  const rawSource =
    edge?.source_id ?? edge?.sourceId ?? edge?.source ?? edge?.from ?? edge?.start ?? '';
  const rawTarget =
    edge?.target_id ?? edge?.targetId ?? edge?.target ?? edge?.to ?? edge?.end ?? '';
  const source = rawSource != null ? String(rawSource) : '';
  const target = rawTarget != null ? String(rawTarget) : '';
  const id = edge?.id != null ? String(edge.id) : `e-${fallbackIdx}-${source}-${target}`;

  return {
    ...edge,
    id,
    source,
    target,
    relation: normalizeRelationType(edge?.type ?? edge?.relation ?? edge?.label ?? edge?.name ?? edge?.r)
  };
};

const applyGraphResult = (result) => {
  const nodes = (result?.nodes || []).map(normalizeNode);
  const edges = (result?.edges || []).map(normalizeEdge).filter((e) => e.source && e.target);

  graphData.nodes = nodes;
  graphData.edges = edges;

  stats.displayed_nodes = nodes.length;
  stats.displayed_edges = edges.length;
  stats.is_truncated = !!result?.is_truncated;

  clearSelection();
  void nextTick(() => graphRef.value?.refreshGraph?.());
};

const loadGraphLabels = async (dbId) => {
  if (!dbId) return;
  loadingLabels.value = true;
  try {
    const response = await lightragApi.getLabels(dbId);
    if (response?.success) {
      availableLabels.value = response.data?.labels || [];
    } else {
      availableLabels.value = [];
    }
  } catch (error) {
    console.error('加载图标签失败:', error);
    availableLabels.value = [];
  } finally {
    loadingLabels.value = false;
  }
};

const loadAvailableDatabases = async () => {
  if (props.hideDbSelector && props.initialDatabaseId) {
    selectedDatabase.value = props.initialDatabaseId;
    await loadGraphLabels(selectedDatabase.value);
    return;
  }

  loadingDatabases.value = true;
  try {
    const response = await lightragApi.getDatabases();
    if (response?.success) {
      const databases = response?.data?.databases || response?.databases || [];
      availableDatabases.value = Array.isArray(databases) ? databases : [];

      if (
        props.initialDatabaseId &&
        availableDatabases.value.some((db) => db.db_id === props.initialDatabaseId)
      ) {
        selectedDatabase.value = props.initialDatabaseId;
      } else if (availableDatabases.value.length > 0 && !selectedDatabase.value) {
        selectedDatabase.value = availableDatabases.value[0].db_id;
      }

      if (selectedDatabase.value) {
        await loadGraphLabels(selectedDatabase.value);
      }
    }
  } catch (error) {
    console.error('加载数据库列表失败:', error);
    message.error('加载数据库列表失败: ' + (error?.message || String(error)));
  } finally {
    loadingDatabases.value = false;
  }
};

const onDatabaseChange = async (dbId) => {
  selectedDatabase.value = dbId;
  selectedLabel.value = '*';
  await loadGraphLabels(dbId);
};

const loadGraphData = async () => {
  if (!selectedDatabase.value) {
    message.warning('请先选择数据库');
    return;
  }

  loading.value = true;
  try {
    const response = await graphApi.getSubgraph({
      db_id: selectedDatabase.value,
      center: selectedLabel.value || '*',
      depth: searchParams.max_depth,
      limit: searchParams.max_nodes,
      page: 1,
      fields: 'full'
    });

    const result = response?.data || response?.result || response || {};
    if (!response?.success || !Array.isArray(result.nodes) || !Array.isArray(result.edges)) {
      throw new Error('返回数据格式不正确');
    }

    applyGraphResult(result);
    message.success(
      `加载成功：${stats.displayed_nodes} 个节点，${stats.displayed_edges} 条边${
        stats.is_truncated ? ' (已截断)' : ''
      }`
    );
  } catch (error) {
    console.error('加载图数据失败:', error);
    message.error('加载图数据失败: ' + (error?.message || String(error)));
  } finally {
    loading.value = false;
  }
};

const expandNode = async (nodeId) => {
  if (!selectedDatabase.value) {
    message.warning('请先选择数据库');
    return;
  }
  const center = nodeId != null ? String(nodeId) : '';
  if (!center) return;

  expanding.value = true;
  try {
    const response = await graphApi.getSubgraph({
      db_id: selectedDatabase.value,
      center,
      depth: 1,
      limit: 50,
      page: 1,
      fields: 'full'
    });

    const result = response?.data || response?.result || response || {};
    if (!response?.success || !Array.isArray(result.nodes) || !Array.isArray(result.edges)) {
      throw new Error('返回数据格式不正确');
    }

    const existingNodeIds = new Set((graphData.nodes || []).map((n) => String(n.id)));
    const existingEdgeIds = new Set((graphData.edges || []).map((e) => String(e.id)));

    const newNodes = (result.nodes || []).map(normalizeNode).filter((n) => !existingNodeIds.has(String(n.id)));
    const newEdges = (result.edges || [])
      .map(normalizeEdge)
      .filter((e) => e.source && e.target && !existingEdgeIds.has(String(e.id)));

    if (newNodes.length === 0 && newEdges.length === 0) {
      message.info('没有新的相邻节点');
      return;
    }

    graphData.nodes = [...graphData.nodes, ...newNodes];
    graphData.edges = [...graphData.edges, ...newEdges];

    stats.displayed_nodes = graphData.nodes.length;
    stats.displayed_edges = graphData.edges.length;

    await nextTick();
    graphRef.value?.refreshGraph?.();
    setTimeout(() => graphRef.value?.focusNode?.(center), 200);

    message.success(`展开成功：新增 ${newNodes.length} 个节点，${newEdges.length} 条边`);
  } catch (error) {
    console.error('展开节点失败:', error);
    message.error('展开节点失败: ' + (error?.message || String(error)));
  } finally {
    expanding.value = false;
  }
};

const reapplyLayout = async () => {
  await nextTick();
  graphRef.value?.refreshGraph?.();
};

const handleNodeClick = ({ data }) => {
  const raw = data?.data || data || null;
  selectedNodeData.value = raw;
  selectedEdgeData.value = null;
};

const handleEdgeClick = ({ data }) => {
  const raw = data?.data || data || null;
  selectedEdgeData.value = raw;
  selectedNodeData.value = null;
};

const getNodeDisplayName = (node) => nodeLabelOf(node);

const getEdgeDisplayName = (edge) => {
  if (edge?.properties?.keywords) return String(edge.properties.keywords);
  if (edge?.properties?.description) return String(edge.properties.description).slice(0, 20) + '...';
  return `${edge?.source ?? ''} -> ${edge?.target ?? ''}`;
};

const loadFullGraph = async () => {
  selectedLabel.value = '*';
  await loadGraphData();
  emit('refresh-graph');
};

const clearGraph = () => {
  graphData.nodes = [];
  graphData.edges = [];
  stats.displayed_nodes = 0;
  stats.displayed_edges = 0;
  stats.is_truncated = false;
  clearSelection();
  void nextTick(() => graphRef.value?.refreshGraph?.());
  emit('clear-graph');
};

watch(
  () => props.initialDatabaseId,
  async (newId) => {
    if (newId && newId !== selectedDatabase.value) {
      selectedDatabase.value = newId;
      selectedLabel.value = '*';
      await loadGraphLabels(newId);
    }
  }
);

watch(
  stats,
  (newStats) => {
    emit('update:stats', { ...newStats });
  },
  { deep: true, immediate: true }
);

onMounted(() => {
  void loadAvailableDatabases();
});

defineExpose({
  loadFullGraph,
  clearGraph
});
</script>

<style lang="less" scoped>
.knowledge-graph-viewer {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.control-panel {
  background: var(--bg-container);
  border-bottom: var(--glass-border);
  backdrop-filter: var(--glass-blur);
  padding: 8px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.database-section,
.search-section,
.layout-section,
.stats-section {
  display: flex;
  align-items: center;
  padding: 0 12px;
}

.graph-shell {
  flex: 1;
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  border: var(--glass-border);
  min-height: 240px;

  &.loading {
    pointer-events: none;
  }
}

.empty-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  background: rgba(0, 0, 0, 0.18);
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 30;
}

.detail-panel {
  position: absolute;
  top: 12px;
  left: 12px;
  width: 240px;
  background: var(--glass-bg);
  border: var(--glass-border);
  border-radius: 6px;
  box-shadow: var(--shadow-md);
  backdrop-filter: var(--glass-blur);
  z-index: 40;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: var(--glass-border);
  background: rgba(15, 23, 42, 0.45);
  border-radius: 6px 6px 0 0;

  h4 {
    margin: 0;
    font-size: 12px;
    font-weight: 600;
    flex: 1;
    color: var(--text-primary);
  }
}

.panel-type-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;

  &.node-indicator {
    background: #52c41a;
  }

  &.edge-indicator {
    background: #1890ff;
  }
}

.detail-content {
  padding: 10px;
  max-height: 300px;
  overflow-y: auto;
}

.detail-item {
  display: flex;
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }
}

.detail-label {
  min-width: 50px;
  font-weight: 600;
  color: var(--text-tertiary);
  font-size: 11px;
  flex-shrink: 0;
}

.detail-value {
  color: var(--text-primary);
  font-size: 11px;
  word-break: break-word;
  line-height: 1.3;
}

.detail-actions {
  margin-top: 12px;
  padding-top: 8px;
  border-top: var(--glass-border);
}
</style>
