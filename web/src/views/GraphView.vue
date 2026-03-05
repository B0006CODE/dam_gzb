<template>
  <div class="database-empty" v-if="!state.showPage">
    <a-empty>
      <template #description>
        <span>
          前往 <router-link to="/setting" style="color: var(--main-color); font-weight: bold;">设置</router-link> 页面启用知识图谱。
        </span>
      </template>
    </a-empty>
  </div>
  <div class="graph-container layout-container" v-else>
    <HeaderComponent
      title="图数据库"
    >
      <template #actions>
        <div class="status-wrapper">
          <div class="status-indicator" :class="graphStatusClass"></div>
          <span class="status-text">{{ graphStatusText }}</span>
        </div>
        <a-tag v-if="isReadOnly" color="default">只读模式</a-tag>
        <a-button v-if="isAdmin" type="default" @click="openLink('http://localhost:7474/')" :icon="h(GlobalOutlined)">
          Neo4j 浏览器
        </a-button>
        <a-button v-if="isAdmin" type="primary" @click="state.showModal = true" ><UploadOutlined/> 上传文件</a-button>
        <a-button v-if="isAdmin && unindexedCount > 0" type="primary" @click="indexNodes" :loading="state.indexing">
          <SyncOutlined v-if="!state.indexing"/> 为{{ unindexedCount }}个节点添加索引
        </a-button>
      </template>
    </HeaderComponent>

    <div class="container-outter">
      <G6GraphCanvas
        ref="graphRef"
        :graph-data="graphData"
        :layout-options="layoutOptions"
        :highlight-keywords="highlightKeywords"
        :hidden-dimensions="hiddenDimensions"
        @node-click="handleNodeExpand"
      >
        <template #top>
          <div class="actions">
            <div class="actions-left">
              <a-select
                v-model:value="selectedGraph"
                :options="graphOptions"
                style="width: 200px"
                :loading="state.loadingGraphs"
                @change="handleGraphChange"
              />
              <a-button v-if="isAdmin" type="default" @click="openRenameModal" :icon="h(EditOutlined)">
                重命名
              </a-button>
              <a-input
                v-model:value="state.searchInput"
                placeholder="输入要查询的实体"
                style="width: 300px"
                @keydown.enter="onSearch"
                allow-clear
              >
                <template #suffix>
                  <component :is="state.searchLoading ? LoadingOutlined : SearchOutlined" @click="onSearch" />
                </template>
              </a-input>
            </div>
            <div class="actions-right">
              <a-select
                v-model:value="displayMode"
                :options="displayModeOptions"
                style="width: 130px"
              />
              <a-button type="default" @click="state.showInfoModal = true" :icon="h(InfoCircleOutlined)">
                说明
              </a-button>
              <a-input
                v-model:value="sampleNodeCount"
                placeholder="查询三元组数量"
                style="width: 120px"
                @keydown.enter="loadSampleNodes"
                :loading="state.fetching"
              >
                <template #suffix>
                  <component :is="state.fetching ? LoadingOutlined : ReloadOutlined" @click="loadSampleNodes" />
                </template>
              </a-input>
            </div>
          </div>
        </template>
        <template #content>
          <div v-show="graphData.nodes.length === 0" class="empty-graph-hint">
            <a-empty style="padding: 4rem 0;">
              <template #description>
                <span>点击右上角的刷新按钮加载图谱数据</span>
              </template>
              <a-button type="primary" @click="loadSampleNodes" :loading="state.fetching">
                <ReloadOutlined v-if="!state.fetching" /> 加载 {{ sampleNodeCount }} 个节点
              </a-button>
            </a-empty>
          </div>
        </template>
        <template #bottom>
          <div class="footer">
            <div class="tags">
              <a-tag :bordered="false" v-for="tag in graphTags" :key="tag.key" :color="tag.type">{{ tag.text }}</a-tag>
            </div>
            <div class="legend" v-if="legendItems.length">
              <div class="legend-header">
                <h4>实体类型</h4>
                <div class="legend-right">
                  <div class="legend-stats">
                    <span class="stat-item">
                      实体 {{ visibleGraphData.nodes.length }}
                      <template v-if="typeof graphInfo?.entity_count === 'number'">
                        / {{ graphInfo.entity_count }}
                      </template>
                    </span>
                    <span class="stat-item">
                      关系 {{ visibleGraphData.edges.length }}
                      <template v-if="typeof graphInfo?.relationship_count === 'number'">
                        / {{ graphInfo.relationship_count }}
                      </template>
                    </span>
                  </div>
                  <a-button
                    type="text"
                    size="small"
                    class="legend-toggle-btn"
                    @click="legendCollapsed = !legendCollapsed"
                  >
                    <template #icon>
                      <component :is="legendCollapsed ? DownOutlined : UpOutlined" />
                    </template>
                    {{ legendCollapsed ? '展开' : '收起' }}
                  </a-button>
                </div>
              </div>
              <div class="legend-content" v-show="!legendCollapsed">
                <div class="legend-item" v-for="item in legendItems" :key="item.type">
                  <span class="legend-color" :style="{ backgroundColor: item.color }"></span>
                  <span class="legend-label">{{ item.type }} ({{ item.count }})</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </G6GraphCanvas>
      
      <!-- 维度筛选器 -->
      <DimensionFilter v-if="showDimensionFilter" v-model="hiddenDimensions" />
    </div>

    <a-modal
      v-if="isAdmin"
      :open="state.showModal" title="上传文件"
      @ok="addDocumentByFile"
      @cancel="() => state.showModal = false"
      ok-text="添加到图数据库" cancel-text="取消"
      :confirm-loading="state.processing">
      <div class="upload">
        <!-- <div class="note">
          <p>上传的文件内容参考 test/data/A_Dream_of_Red_Mansions_tiny.jsonl 中的格式：</p>
        </div> -->
        <a-upload-dragger
          class="upload-dragger"
          v-model:fileList="fileList"
          name="file"
          :fileList="fileList"
          :max-count="1"
          accept=".jsonl"
          action="/api/knowledge/files/upload?allow_jsonl=true"
          :headers="getAuthHeaders()"
          @change="handleFileUpload"
          @drop="handleDrop"
        >
          <p class="ant-upload-text">点击或者把文件拖拽到这里上传</p>
          <p class="ant-upload-hint">
            目前仅支持上传 jsonl 文件。
          </p>
        </a-upload-dragger>
      </div>
    </a-modal>

    <!-- 说明弹窗 -->
    <!-- <a-modal
      :open="state.showInfoModal"
      title="图数据库说明"
      @cancel="() => state.showInfoModal = false"
      :footer="null"
      width="600px"
    >
      <div class="info-content">
        <p>本页面展示的是 Neo4j 图数据库中的知识图谱信息。</p>
        <p>具体展示内容包括：</p>
        <ul>
          <li>带有 <code>Entity</code> 标签的节点</li>
          <li>带有 <code>RELATION</code> 类型的关系边</li>
        </ul>
        <p>注意：</p>
        <ul>
          <li>这里仅展示用户上传的实体和关系，不包含知识库中自动创建的图谱。</li>
          <li>查询逻辑基于 <code>graphbase.py</code> 中的 <code>get_sample_nodes</code> 方法实现：</li>
        </ul>
        <pre><code>MATCH (n:Entity)-[r]-&gt;(m:Entity)
