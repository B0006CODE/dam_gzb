<template>
  <div class="message-box" :class="[message.type, customClasses]">
    <!-- 用户消息 -->
    <p v-if="message.type === 'human'" class="message-text">{{ message.content }}</p>

    <!-- 助手消息 -->
    <div v-else-if="message.type === 'ai'" class="assistant-message">
      <div v-if="parsedData.reasoning_content" class="reasoning-box">
        <a-collapse v-model:activeKey="reasoningActiveKey" :bordered="false">
          <template #expandIcon="{ isActive }">
            <caret-right-outlined :rotate="isActive ? 90 : 0" />
          </template>
          <a-collapse-panel key="show" :header="message.status=='reasoning' ? '正在思考...' : '推理过程'" class="reasoning-header">
            <p class="reasoning-content">{{ parsedData.reasoning_content }}</p>
          </a-collapse-panel>
        </a-collapse>
      </div>

      <!-- 消息内容 -->
      <MdPreview v-if="parsedData.content" ref="editorRef"
        editorId="preview-only"
        theme="dark"
        previewTheme="github"
        codeTheme="atom"
        :showCodeRowNumber="false"
        :modelValue="parsedData.content"
        :key="message.id"
        class="message-md"/>

      <div v-else-if="parsedData.reasoning_content"  class="empty-block"></div>

      <div v-if="hasKnowledgeGraphData && (message.isLast || message.status === 'finished')" class="knowledge-graph-wrapper">
        <div class="kg-toggle-header" @click="toggleKnowledgeGraph">
          <div class="kg-toggle-left">
            <caret-right-outlined class="kg-caret" :rotate="kgCollapsed ? 0 : 90" />
            <span class="kg-title">{{ kgTitle }}</span>
          </div>
          <a-button
            size="small"
            class="kg-collapse-btn"
            :title="kgCollapsed ? '展开图谱过程' : '收起图谱过程'"
            @click.stop="toggleKnowledgeGraph"
          >
            {{ kgCollapsed ? '展开' : '收起' }}
          </a-button>
        </div>
        <KnowledgeGraphResult 
          v-show="!kgCollapsed"
          :data="message.knowledgeGraphData"
          :hide-header="true"
        />
      </div>

      <!-- 错误提示块 -->
      <div v-if="message.error_type" class="error-hint" :class="{ 'error-interrupted': message.error_type === 'interrupted', 'error-unexpect': message.error_type === 'unexpect' }">
        <span v-if="message.error_type === 'interrupted'">回答生成已中断</span>
        <span v-else-if="message.error_type === 'unexpect'">生成过程中出现异常</span>
      </div>

      <div v-if="filteredToolCalls && Object.keys(filteredToolCalls).length > 0" class="tool-calls-container">
        <div v-for="(toolCall, index) in filteredToolCalls" :key="index" class="tool-call-container">
          <div v-if="toolCall" class="tool-call-display" :class="{ 'is-collapsed': !expandedToolCalls.has(toolCall.id) }">
            <div class="tool-header" @click="toggleToolCall(toolCall.id)">
              <span v-if="!toolCall.tool_call_result">
                <span><Loader size="16" class="tool-loader rotate tool-loading" /></span> &nbsp;
                <span>正在调用工具: </span>
                <span class="tool-name">{{ getToolNameByToolCall(toolCall) }}</span>
              </span>
              <span v-else>
                <span><CircleCheckBig size="16" class="tool-loader tool-success" /></span> &nbsp; 工具 <span class="tool-name">{{ getToolNameByToolCall(toolCall) }}</span> 执行完成
              </span>
            </div>
            <div class="tool-content" v-show="expandedToolCalls.has(toolCall.id)">
              <div class="tool-params" v-if="toolCall.args || toolCall.function.arguments">
                <div class="tool-params-content">
                  <strong>参数:</strong> {{ toolCall.args || toolCall.function.arguments }}
                </div>
              </div>
              <div class="tool-result" v-if="toolCall.tool_call_result && toolCall.tool_call_result.content">
                <div class="tool-result-content" :data-tool-call-id="toolCall.id">
                  <ToolResultRenderer
                    :tool-name="toolCall.name || toolCall.function.name"
                    :result-content="toolCall.tool_call_result.content"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="citationList.length > 0" class="citations-wrapper">
        <div class="citations-title">引用来源</div>
        <ol class="citations-list">
          <li v-for="citation in citationList" :key="citationKey(citation)" class="citation-item">
            <div class="citation-main">
              <span class="citation-index">[{{ citation.index }}]</span>
              <a
                v-if="isHttpLink(citation.path)"
                :href="citation.path"
                target="_blank"
                rel="noopener noreferrer"
                class="citation-link"
              >
                {{ formatCitationTitle(citation) }}
              </a>
              <span v-else class="citation-text">{{ formatCitationTitle(citation) }}</span>
            </div>
          </li>
        </ol>
      </div>

      <div v-if="message.isStoppedByUser" class="retry-hint">
        你停止生成了本次回答
        <span class="retry-link" @click="emit('retryStoppedMessage', message.id)">重新编辑问题</span>
      </div>



      <!-- 错误消息 -->
    </div>

    <div v-if="infoStore.debugMode" class="status-info">{{ message }}</div>

    <!-- 自定义内容 -->
    <slot></slot>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { CaretRightOutlined } from '@ant-design/icons-vue';

