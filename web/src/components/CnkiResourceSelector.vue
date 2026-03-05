<template>
  <div class="cnki-resource-selector">
    <!-- 知识库筛选组 -->
    <div class="cnki-filter-group">
      <div class="filter-header" @click="kbCollapsed = !kbCollapsed">
        <span class="filter-title">知识库</span>
        <div class="filter-header-right">
          <BarChartOutlined class="filter-stats-icon" />
          <UpOutlined v-if="!kbCollapsed" class="collapse-icon" />
          <DownOutlined v-else class="collapse-icon" />
        </div>
      </div>
      <div class="filter-body" v-show="!kbCollapsed">
        <div class="filter-disabled-hint" v-if="!allowKbSelect">
          <InfoCircleOutlined /> 切换到"混合检索"或"知识库检索"以选择
        </div>
        <div 
          v-for="option in kbOptionsWithStats" 
          :key="option.value"
          class="filter-item"
          :class="{ 
            'disabled': !allowKbSelect, 
            'selected': selectedKbIds.includes(option.value) 
          }"
          @click="toggleKbSelection(option.value)"
        >
          <a-checkbox 
            :checked="selectedKbIds.includes(option.value)"
            :disabled="!allowKbSelect"
            @click.stop
            @change="(e) => handleKbCheckChange(option.value, e.target.checked)"
          />
          <span class="filter-label">{{ option.name }}</span>
          <span class="filter-count">({{ option.fileCount }})</span>
        </div>
        <div class="filter-empty" v-if="kbOptionsWithStats.length === 0">
          暂无可用知识库
        </div>
      </div>
    </div>

    <!-- 知识图谱筛选组 -->
    <div class="cnki-filter-group">
      <div class="filter-header" @click="graphCollapsed = !graphCollapsed">
        <span class="filter-title">知识图谱</span>
        <div class="filter-header-right">
          <BarChartOutlined class="filter-stats-icon" />
          <UpOutlined v-if="!graphCollapsed" class="collapse-icon" />
          <DownOutlined v-else class="collapse-icon" />
        </div>
      </div>
      <div class="filter-body" v-show="!graphCollapsed">
        <div class="filter-disabled-hint" v-if="!allowGraphSelect">
          <InfoCircleOutlined /> 切换到"混合检索"或"知识图谱检索"以选择
        </div>
        <div 
          v-for="option in graphOptionsWithStats" 
          :key="option.value"
          class="filter-item"
          :class="{ 
            'disabled': !allowGraphSelect, 
            'selected': selectedGraph === option.value 
          }"
          @click="selectGraphOption(option.value)"
        >
          <a-radio 
            :checked="selectedGraph === option.value"
            :disabled="!allowGraphSelect"
            @click.stop
            @change="() => selectGraphOption(option.value)"
          />
          <span class="filter-label">{{ option.name }}</span>
          <span class="filter-count" v-if="option.entityCount !== undefined">
            ({{ formatCount(option.entityCount) }})
          </span>
          <a-tooltip v-if="option.isTruncated" title="数据量较大，统计可能不完全准确">
            <ExclamationCircleOutlined class="truncated-warning" />
          </a-tooltip>
        </div>
        <div class="filter-empty" v-if="graphOptionsWithStats.length === 0">
          暂无可用知识图谱
        </div>
      </div>
    </div>

    <!-- 当前选择摘要 -->
    <div class="selection-summary">
      <div class="summary-row">
        <span class="summary-label">检索模式:</span>
        <span class="summary-value mode-tag">{{ retrievalModeLabel }}</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">知识库:</span>
        <span class="summary-value">{{ kbSummary }}</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">图谱:</span>
        <span class="summary-value">{{ graphSummary }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { 
  BarChartOutlined, 
  UpOutlined, 
  DownOutlined, 
  InfoCircleOutlined,
  ExclamationCircleOutlined 
} from '@ant-design/icons-vue';
import { databaseApi } from '@/apis/knowledge_api';
import { lightragApi, neo4jApi } from '@/apis/graph_api';

// Props
const props = defineProps({
  retrievalMode: {
    type: String,
    default: 'mix'
  },
  modelValue: {
    type: Object,
    default: () => ({ kbIds: [], graph: '' })
  }
});

// Emits
const emit = defineEmits(['update:modelValue']);

// 折叠状态
const kbCollapsed = ref(false);
const graphCollapsed = ref(false);

// 数据
const kbOptionsRaw = ref([]);
const graphOptionsRaw = ref([]);
const graphStats = ref({});

// 选择状态 - 从 modelValue 同步
const selectedKbIds = computed({
  get: () => props.modelValue.kbIds || [],
  set: (val) => emit('update:modelValue', { ...props.modelValue, kbIds: val })
});

const selectedGraph = computed({
  get: () => props.modelValue.graph || '',
  set: (val) => emit('update:modelValue', { ...props.modelValue, graph: val })
});

// 是否允许选择
const allowKbSelect = computed(() => ['mix', 'local'].includes(props.retrievalMode));
const allowGraphSelect = computed(() => ['mix', 'global'].includes(props.retrievalMode));

// 带统计信息的知识库选项
const kbOptionsWithStats = computed(() => {
  return kbOptionsRaw.value.map(db => ({
    value: db.db_id,
    name: db.name || db.db_id,
    fileCount: db.files ? Object.keys(db.files).length : 0,
    kb_type: db.kb_type
  }));
});

// 读取图谱别名（与GraphView保持一致）
const loadGraphAliases = () => {
  try {
    const raw = localStorage.getItem('graph_aliases');
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
};
const graphAliases = ref(loadGraphAliases());

// 带统计信息的图谱选项
const graphOptionsWithStats = computed(() => {
  return graphOptionsRaw.value.map(db => {
    const stats = graphStats.value[db.db_id];
    const alias = graphAliases.value[db.db_id];
    return {
      value: db.db_id,
      name: alias || db.name || db.db_id,
      entityCount: stats?.total_nodes,
      relationCount: stats?.total_edges,
      isTruncated: stats?.is_truncated || false
    };
  });
});


// 格式化数量显示
const formatCount = (count) => {
  if (count === undefined || count === null) return '?';
  if (count >= 10000) {
    return (count / 10000).toFixed(2) + '万';
  }
  return count.toString();
};

// 检索模式标签
const retrievalModeLabels = {
  mix: '混合检索',
  local: '知识库检索',
  global: '知识图谱检索',
  llm: '大模型检索'
};
const retrievalModeLabel = computed(() => retrievalModeLabels[props.retrievalMode] || '检索模式');

// 摘要信息
const kbSummary = computed(() => {
  if (!allowKbSelect.value) return '由模式决定';
  if (!selectedKbIds.value.length) return '未选择';
  const labels = kbOptionsWithStats.value
    .filter(opt => selectedKbIds.value.includes(opt.value))
    .map(opt => opt.name);
  const preview = labels.slice(0, 2).join('、');
  return labels.length > 2 ? `${preview} 等${labels.length}个` : preview || '未选择';
});

const graphSummary = computed(() => {
  if (!allowGraphSelect.value) return '由模式决定';
  const found = graphOptionsWithStats.value.find(g => g.value === selectedGraph.value);
  return found?.name || '未选择';
});

const ensureKbSelectionForMode = () => {
  if (!allowKbSelect.value) return;

  const validKbIds = new Set(
    (kbOptionsRaw.value || [])
      .map(db => db?.db_id)
      .filter(Boolean)
  );

  const current = Array.isArray(selectedKbIds.value) ? selectedKbIds.value : [];
  let next = current.filter(id => validKbIds.has(id));

  if (next.length === 0 && kbOptionsRaw.value.length > 0) {
    const fallbackId = kbOptionsRaw.value[0]?.db_id;
    if (fallbackId) next = [fallbackId];
  }

  const changed = next.length !== current.length || next.some((id, idx) => id !== current[idx]);
  if (changed) {
    selectedKbIds.value = next;
  }
};

// 切换知识库选择
const toggleKbSelection = (value) => {
  if (!allowKbSelect.value) return;
  const current = [...selectedKbIds.value];
  const index = current.indexOf(value);
  if (index > -1) {
    current.splice(index, 1);
  } else {
    current.push(value);
  }
  selectedKbIds.value = current;
};

const handleKbCheckChange = (value, checked) => {
  if (!allowKbSelect.value) return;
  const current = [...selectedKbIds.value];
  const index = current.indexOf(value);
  if (checked && index === -1) {
    current.push(value);
  } else if (!checked && index > -1) {
    current.splice(index, 1);
  }
  selectedKbIds.value = current;
};

const loadGraphStats = async (dbId) => {
  if (!dbId || dbId === 'neo4j') return;
  if (graphStats.value[dbId]) return;
  try {
    const stats = await lightragApi.getStats(dbId);
    if (stats?.data) {
      graphStats.value[dbId] = stats.data;
    }
  } catch (error) {
    console.warn('获取图谱统计失败:', error);
  }
};

// 选择图谱
const selectGraphOption = (value) => {
  if (!allowGraphSelect.value) return;
  selectedGraph.value = value;
  void loadGraphStats(value);
};

// 加载知识库列表
const loadKnowledgeBases = async () => {
  try {
    const res = await (databaseApi.getDatabasesForChat ? databaseApi.getDatabasesForChat() : databaseApi.getDatabases());
    kbOptionsRaw.value = res?.databases || res?.data || [];

    ensureKbSelectionForMode();
  } catch (error) {
    console.error('加载知识库列表失败:', error);
    kbOptionsRaw.value = [];
  }
};

// 加载知识图谱列表和统计信息
const loadGraphOptions = async () => {
  try {
    const allGraphs = [];
    
    // 1. 始终添加 Neo4j 原生图谱选项（与 GraphView 保持一致）
    let neo4jName = '大坝安全知识图谱';
    let neo4jEntityCount = 0;
    let neo4jRelationCount = 0;
    
    // 尝试加载已保存的别名
    try {
      const savedAliases = localStorage.getItem('graph_aliases');
      if (savedAliases) {
        const aliases = JSON.parse(savedAliases);
        if (aliases['neo4j']) {
          neo4jName = aliases['neo4j'];
        }
      }
    } catch (e) {}
    
    // 尝试获取 Neo4j 统计信息
    try {
      const neo4jInfo = await neo4jApi.getInfo();
      const info = neo4jInfo?.data || neo4jInfo;
      if (info?.entity_count !== undefined) {
        neo4jEntityCount = info.entity_count;
        neo4jRelationCount = info.relationship_count || 0;
      }
    } catch (e) {
      console.warn('获取 Neo4j 图谱信息失败:', e);
    }
    
    // 始终添加 Neo4j 选项
    allGraphs.push({
      db_id: 'neo4j',
      name: neo4jName,
      kb_type: 'neo4j',
      entity_count: neo4jEntityCount,
      relationship_count: neo4jRelationCount,
    });
    graphStats.value['neo4j'] = {
      total_nodes: neo4jEntityCount,
      total_edges: neo4jRelationCount,
      is_truncated: false,
    };
    
    // 2. 获取所有 LightRAG 知识库（与 GraphView 保持一致）
    try {
      const res = await lightragApi.getDatabases();
      // 安全地提取数据库列表
      let lightragDbs = res?.databases || res?.data?.databases || res?.data || [];
      if (!Array.isArray(lightragDbs)) {
        if (lightragDbs && typeof lightragDbs === 'object' && lightragDbs.databases) {
          lightragDbs = lightragDbs.databases;
        } else {
          lightragDbs = [];
        }
      }
      
      for (const db of lightragDbs) {
        const dbId = db.db_id || db.id || db.name;
        if (!dbId) continue;
        
        allGraphs.push({
          db_id: dbId,
          name: db.name || dbId,
          kb_type: 'lightrag',
          row_count: db.row_count || 0,
        });
      }
    } catch (e) {
      console.warn('获取 LightRAG 图谱列表失败:', e);
    }
    
    graphOptionsRaw.value = allGraphs;
    
    // 检查当前选中的图谱是否在列表中
    const currentValid = allGraphs.some(db => db.db_id === selectedGraph.value);
    
    // 如果当前选中的图谱无效或未选择，默认选中第一个
    if ((!selectedGraph.value || !currentValid) && allGraphs.length > 0) {
      selectedGraph.value = allGraphs[0].db_id;
    }
    void loadGraphStats(selectedGraph.value);
  } catch (error) {
    console.error('加载知识图谱列表失败:', error);
    graphOptionsRaw.value = [];
  }
};

// 初始化
onMounted(() => {
  loadKnowledgeBases();
  loadGraphOptions();
});

// 监听检索模式变化
watch(() => props.retrievalMode, () => {
  if (allowKbSelect.value) {
    ensureKbSelectionForMode();
  }
  if (!allowGraphSelect.value) {
    // 不清空图谱选择，保持上次选择
  } else if (!selectedGraph.value && graphOptionsWithStats.value.length > 0) {
    selectedGraph.value = graphOptionsWithStats.value[0].value;
  }
});
</script>

<style lang="less" scoped>
.cnki-resource-selector {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cnki-filter-group {
  background: rgba(15, 23, 42, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 8px;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;

  &:hover {
    border-color: rgba(6, 182, 212, 0.3);
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.1);
  }
  
  .filter-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    background: rgba(255, 255, 255, 0.03);
    cursor: pointer;
    user-select: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    transition: all 0.2s ease;
    
    &:hover {
      background: rgba(255, 255, 255, 0.08);
      
      .filter-title {
        color: #fff;
        text-shadow: 0 0 8px rgba(6, 182, 212, 0.5);
      }
    }
    
    .filter-title {
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
      font-size: 14px;
      transition: all 0.2s ease;
    }
    
    .filter-header-right {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .filter-stats-icon {
        color: #06b6d4;
        font-size: 14px;
        filter: drop-shadow(0 0 5px rgba(6, 182, 212, 0.5));
      }
      
      .collapse-icon {
        color: rgba(255, 255, 255, 0.4);
        font-size: 12px;
        transition: transform 0.2s;
      }
    }
  }
  
  .filter-body {
    padding: 8px 0;
    max-height: 280px;
    overflow-y: auto;
    background: rgba(15, 23, 42, 0.2);
    
    // Custom scrollbar
    &::-webkit-scrollbar {
      width: 4px;
    }
    &::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.02);
    }
    &::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 2px;
      &:hover {
        background: rgba(255, 255, 255, 0.2);
      }
    }
    
    .filter-disabled-hint {
      padding: 8px 16px;
      color: rgba(255, 255, 255, 0.5);
      font-size: 12px;
      background: rgba(245, 158, 11, 0.1);
      border-bottom: 1px solid rgba(245, 158, 11, 0.2);
      display: flex;
      align-items: center;
      gap: 6px;
      
      .anticon {
        color: #f59e0b;
      }
    }
    
    .filter-item {
      display: flex;
      align-items: center;
      padding: 8px 16px;
      cursor: pointer;
      transition: all 0.2s ease;
      border-left: 2px solid transparent;
      
      &:hover:not(.disabled) {
        background: rgba(6, 182, 212, 0.1);
        border-left-color: #06b6d4;
        
        .filter-label {
          color: #fff;
        }
      }
      
      &.disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      
      &.selected {
        background: rgba(6, 182, 212, 0.15);
        border-left-color: #06b6d4;
        
        .filter-label {
          color: #06b6d4;
          font-weight: 500;
          text-shadow: 0 0 8px rgba(6, 182, 212, 0.3);
        }
      }
      
      .filter-label {
        flex: 1;
        margin-left: 8px;
        color: rgba(255, 255, 255, 0.8);
        font-size: 14px;
        transition: all 0.2s ease;
      }
      
      .filter-count {
        color: rgba(255, 255, 255, 0.4);
        font-size: 12px;
        margin-left: 4px;
        font-family: monospace;
      }
      
      .truncated-warning {
        color: #f59e0b;
        margin-left: 4px;
        font-size: 12px;
      }

      :deep(.ant-checkbox-inner) {
        background-color: transparent;
        border-color: rgba(255, 255, 255, 0.3);
      }

      :deep(.ant-checkbox-checked .ant-checkbox-inner) {
        background-color: #06b6d4;
        border-color: #06b6d4;
        box-shadow: 0 0 5px rgba(6, 182, 212, 0.5);
      }

      :deep(.ant-radio-inner) {
        background-color: transparent;
        border-color: rgba(255, 255, 255, 0.3);
      }

      :deep(.ant-radio-checked .ant-radio-inner) {
        background-color: #06b6d4;
        border-color: #06b6d4;
        box-shadow: 0 0 5px rgba(6, 182, 212, 0.5);
        
        &::after {
          background-color: white;
        }
      }
    }
    
    .filter-empty {
      padding: 16px;
      text-align: center;
      color: rgba(255, 255, 255, 0.3);
      font-size: 13px;
    }
  }
}

.selection-summary {
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 12px 16px;
  transition: all 0.3s ease;

  &:hover {
    border-color: rgba(6, 182, 212, 0.2);
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.05);
  }
  
  .summary-row {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .summary-label {
      color: rgba(255, 255, 255, 0.5);
      font-size: 12px;
      min-width: 70px;
    }
    
    .summary-value {
      color: rgba(255, 255, 255, 0.9);
      font-size: 13px;
      
      &.mode-tag {
        background: rgba(6, 182, 212, 0.15);
        color: #06b6d4;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        border: 1px solid rgba(6, 182, 212, 0.2);
        box-shadow: 0 0 5px rgba(6, 182, 212, 0.1);
      }
    }
  }
}
</style>