RETURN
    {id: elementId(n), name: n.name} AS h,
    {type: r.type, source_id: elementId(n), target_id: elementId(m)} AS r,
    {id: elementId(m), name: m.name} AS t
LIMIT $num</code></pre>
        <p>如需查看完整的 Neo4j 数据库内容，请使用 "Neo4j 浏览器" 按钮访问原生界面。</p>
      </div>
    </a-modal> -->

    <a-modal
      :open="isAdmin && renameModalVisible"
      title="重命名知识图谱"
      @ok="confirmRename"
      @cancel="() => (renameModalVisible = false)"
      ok-text="保存"
      cancel-text="取消"
    >
      <a-input
        v-model:value="renameInput"
        placeholder="输入新的图谱名称"
        @keydown.enter.prevent="confirmRename"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, h } from 'vue';
import { message } from 'ant-design-vue';
import { useConfigStore } from '@/stores/config';
import { UploadOutlined, SyncOutlined, GlobalOutlined, InfoCircleOutlined, SearchOutlined, ReloadOutlined, LoadingOutlined, EditOutlined, UpOutlined, DownOutlined } from '@ant-design/icons-vue';
import HeaderComponent from '@/components/HeaderComponent.vue';
import { neo4jApi, lightragApi, getPagedSubgraph } from '@/apis/graph_api';
import { useUserStore } from '@/stores/user';
import G6GraphCanvas from '@/components/G6GraphCanvas.vue';
import DimensionFilter from '@/components/DimensionFilter.vue';
import { buildNodeColorMap, DIMENSION_COLORS, filterByDimensions } from '@/utils/nodeColorMapper';
import { getEntityTypeColor, normalizeEntityType } from '@/utils/entityTypeColors';
import { storeToRefs } from 'pinia';