import { Loader, CircleCheckBig } from 'lucide-vue-next';
import { ToolResultRenderer, KnowledgeGraphResult } from '@/components/ToolCallingResult'
import { useAgentStore } from '@/stores/agent'
import { useInfoStore } from '@/stores/info'
import { useUserStore } from '@/stores/user'
import { storeToRefs } from 'pinia'


import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css';

const props = defineProps({
  // 消息角色：'user'|'assistant'|'sent'|'received'
  message: {
    type: Object,
    required: true
  },
  // 是否正在处理中
  isProcessing: {
    type: Boolean,
    default: false
  },
  // 自定义类
  customClasses: {
    type: Object,
    default: () => ({})
  },
  // 是否显示推理过程
  showRefs: {
    type: [Array, Boolean],
    default: () => false
  },
  // 是否为最新消息
  isLatestMessage: {
    type: Boolean,
    default: false
  },
  // 是否显示调试信息 (已废弃，使用 infoStore.debugMode)
  debugMode: {
    type: Boolean,
    default: false
  }
});

const editorRef = ref()

const emit = defineEmits(['retry', 'retryStoppedMessage', 'openRefs']);

// 推理面板展开状态
const reasoningActiveKey = ref(['hide']);
const expandedToolCalls = ref(new Set()); // 展开的工具调用集合

// 引入智能体 store
const agentStore = useAgentStore();
const infoStore = useInfoStore();
const userStore = useUserStore();
// KG 折叠开关（默认收起）
const kgCollapsed = ref(true);
const { availableTools } = storeToRefs(agentStore);
const { isAdmin } = storeToRefs(userStore);

// 过滤工具调用（非管理员隐藏 sequentialthinking）
const filteredToolCalls = computed(() => {
  const toolCalls = props.message.tool_calls;
  if (!toolCalls) return {};
  
  // 管理员可以看到所有工具
  if (isAdmin.value) return toolCalls;
  
  // 非管理员过滤掉 sequentialthinking 工具
  if (Array.isArray(toolCalls)) {
    return toolCalls.filter(tc => {
      const toolName = tc?.name || tc?.function?.name || '';
      return !toolName.toLowerCase().includes('sequentialthinking');
    });
  }
  
  // 对象格式
  const filtered = {};
  for (const [key, tc] of Object.entries(toolCalls)) {
    const toolName = tc?.name || tc?.function?.name || '';
    if (!toolName.toLowerCase().includes('sequentialthinking')) {
      filtered[key] = tc;
    }
  }
  return filtered;
});

// 工具相关方法
const getToolNameByToolCall = (toolCall) => {
  const toolId = toolCall.name || toolCall.function.name;
  const toolsList = availableTools.value ? Object.values(availableTools.value) : [];
  const tool = toolsList.find(t => t.id === toolId);
  return tool ? tool.name : toolId;
};

const parsedData = computed(() => {
  // Start with default values from the prop to avoid mutation.
  let content = props.message.content.trim() || '';
  let reasoning_content = props.message.additional_kwargs?.reasoning_content || '';

  if (reasoning_content) {
    return {
      content,
      reasoning_content,
    }
  }

  // Regex to find <think>...</think> or an unclosed <think>... at the end of the string.
  const thinkRegex = /<think>(.*?)<\/think>|<think>(.*?)$/s;
  const thinkMatch = content.match(thinkRegex);

  if (thinkMatch) {
    // The captured reasoning is in either group 1 (closed tag) or 2 (unclosed tag).
    reasoning_content = (thinkMatch[1] || thinkMatch[2] || '').trim();
    // Remove the entire matched <think> block from the original content.
    content = content.replace(thinkMatch[0], '').trim();
  }

  return {
    content,
    reasoning_content,
  };
});

