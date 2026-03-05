<template>
  <div class="hybrid-search-result">
    <div class="result-summary">
      <InfoCircleOutlined />
      <span>{{ data.summary }}</span>
    </div>

    <!-- 知识库结果 -->
    <div class="result-section" v-if="data.knowledge_base_results && data.knowledge_base_results.length > 0">
      <div class="section-header" @click="kbCollapsed = !kbCollapsed">
        <DatabaseOutlined />
        <span class="section-title">知识库检索结果 ({{ data.knowledge_base_results.length }})</span>
        <UpOutlined v-if="!kbCollapsed" class="collapse-icon" />
        <DownOutlined v-else class="collapse-icon" />
      </div>
      <div class="section-content" v-show="!kbCollapsed">
        <div class="kb-item" v-for="(item, index) in data.knowledge_base_results" :key="index">
          <div class="item-header">
            <span class="source-tag">{{ item.source_db || item.metadata?.source || '知识库' }}</span>
            <span class="score-tag" v-if="item.score">相似度: {{ (item.score * 100).toFixed(1) }}%</span>
          </div>
          <div class="item-content">{{ truncateContent(item.content) }}</div>
        </div>
      </div>
    </div>

    <!-- 知识图谱结果 -->
    <div class="result-section" v-if="hasGraphResults">
      <div class="section-header" @click="graphCollapsed = !graphCollapsed">
        <ApartmentOutlined />
        <span class="section-title">
          知识图谱检索结果
          <span class="graph-type-tag" v-if="graphType">{{ graphType === 'lightrag' ? 'LightRAG' : 'Neo4j' }}</span>
        </span>
        <UpOutlined v-if="!graphCollapsed" class="collapse-icon" />
        <DownOutlined v-else class="collapse-icon" />
      </div>
      <div class="section-content" v-show="!graphCollapsed">
        <!-- Neo4j 三元组展示 -->
        <div class="graph-triples" v-if="data.knowledge_graph_results?.triples && data.knowledge_graph_results.triples.length > 0">
          <div class="triple-item" v-for="(triple, index) in data.knowledge_graph_results.triples.slice(0, 10)" :key="index">
            <span class="entity source">{{ triple.source || triple[0] }}</span>
            <span class="relation">{{ triple.relation || triple[1] }}</span>
            <span class="entity target">{{ triple.target || triple[2] }}</span>
          </div>
          <div class="more-hint" v-if="data.knowledge_graph_results.triples.length > 10">
            ... 还有 {{ data.knowledge_graph_results.triples.length - 10 }} 条结果
          </div>
        </div>
        <!-- LightRAG 文本内容展示 -->
        <div class="graph-content" v-else-if="data.knowledge_graph_results?.content">
          <div class="content-text">{{ truncateContent(data.knowledge_graph_results.content, 500) }}</div>
        </div>
        <!-- 错误展示 -->
        <div class="graph-error" v-else-if="data.knowledge_graph_results?.error">
          <WarningOutlined /> {{ data.knowledge_graph_results.error }}
        </div>
        <!-- 无结果 -->
        <div class="graph-empty" v-else>
          暂无相关图谱数据
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  InfoCircleOutlined, 
  DatabaseOutlined, 
  ApartmentOutlined,
  UpOutlined,
  DownOutlined,
  WarningOutlined
} from '@ant-design/icons-vue'

const props = defineProps({
  data: {
    type: Object,
    required: true
  }
})

const kbCollapsed = ref(false)
const graphCollapsed = ref(false)

const graphType = computed(() => {
  return props.data.knowledge_graph_results?.graph_type || null
})

const hasGraphResults = computed(() => {
  const graphData = props.data.knowledge_graph_results
  if (!graphData) return false
  if (graphData.error) return true
  if (graphData.triples && graphData.triples.length > 0) return true
  if (graphData.content) return true
  return false
})

const graphTriplesCount = computed(() => {
  return props.data.knowledge_graph_results?.triples?.length || 0
})

const truncateContent = (content, maxLength = 300) => {
  if (!content) return ''
  if (content.length <= maxLength) return content
  return content.substring(0, maxLength) + '...'
}
</script>

<style lang="less" scoped>
.hybrid-search-result {
  background: rgba(15, 23, 42, 0.4);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;

  .result-summary {
    padding: 12px 16px;
    background: rgba(6, 182, 212, 0.1);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    display: flex;
    align-items: center;
    gap: 8px;
    color: #06b6d4;
    font-size: 13px;
  }

  .result-section {
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);

    &:last-child {
      border-bottom: none;
    }

    .section-header {
      padding: 10px 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      background: rgba(0, 0, 0, 0.2);
      transition: all 0.2s;
      color: rgba(255, 255, 255, 0.8);

      &:hover {
        background: rgba(0, 0, 0, 0.3);
      }

      .section-title {
        flex: 1;
        font-weight: 500;
        font-size: 13px;
      }

      .collapse-icon {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.5);
      }
    }

    .section-content {
      padding: 12px 16px;
      max-height: 300px;
      overflow-y: auto;
    }
  }

  .kb-item {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;

    &:last-child {
      margin-bottom: 0;
    }

    .item-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;

      .source-tag {
        background: rgba(6, 182, 212, 0.2);
        color: #06b6d4;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
      }

      .score-tag {
        color: rgba(255, 255, 255, 0.5);
        font-size: 11px;
      }
    }

    .item-content {
      color: rgba(255, 255, 255, 0.8);
      font-size: 13px;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }
  }

  .graph-triples {
    .triple-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);

      &:last-child {
        border-bottom: none;
      }

      .entity {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
      }

      .relation {
        color: rgba(255, 255, 255, 0.6);
        font-size: 12px;

        &::before {
          content: '→';
          margin-right: 4px;
        }
        &::after {
          content: '→';
          margin-left: 4px;
        }
      }
    }

    .more-hint {
      padding: 8px 0;
      color: rgba(255, 255, 255, 0.5);
      font-size: 12px;
      text-align: center;
    }
  }

  .graph-content {
    .content-text {
      color: rgba(255, 255, 255, 0.8);
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(0, 0, 0, 0.2);
      padding: 12px;
      border-radius: 8px;
      border-left: 3px solid #8b5cf6;
    }
  }

  .graph-error {
    color: #f59e0b;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .graph-empty {
    color: rgba(255, 255, 255, 0.5);
    font-size: 13px;
    text-align: center;
    padding: 16px;
  }

  .graph-type-tag {
    background: rgba(139, 92, 246, 0.2);
    color: #8b5cf6;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    margin-left: 8px;
    font-weight: normal;
  }
}
</style>