const configStore = useConfigStore();
const userStore = useUserStore();
const { isAdmin } = storeToRefs(userStore);
const isReadOnly = computed(() => !isAdmin.value);
const cur_embed_model = computed(() => configStore.config?.embed_model);
const modelMatched = computed(() => !graphInfo?.value?.embed_model_name || graphInfo.value.embed_model_name === cur_embed_model.value)

const graphRef = ref(null)
const graphInfo = ref(null)
const fileList = ref([]);
const DEFAULT_SAMPLE_NODE_COUNT = 100;
const MIN_SAMPLE_NODE_COUNT = 20;
const MAX_SAMPLE_NODE_COUNT = 1000;
const sampleNodeCount = ref(DEFAULT_SAMPLE_NODE_COUNT);  // 分页加载每页数量
const hiddenDimensions = ref([]);  // 隐藏的维度列表
const committedSearchKeyword = ref('');
const highlightKeywords = computed(() =>
  committedSearchKeyword.value ? [committedSearchKeyword.value] : []
);
const graphOptions = ref([{ label: 'Neo4j', value: 'neo4j' }]);
const selectedGraph = ref('neo4j');
const displayMode = ref('force');
const displayModeOptions = [
  { label: '自由布局', value: 'force' },
  { label: '环形布局', value: 'radial' },
  { label: '同心布局', value: 'concentric' },
  { label: '圆形布局', value: 'circular' },
];
const graphAliases = ref(loadGraphAliases());
const renameModalVisible = ref(false);
const renameInput = ref('');
const legendCollapsed = ref(false);
const graphData = reactive({
  nodes: [],
  edges: [],
});

const expandedNodeIds = new Set();
const expandingNodeIds = new Set();

const clampSampleNodeCount = (value) => {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) return DEFAULT_SAMPLE_NODE_COUNT;
  return Math.max(MIN_SAMPLE_NODE_COUNT, Math.min(MAX_SAMPLE_NODE_COUNT, parsed));
};

const resolveSampleNodeCount = () => {
  const safe = clampSampleNodeCount(sampleNodeCount.value);
  if (safe !== sampleNodeCount.value) {
    sampleNodeCount.value = safe;
  }
  return safe;
};

const resetExpandState = () => {
  expandedNodeIds.clear();
  expandingNodeIds.clear();
};

const getEdgeSourceId = (edge) =>
  edge?.source_id ?? edge?.sourceId ?? edge?.source ?? edge?.from ?? edge?.start;

const getEdgeTargetId = (edge) =>
  edge?.target_id ?? edge?.targetId ?? edge?.target ?? edge?.to ?? edge?.end;

const edgeKeyOf = (edge) => {
  if (!edge) return '';
  const s = getEdgeSourceId(edge);
  const t = getEdgeTargetId(edge);
  if (s == null || t == null) {
    if (edge.id != null && edge.id !== '') return `id:${String(edge.id)}`;
    return '';
  }
  const type = edge?.type ?? edge?.r ?? edge?.relation ?? edge?.label ?? edge?.name ?? '';
  return `${String(s)}->${String(t)}::${String(type)}`;
};