const toggleToolCall = (toolCallId) => {
  if (expandedToolCalls.value.has(toolCallId)) {
    expandedToolCalls.value.delete(toolCallId);
  } else {
    expandedToolCalls.value.add(toolCallId);
  }
};

const toggleKnowledgeGraph = () => {
  kgCollapsed.value = !kgCollapsed.value;
};

// 是否存在可视化的知识图谱数据（搜索结果或统计结果）
const hasKnowledgeGraphData = computed(() => {
  const kg = props.message && props.message.knowledgeGraphData;
  if (!kg) return false;
  
  // 搜索类结果：检查是否有三元组
  const triples = Array.isArray(kg.triples) ? kg.triples : [];
  if (triples.length > 0) return true;

  // 搜索类结果：支持 content-only（如部分嵌套/LightRAG 返回）
  const content = typeof kg.content === 'string' ? kg.content.trim() : '';
  if ((kg.query_type === 'search' || kg.query_type === undefined) && content) return true;
  
  // 统计类结果：检查 query_type
  if (kg.query_type === 'statistics' && kg.total_count !== undefined) return true;
  
  return false;
});

// 知识图谱数据标题（根据类型动态显示）
const kgTitle = computed(() => {
  const kg = props.message && props.message.knowledgeGraphData;
  if (kg && kg.query_type === 'statistics') {
    return '图谱过程（统计）';
  }
  return '图谱过程';
});

const citationList = computed(() => {
  const list = Array.isArray(props.message?.citations) ? props.message.citations : [];
  return list
    .filter((item) => item && (item.path || item.title || item.referenceId))
    .map((item, index) => ({
      ...item,
      index: Number.isFinite(item.index) ? item.index : index + 1,
    }));
});

const isHttpLink = (value) => {
  if (typeof value !== 'string') return false;
  return /^https?:\/\//i.test(value.trim());
};

const formatCitationTitle = (citation) => {
  const path = typeof citation?.path === 'string' ? citation.path.trim() : '';
  if (path && !isHttpLink(path)) {
    const parts = path.split(/[\\/]/).filter(Boolean);
    return parts[parts.length - 1] || path;
  }

  const title = typeof citation?.title === 'string' ? citation.title.trim() : '';
  if (title) return title;

  if (path) return path;

  if (citation?.referenceId) return `参考 ${citation.referenceId}`;
  return '未知来源';
};

const citationKey = (citation) => {
  return `${citation?.sourceType || 'source'}-${citation?.referenceId || ''}-${citation?.path || ''}-${citation?.title || ''}-${citation?.index || ''}`;
};
</script>