const normalizeRenderableGraphData = (nodes = [], edges = []) => {
  const nodeMap = new Map();
  const normalizedNodes = [];

  for (const node of nodes || []) {
    if (!node || node.id == null || node.id === '') continue;
    const key = String(node.id);
    if (!nodeMap.has(key)) {
      const nextNode = { ...node, id: key };
      nodeMap.set(key, nextNode);
      normalizedNodes.push(nextNode);
      continue;
    }
    const prev = nodeMap.get(key);
    Object.assign(prev, node, { id: key });
  }

  const normalizedEdges = [];
  const seenEdgeKeys = new Set();
  for (const edge of edges || []) {
    if (!edge) continue;
    const s = getEdgeSourceId(edge);
    const t = getEdgeTargetId(edge);
    if (s == null || t == null) continue;
    const sourceKey = String(s);
    const targetKey = String(t);
    if (!nodeMap.has(sourceKey) || !nodeMap.has(targetKey)) continue;
    const key = edgeKeyOf(edge);
    if (!key || seenEdgeKeys.has(key)) continue;
    seenEdgeKeys.add(key);
    normalizedEdges.push(edge);
  }

  return { nodes: normalizedNodes, edges: normalizedEdges };
};

const mergeSubgraphIntoGraphData = (subgraph) => {
  const nodes = subgraph?.nodes || [];
  const edges = subgraph?.edges || [];

  const nextNodes = [];
  const seenNodeIds = new Set();

  const pushNode = (node) => {
    if (!node) return;
    const id = node.id;
    if (id == null) return;
    const key = String(id);
    if (seenNodeIds.has(key)) return;
    seenNodeIds.add(key);
    nextNodes.push(node);
  };

  graphData.nodes.forEach(pushNode);
  nodes.forEach(pushNode);

  const nextEdges = [];
  const seenEdgeKeys = new Set();

  const pushEdge = (edge) => {
    if (!edge) return;
    const s = getEdgeSourceId(edge);
    const t = getEdgeTargetId(edge);
    if (s == null || t == null) return;
    const key = edgeKeyOf(edge);
    if (!key || seenEdgeKeys.has(key)) return;
    seenEdgeKeys.add(key);
    nextEdges.push(edge);
  };

  graphData.edges.forEach(pushEdge);
  edges.forEach(pushEdge);

  graphData.nodes = nextNodes;
  graphData.edges = nextEdges;
};

const layoutOptions = computed(() => {
  switch (displayMode.value) {
    case 'radial':
      return {
        type: 'radial',
        unitRadius: 180,
        linkDistance: 220,
        maxIteration: 1000
      };
    case 'concentric':
      return {
        type: 'concentric',
        preventOverlap: true,
        equidistant: false,
        startAngle: -Math.PI / 2,
        clockwise: true
      };
    case 'circular':
      return {
        type: 'circular',
        ordering: 'degree',
        startAngle: -Math.PI / 2,
        clockwise: true
      };
    case 'force':
    default:
      return { type: 'force' };
  }
})

const state = reactive({
  fetching: false,
  loadingGraphInfo: false,
  searchInput: '',
  searchLoading: false,
  showModal: false,
  showInfoModal: false,
  processing: false,
  indexing: false,
  showPage: true,
  loadingGraphs: false,
})

// 计算未索引节点数量
const unindexedCount = computed(() => {
  return graphInfo.value?.unindexed_node_count || 0;
});

const loadGraphInfo = async () => {
  state.loadingGraphInfo = true;
  try {
    const data = await neo4jApi.getInfo();
    graphInfo.value = data.data;
    return data.data;
  } catch (error) {
    console.error(error);
    message.error(error.message || '加载图数据库信息失败');
    return null;
  } finally {
    state.loadingGraphInfo = false;
  }
};

const addDocumentByFile = () => {
  if (isReadOnly.value) {
    message.warning('当前为只读模式，无法上传或写入图谱');
    state.showModal = false;
    return;
  }

  state.processing = true
  const files = fileList.value.filter(file => file.status === 'done').map(file => file.response.file_path)
  neo4jApi.addEntities(files[0])
    .then((data) => {
      if (data.status === 'success') {
        message.success(data.message);
        state.showModal = false;
      } else {
        throw new Error(data.message);
      }
    })
    .catch((error) => {
      console.error(error)
      message.error(error.message || '添加文件失败');
    })
    .finally(() => state.processing = false)
};