<style lang="less" scoped>
.message-box {
  display: inline-block;
  border-radius: 1.5rem;
  margin: 0.8rem 0;
  padding: 0.625rem 1.25rem;
  user-select: text;
  word-break: break-word;
  word-wrap: break-word;
  font-size: 15px;
  line-height: 24px;
  box-sizing: border-box;
  color: var(--text-primary);
  max-width: 100%;
  position: relative;
  letter-spacing: .25px;

  &.human, &.sent {
    max-width: 85%;
    color: white;
    background: linear-gradient(135deg, #06b6d4, #3b82f6);
    align-self: flex-end;
    border-radius: 16px 16px 4px 16px;
    padding: 10px 16px;
    box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  &.assistant, &.received, &.ai {
    color: initial;
    width: 100%;
    text-align: left;
    margin: 0;
    padding: 0px;
    background-color: transparent !important;
    border-radius: 0;
  }

  .message-text {
    max-width: 100%;
    margin-bottom: 0;
    white-space: pre-line;
  }

  .err-msg {
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 0.5rem 1rem;
    border-radius: 8px;
    text-align: left;
    background: rgba(239, 68, 68, 0.1);
    margin-bottom: 10px;
    cursor: pointer;
  }

  .searching-msg {
    color: var(--text-secondary);
    animation: colorPulse 1s infinite ease-in-out;
  }

  .reasoning-box {
    margin-top: 12px;
    margin-bottom: 16px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    background: rgba(15, 23, 42, 0.3);
    backdrop-filter: blur(8px);
    overflow: hidden;
    transition: all 0.3s ease;

    :deep(.ant-collapse) {
      background-color: transparent;
      border: none;

      .ant-collapse-item {
        border: none;

        .ant-collapse-header {
          padding: 8px 12px;
          font-size: 14px;
          font-weight: 500;
          color: var(--text-secondary);
          transition: all 0.2s ease;

          .ant-collapse-expand-icon {
            color: var(--text-tertiary);
          }
        }

        .ant-collapse-content {
          border: none;
          background-color: transparent;

          .ant-collapse-content-box {
            padding: 16px;
            background-color: rgba(0, 0, 0, 0.1);
          }
        }
      }
    }

    .reasoning-content {
      font-size: 13px;
      color: var(--text-secondary);
      white-space: pre-wrap;
      margin: 0;
      line-height: 1.6;
    }
  }

  .assistant-message {
    width: 100%;
  }

  .citations-wrapper {
    margin-top: 12px;
    padding: 10px 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    background: rgba(15, 23, 42, 0.35);
  }

  .citations-title {
    margin-bottom: 6px;
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.4px;
  }

  .citations-list {
    margin: 0;
    padding-left: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .citation-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.5;
  }

  .citation-main {
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex-wrap: wrap;
  }

  .citation-index {
    color: var(--text-tertiary);
    font-size: 12px;
  }

  .citation-link {
    color: var(--main-color);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  .citation-text {
    color: var(--text-secondary);
    word-break: break-all;
  }

  .error-hint {
    margin: 10px 0;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;

    &.error-interrupted {
      background-color: rgba(245, 158, 11, 0.1);
      color: #f59e0b;
    }

    &.error-unexpect {
      background-color: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }

    span {
      line-height: 1.5;
    }
  }

  .status-info {
    display: block;
    background-color: rgba(0, 0, 0, 0.3);
    color: var(--text-tertiary);
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 10px;
    font-size: 12px;
    font-family: monospace;
    max-height: 200px;
    overflow-y: auto;
  }

  :deep(.tool-calls-container) {
    width: 100%;
    margin-top: 10px;

    .tool-call-container {
      margin-bottom: 10px;

      &:last-child {
        margin-bottom: 0;
      }
    }
  }

  :deep(.tool-call-display) {
    background: rgba(15, 23, 42, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    overflow: hidden;
    transition: all 0.3s ease;
    backdrop-filter: blur(4px);

    .tool-header {
      padding: 8px 12px;
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary);
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      user-select: none;
      position: relative;
      transition: color 0.2s ease;
      align-items: center;

      .anticon {
        color: var(--main-color);
        font-size: 16px;
      }

      .tool-name {
        font-weight: 600;
        color: var(--main-color);
      }

      span {
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .tool-loader {
        margin-top: 2px;
        color: var(--main-color);
      }

      .tool-loader.rotate {
        animation: rotate 2s linear infinite;
      }

      .tool-loader.tool-success {
        color: var(--color-success);
      }

      .tool-loader.tool-error {
        color: var(--color-error);
      }

      .tool-loader.tool-loading {
        color: var(--main-color);
      }
    }

    .tool-content {
      transition: all 0.3s ease;

      .tool-params {
        padding: 8px 12px;
        background-color: rgba(0, 0, 0, 0.2);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);

        .tool-params-content {
          margin: 0;
          font-size: 13px;
          overflow-x: auto;
          color: var(--text-secondary);
          line-height: 1.5;

          pre {
            margin: 0;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          }
        }
      }

      .tool-result {
        padding: 0;
        background-color: transparent;

        .tool-result-header {
          padding: 12px 16px;
          background-color: rgba(255, 255, 255, 0.05);
          font-size: 12px;
          color: var(--text-secondary);
          font-weight: 500;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .tool-result-content {
          padding: 0;
          background-color: transparent;
        }
      }
    }

    &.is-collapsed {
      .tool-header {
        border-bottom: none;
      }
    }
  }
}

.retry-hint {
  margin-top: 8px;
  padding: 8px 16px;
  color: var(--text-secondary);
  font-size: 14px;
  text-align: left;
}

.retry-link {
  color: var(--main-color);
  cursor: pointer;
  margin-left: 4px;

  &:hover {
    text-decoration: underline;
  }
}

.ant-btn-icon-only {
  &:has(.anticon-stop) {
    background-color: #ef4444 !important;

    &:hover {
      background-color: #f87171 !important;
    }
  }
}

@keyframes colorPulse {
  0% { color: var(--text-secondary); }
  50% { color: var(--text-primary); }
  100% { color: var(--text-secondary); }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

<style lang="less" scoped>
:deep(.message-md) {
  margin: 8px 0;
  background-color: transparent !important;
}

:deep(.message-md .md-editor),
:deep(.message-md .md-editor-preview),
:deep(.message-md .md-editor-preview-wrapper),
:deep(.message-md .md-editor-content) {
  background: transparent !important;
  background-color: transparent !important;
}

:deep(.md-editor-dark) {
  --md-bk-color: transparent !important;
}

:deep(.message-md .md-editor-preview-wrapper) {
  max-width: 100%;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', 'Hiragino Sans GB', 'Source Han Sans CN', 'Courier New', monospace;

  #preview-only-preview {
    font-size: 1rem;
    line-height: 1.75;
    color: var(--text-primary);
    background-color: transparent !important;
  }


  h1, h2 {
    font-size: 1.2rem;
    color: var(--text-primary);
  }

  h3, h4 {
    font-size: 1.1rem;
    color: var(--text-primary);
  }

  h5, h6 {
    font-size: 1rem;
    color: var(--text-secondary);
  }

  strong {
    font-weight: 500;
    color: var(--main-color);
  }

  li > p, ol > p, ul > p {
    margin: 0.25rem 0;
  }

  ul li::marker,
  ol li::marker {
    color: var(--main-color);
  }

  ul, ol {
    padding-left: 1.625rem;
  }

  cite {
    font-size: 12px;
    color: var(--text-secondary);
    font-style: normal;
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    outline: 2px solid rgba(255, 255, 255, 0.05);
  }

  a {
    color: var(--main-color);
  }

  .md-editor-code {
    border: var(--glass-border);
    border-radius: 8px;

    .md-editor-code-head {
      background-color: rgba(0, 0, 0, 0.3);
      z-index: 1;

      .md-editor-collapse-tips {
        color: var(--text-tertiary);
      }
    }
  }

  code {
    font-size: 13px;
    font-family: 'Menlo', 'Monaco', 'Consolas', 'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', 'Hiragino Sans GB', 'Source Han Sans CN', 'Courier New', monospace;
    line-height: 1.5;
    letter-spacing: 0.025em;
    tab-size: 4;
    -moz-tab-size: 4;
    background-color: rgba(255, 255, 255, 0.1);
    color: var(--text-primary);
  }

  p:last-child {
    margin-bottom: 0;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 2em 0;
    font-size: 15px;
    display: table;
    outline: 1px solid rgba(255, 255, 255, 0.1);
    outline-offset: 14px;
    border-radius: 12px;

    thead tr th{
      padding-top: 0;
    }

    thead th,
    tbody th {
      border: none;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    tbody tr:last-child td {
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      border: none;
      padding-bottom: 0;
    }
  }

  th,
  td {
    padding: 0.5rem 0rem;
    text-align: left;
    border: none;
  }

  td {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-secondary);
  }

  th {
    font-weight: 600;
    color: var(--text-primary);
  }

  tr {
    background-color: transparent;
  }
}

:deep(.chat-box.font-smaller #preview-only-preview) {
  font-size: 14px;

  h1, h2 {
    font-size: 1.1rem;
  }

  h3, h4 {
    font-size: 1rem;
  }
}

:deep(.chat-box.font-larger #preview-only-preview) {
  font-size: 16px;

  h1, h2 {
    font-size: 1.3rem;
  }

  h3, h4 {
    font-size: 1.2rem;
  }

  h5, h6 {
    font-size: 1.1rem;
  }

  code {
    font-size: 14px;
  }
}

/* KG toggle header styles */
.knowledge-graph-wrapper {
  margin-top: 8px;
  border: var(--glass-border);
  border-radius: 8px;
  background: var(--bg-elevated);
}
.knowledge-graph-wrapper .kg-toggle-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  cursor: pointer;
}
.knowledge-graph-wrapper .kg-toggle-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.knowledge-graph-wrapper .kg-caret {
  color: var(--text-tertiary);
  transition: transform 0.2s ease;
}
.knowledge-graph-wrapper .kg-title {
  color: var(--main-color);
  font-weight: 500;
}
.knowledge-graph-wrapper .kg-collapse-btn {
  min-width: 56px;
  height: 24px;
  padding: 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  
  &:hover {
    color: var(--main-color);
    border-color: var(--main-color);
  }
}
</style>