const handleNodeExpand = async ({ id, data }) => {
  const nodeId = id != null ? String(id) : '';
  if (!nodeId) return;
  if (state.fetching || state.searchLoading) return;
  if (expandedNodeIds.has(nodeId)) return;
  if (expandingNodeIds.has(nodeId)) return;

  expandingNodeIds.add(nodeId);
  const currentGraph = selectedGraph.value || 'neo4j';
  const limit = resolveSampleNodeCount();

  try {
    let res;
    if (currentGraph === 'neo4j') {
      res = await neo4jApi.expandNode(nodeId, { limit: 120 });
    } else {
      const rawNode = data?.data || data || {};
      const center = rawNode?.label || rawNode?.name || rawNode?.id || nodeId;
      res = await getPagedSubgraph({
        db_id: currentGraph,
        center,
        depth: 1,
        limit,
        page: 1,
        fields: 'compact'
      });
    }

    const result = res?.result || res?.data || res || {};
    if (!Array.isArray(result.nodes) || !Array.isArray(result.edges)) {
      throw new Error('返回数据格式不正确');
    }

    mergeSubgraphIntoGraphData(result);
    expandedNodeIds.add(nodeId);
    setTimeout(() => graphRef.value?.focusNode?.(nodeId), 200);
  } catch (error) {
    console.error('expand node error:', error);
    message.error(error?.message || '展开相邻节点失败');
  } finally {
    expandingNodeIds.delete(nodeId);
  }
};

const loadSampleNodes = () => {
  state.fetching = true
  const currentGraph = selectedGraph.value || 'neo4j'
  const limit = resolveSampleNodeCount();
  committedSearchKeyword.value = '';

  const handleResult = (data) => {
    const result = data?.result || data?.data || data || {}
    resetExpandState();
    graphData.nodes = result.nodes || []
    graphData.edges = result.edges || []
  }

  const handleError = (error) => {
    console.error(error)
    message.error(error.message || '加载节点失败');
  }

  const finallyCb = () => { state.fetching = false }

  if (currentGraph === 'neo4j') {
    neo4jApi.getSampleNodes(currentGraph, limit)
      .then(handleResult)
      .catch(handleError)
      .finally(finallyCb)
  } else {
    getPagedSubgraph({
      db_id: currentGraph,
      center: '*',
      depth: 2,
      limit,
      page: 1,
      fields: 'compact'
    })
      .then(handleResult)
      .catch(handleError)
      .finally(finallyCb)
  }
}

const onSearch = () => {
  if (state.searchLoading) {
    message.error('请稍后再试')
    return
  }

  if (graphInfo?.value?.embed_model_name !== cur_embed_model.value) {
    // 可选：提示模型不一致
  }

  const keyword = (state.searchInput || '').trim();
  if (!keyword) {
    message.error('请输入要查询的实体')
    return
  }

  state.searchLoading = true
  const currentGraph = selectedGraph.value || 'neo4j'
  const limit = resolveSampleNodeCount();

  const handleResult = (data) => {
    const result = data?.result || data?.data || data || {}
    if (!result.nodes || !result.edges) {
      throw new Error('返回数据格式不正确');
    }
    resetExpandState();
    graphData.nodes = result.nodes
    graphData.edges = result.edges
    committedSearchKeyword.value = keyword;
    if (graphData.nodes.length === 0) {
      message.info('未找到相关实体')
    }
  }

  const handleError = (error) => {
    console.error('查询错误:', error);
    message.error(`查询出错：${error.message || '未知错误'}`);
  }

  const finallyCb = () => { state.searchLoading = false }

  if (currentGraph === 'neo4j') {
    neo4jApi.queryNode(keyword)
      .then(handleResult)
      .catch(handleError)
      .finally(finallyCb)
  } else {
    getPagedSubgraph({
      db_id: currentGraph,
      center: keyword,
      depth: 2,
      limit,
      page: 1,
      fields: 'compact'
    })
      .then(handleResult)
      .catch(handleError)
      .finally(finallyCb)
  }
};

onMounted(async () => {
  await loadGraphInfo();
  await loadGraphOptions();
  // 自动加载节点数据
  loadSampleNodes();
});

const handleFileUpload = (event) => {
  // File upload handler
}

const handleDrop = (event) => {
  // Drop handler
}

const graphStatusClass = computed(() => {
  if (state.loadingGraphInfo) return 'loading';
  return graphInfo.value?.status === 'open' ? 'open' : 'closed';
});

const graphStatusText = computed(() => {
  if (state.loadingGraphInfo) return '加载中';
  return graphInfo.value?.status === 'open' ? '已连接' : '已关闭';
});

// 新增：将图谱信息拆分为多条标签用于展示
const graphTags = computed(() => {
  const tags = [];

  // 只保留未索引警告标签
  if (unindexedCount.value > 0) tags.push({ key: 'unindexed', text: `未索引 ${unindexedCount.value}`, type: 'warning' });

  return tags;
});

const useEntityTypes = computed(() => {
  return (graphData.nodes || []).some(
    (node) =>
      node &&
      (node.type !== undefined || node.entity_type !== undefined || node.entityType !== undefined)
  );
});

const showDimensionFilter = computed(() => !useEntityTypes.value);

const visibleGraphData = computed(() => {
  const filtered = filterByDimensions(
    graphData.nodes || [],
    graphData.edges || [],
    hiddenDimensions.value
  );
  return normalizeRenderableGraphData(filtered.nodes || [], filtered.edges || []);
});

// ========= 图例 =========
const legendItems = computed(() => {
  const visibleNodes = visibleGraphData.value.nodes || [];
  const visibleEdges = visibleGraphData.value.edges || [];

  if (useEntityTypes.value) {
    const counts = new Map();
    visibleNodes.forEach((node) => {
      const typeKey = normalizeEntityType(node?.type ?? node?.entity_type ?? node?.entityType);
      counts.set(typeKey, (counts.get(typeKey) || 0) + 1);
    });

    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([type, count]) => ({
        type,
        count,
        color: getEntityTypeColor(type)
      }));
  }

  // 统计每个维度的节点数量
  const colorMap = buildNodeColorMap(visibleNodes, visibleEdges);
  const dimensionCounts = new Map();
  
  for (const [nodeId, info] of colorMap) {
    const dim = info.dimension;
    dimensionCounts.set(dim, (dimensionCounts.get(dim) || 0) + 1);
  }
  
  // 使用所有维度（包括 default）
  return Object.values(DIMENSION_COLORS).map(dim => ({
    type: dim.label,
    count: dimensionCounts.get(dim.key) || 0,
    color: dim.main,
    dimension: dim.key
  })).filter(item => item.count > 0);
});

// 为未索引节点添加索引
const indexNodes = () => {
  if (isReadOnly.value) {
    message.warning('当前为只读模式，无法添加索引');
    return;
  }

  if (selectedGraph.value !== 'neo4j') {
    message.info('当前仅支持 Neo4j 图谱的索引操作');
    return;
  }
  // 判断 embed_model_name 是否相同
  if (!modelMatched.value) {
    message.error(`向量模型不匹配，无法添加索引，当前向量模型为 ${cur_embed_model.value}，图数据库向量模型为 ${graphInfo.value?.embed_model_name}`)
    return
  }

  if (state.processing) {
    message.error('后台正在处理，请稍后再试')
    return
  }

  state.indexing = true;
  neo4jApi.indexEntities('neo4j')
    .then(data => {
      message.success(data.message || '索引添加成功');
      // 刷新图谱信息
      loadGraphInfo();
    })
    .catch(error => {
      console.error(error);
      message.error(error.message || '添加索引失败');
    })
    .finally(() => {
      state.indexing = false;
    });
};

const getAuthHeaders = () => {
  return userStore.getAuthHeaders();
};

const openLink = (url) => {
  window.open(url, '_blank')
}

function loadGraphAliases() {
  try {
    const raw = localStorage.getItem('graph_aliases');
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
}

const persistGraphAliases = () => {
  localStorage.setItem('graph_aliases', JSON.stringify(graphAliases.value || {}));
};

const labelWithAlias = (id, fallback) => {
  return graphAliases.value?.[id] || fallback || id;
};

const loadGraphOptions = async () => {
  state.loadingGraphs = true;
  const options = [{ label: labelWithAlias('neo4j', 'Neo4j'), value: 'neo4j' }];

  try {
    const res = await lightragApi.getDatabases();
    // 安全地提取数据库列表，确保是数组
    let list = res?.databases || res?.data || res;
    if (!Array.isArray(list)) {
      // 如果响应是对象且有 databases 属性，尝试提取
      if (list && typeof list === 'object' && list.databases) {
        list = list.databases;
      } else {
        list = [];
      }
    }
    list.forEach((item) => {
      const value = item.db_id || item.id || item.name;
      const label = labelWithAlias(value, item.name || value);
      if (value) options.push({ label, value });
    });
  } catch (error) {
    console.warn('获取图谱列表失败，使用默认 Neo4j：', error);
  } finally {
    state.loadingGraphs = false;
  }

  const dedup = [];
  const seen = new Set();
  options.forEach((opt) => {
    if (!seen.has(opt.value)) {
      seen.add(opt.value);
      dedup.push(opt);
    }
  });
  graphOptions.value = dedup;

  if (!seen.has(selectedGraph.value)) {
    selectedGraph.value = dedup[0]?.value || 'neo4j';
  }
};

const handleGraphChange = () => {
  committedSearchKeyword.value = '';
  loadSampleNodes();
};

const openRenameModal = () => {
  if (isReadOnly.value) {
    message.warning('当前为只读模式，无法重命名');
    return;
  }

  renameInput.value = labelWithAlias(selectedGraph.value, selectedGraph.value);
  renameModalVisible.value = true;
};

const confirmRename = () => {
  if (isReadOnly.value) {
    message.warning('当前为只读模式，无法重命名');
    return;
  }

  const newName = (renameInput.value || '').trim();
  if (!newName) {
    message.error('名称不能为空');
    return;
  }
  graphAliases.value = { ...(graphAliases.value || {}), [selectedGraph.value]: newName };
  persistGraphAliases();
  graphOptions.value = graphOptions.value.map((opt) =>
    opt.value === selectedGraph.value ? { ...opt, label: newName } : opt
  );
  renameModalVisible.value = false;
  message.success('已更新图谱名称');
};

</script>

<style lang="less" scoped>
@graph-header-height: 55px;

.graph-container {
  padding: 0;

  .header-container {
    height: @graph-header-height;
  }
}

.status-wrapper {
  display: flex;
  align-items: center;
  margin-right: 16px;
  font-size: 14px;
  color: var(--text-secondary);
}

.status-text {
  margin-left: 8px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;

  &.loading {
    background-color: #faad14;
    animation: pulse 1.5s infinite ease-in-out;
  }

  &.open {
    background-color: #52c41a;
  }

  &.closed {
    background-color: #f5222d;
  }
}

@keyframes pulse {
  0% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.2);
    opacity: 1;
  }
  100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
}


.upload {
  margin-bottom: 20px;

  .upload-dragger {
    margin: 0px;
  }
}

.container-outter {
  width: 100%;
  height: calc(100vh - @graph-header-height);
  overflow: hidden;
  background: var(--gray-10);

  .actions,
  .footer {
    display: flex;
    justify-content: space-between;
    margin: 20px 0;
    padding: 0 24px;
    width: 100%;
  }
}

.actions {
  top: 0;

  .actions-left, .actions-right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  :deep(.ant-input) {
    padding: 2px 10px;
  }

  button {
    height: 37px;
    box-shadow: none;
  }
}

/* 图例样式 */
.legend {
  background: var(--glass-bg);
  border: var(--glass-border);
  backdrop-filter: var(--glass-blur);
  border-radius: 6px;
  max-height: 180px;
  overflow-y: auto;
  padding: 6px 10px;
  min-width: 180px;
}
.legend-header {
  padding: 2px 0 6px 0;
  border-bottom: var(--glass-border);
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.legend-header h4 {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  flex-shrink: 0;
}
.legend-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.legend-stats {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-secondary);
}
.legend-stats .stat-item {
  white-space: nowrap;
}
.legend-toggle-btn {
  color: var(--text-secondary);
  padding: 0 4px;
}
.legend-content { max-height: 140px; overflow-y: auto; }
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px;
  margin: 2px 0;
  border-radius: 4px;
  font-size: 12px;
}
.legend-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.15);
}
</style>
