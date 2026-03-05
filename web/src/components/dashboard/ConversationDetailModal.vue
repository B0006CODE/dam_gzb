<template>
  <!-- 对话详情模态框 -->
  <a-modal
    v-model:open="modalVisible"
    :title="`对话详情 - ${conversationDetail?.title || '未命名对话'}`"
    width="1200px"
    :footer="null"
    class="conversation-detail-modal"
  >
    <div v-if="loading" class="loading-container">
      <a-spin size="large" tip="加载对话详情中..." />
    </div>

    <div v-else-if="conversationDetail" class="conversation-detail">
      <!-- 对话基本信息 -->
      <div class="conversation-header">
        <a-descriptions :column="3" size="small" bordered>
          <a-descriptions-item label="对话ID">{{ conversationDetail.thread_id }}</a-descriptions-item>
          <a-descriptions-item label="用户ID">{{ conversationDetail.user_id }}</a-descriptions-item>
          <a-descriptions-item label="智能体">{{ conversationDetail.agent_id }}</a-descriptions-item>
          <a-descriptions-item label="消息数量">{{ conversationDetail.message_count }}</a-descriptions-item>
          <a-descriptions-item label="Token消耗">{{ formatNumber(conversationDetail.total_tokens) }}</a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="conversationDetail.status === 'active' ? 'green' : 'red'" size="small">
              {{ conversationDetail.status === 'active' ? '活跃' : '已删除' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="创建时间" :span="2">{{ formatDateTime(conversationDetail.created_at) }}</a-descriptions-item>
          <a-descriptions-item label="更新时间">{{ formatDateTime(conversationDetail.updated_at) }}</a-descriptions-item>
        </a-descriptions>
      </div>

      <!-- 消息列表 -->
      <div class="messages-section">
        <h4 class="section-title">对话消息</h4>
        <div class="messages-container">
          <div
            v-for="(message, index) in conversationDetail.messages"
            :key="message.id"
            class="message-item"
            :class="{ 'user-message': message.role === 'user', 'assistant-message': message.role === 'assistant' }"
          >
            <!-- 消息头部 -->
            <div class="message-header">
              <div class="message-role">
                <a-avatar
                  :size="24"
                  :style="{ backgroundColor: message.role === 'user' ? '#1890ff' : '#52c41a' }"
                >
                  {{ message.role === 'user' ? 'U' : 'A' }}
                </a-avatar>
                <span class="role-text">
                  {{ message.role === 'user' ? '用户' : 'AI助手' }}
                </span>
              </div>
              <div class="message-time">{{ formatTime(message.created_at) }}</div>
            </div>

            <!-- 消息内容 -->
            <div class="message-content">
              <div class="content-text" v-html="formatMessageContent(message.content)"></div>

              <!-- 工具调用信息 -->
              <div v-if="message.tool_calls && message.tool_calls.length > 0" class="tool-calls-section">
                <a-collapse size="small" :bordered="false">
                  <a-collapse-panel
                    v-for="(toolCall, toolIndex) in message.tool_calls"
                    :key="toolCall.id"
                    :header="`工具调用: ${toolCall.tool_name}`"
                    class="tool-call-panel"
                  >
                    <div class="tool-call-content">
                      <div class="tool-status">
                        <a-tag
                          :color="toolCall.status === 'success' ? 'green' : 'red'"
                          size="small"
                        >
                          {{ toolCall.status === 'success' ? '成功' : '失败' }}
                        </a-tag>
                      </div>

                      <!-- 工具输入 -->
                      <div class="tool-input">
                        <h5>输入参数:</h5>
                        <pre class="code-block">{{ formatJson(toolCall.tool_input) }}</pre>
                      </div>

                      <!-- 工具输出 -->
                      <div v-if="toolCall.tool_output" class="tool-output">
                        <h5>输出结果:</h5>
                        <pre class="code-block">{{ formatJson(toolCall.tool_output) }}</pre>
                      </div>
                    </div>
                  </a-collapse-panel>
                </a-collapse>
              </div>

              <!-- 消息类型标签 -->
              <div class="message-type">
                <a-tag color="blue" size="small">{{ getMessageTypeLabel(message.message_type) }}</a-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!conversationDetail.messages || conversationDetail.messages.length === 0" class="empty-state">
        <a-empty description="暂无消息内容" />
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <a-result
        status="error"
        title="加载失败"
        :sub-title="error"
      >
        <template #extra>
          <a-button type="primary" @click="loadConversationDetail">
            重试
          </a-button>
        </template>
      </a-result>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { dashboardApi } from '@/apis/dashboard_api'
import { formatDateTime, formatFullDateTime } from '@/utils/time'

// Props
const props = defineProps({
  threadId: {
    type: String,
    default: null
  }
})

// 响应式数据
const modalVisible = ref(false)
const loading = ref(false)
const error = ref('')
const conversationDetail = ref(null)

// 显示模态框
const show = (threadId) => {
  if (threadId) {
    modalVisible.value = true
    loadConversationDetail(threadId)
  }
}

// 隐藏模态框
const hide = () => {
  modalVisible.value = false
  conversationDetail.value = null
  error.value = ''
}

// 暴露方法给父组件
defineExpose({ show, hide })

// 加载对话详情
const loadConversationDetail = async (threadId) => {
  const targetThreadId = threadId || props.threadId
  if (!targetThreadId) {
    error.value = '缺少对话ID'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await dashboardApi.getConversationDetail(targetThreadId)
    conversationDetail.value = response
    console.log('对话详情加载成功:', response)
  } catch (err) {
    console.error('加载对话详情失败:', err)
    error.value = err.message || '加载对话详情失败'
    message.error('加载对话详情失败')
  } finally {
    loading.value = false
  }
}

// 格式化时间
const formatTime = (dateString) => {
  return formatFullDateTime(dateString)
}

// 格式化数字
const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString()
}

// 格式化JSON
const formatJson = (jsonString) => {
  try {
    if (typeof jsonString === 'object') {
      return JSON.stringify(jsonString, null, 2)
    }
    const parsed = JSON.parse(jsonString)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return jsonString
  }
}

// 格式化消息内容
const formatMessageContent = (content) => {
  if (!content) return ''

  // 简单的Markdown转HTML处理
  let formatted = content
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')

  return formatted
}

// 获取消息类型标签
const getMessageTypeLabel = (messageType) => {
  const typeMap = {
    'text': '文本消息',
    'tool_call': '工具调用',
    'tool_response': '工具响应',
    'system': '系统消息',
    'error': '错误消息'
  }
  return typeMap[messageType] || messageType
}

// 监听 threadId 变化，重新加载数据
watch(() => props.threadId, (newThreadId) => {
  if (newThreadId && modalVisible.value) {
    loadConversationDetail(newThreadId)
  }
})
</script>

<style scoped lang="less">
// 加载状态
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px 0;
}

// 对话详情容器
.conversation-detail {
  .conversation-header {
    margin-bottom: 24px;

    :deep(.ant-descriptions-item-label) {
      font-weight: 500;
      color: rgba(255, 255, 255, 0.6);
      background: rgba(255, 255, 255, 0.02);
    }

    :deep(.ant-descriptions-item-content) {
      color: #fff;
    }

    :deep(.ant-descriptions-bordered .ant-descriptions-item-label),
    :deep(.ant-descriptions-bordered .ant-descriptions-item-content) {
      border-color: rgba(255, 255, 255, 0.1);
    }
  }
}

// 消息区域
.messages-section {
  .section-title {
    margin-bottom: 16px;
    color: #fff;
    font-size: 16px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;

    &::before {
      content: '';
      display: block;
      width: 4px;
      height: 16px;
      background: #06b6d4;
      border-radius: 2px;
      box-shadow: 0 0 8px #06b6d4;
    }
  }
}

.messages-container {
  max-height: 600px;
  overflow-y: auto;
  padding-right: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background-color: rgba(15, 23, 42, 0.35);

  // 滚动条样式
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.06);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.14);
    border-radius: 3px;

    &:hover {
      background: rgba(255, 255, 255, 0.22);
    }
  }
}

// 消息项
.message-item {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);

  &:last-child {
    border-bottom: none;
  }

  &.user-message {
    background-color: rgba(6, 182, 212, 0.05);

    .message-role .role-text {
      color: #06b6d4;
    }
  }

  &.assistant-message {
    background-color: rgba(16, 185, 129, 0.05);

    .message-role .role-text {
      color: #10b981;
    }
  }
}

// 消息头部
.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.message-role {
  display: flex;
  align-items: center;
  gap: 8px;

  .role-text {
    font-weight: 500;
    font-size: 13px;
  }
}

.message-time {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

// 消息内容
.message-content {
  .content-text {
    line-height: 1.6;
    color: rgba(255, 255, 255, 0.9);
    margin-bottom: 12px;
    word-break: break-word;

    :deep(code) {
      background-color: rgba(255, 255, 255, 0.1);
      padding: 2px 4px;
      border-radius: 3px;
      font-size: 12px;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      color: #e2e8f0;
    }
  }
}

// 工具调用区域
.tool-calls-section {
  margin-top: 12px;

  :deep(.ant-collapse) {
    background: transparent;
    border: none;
  }

  :deep(.ant-collapse-item) {
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    margin-bottom: 8px;
  }

  :deep(.ant-collapse-header) {
    background-color: rgba(15, 23, 42, 0.45);
    border-radius: 6px 6px 0 0;
    font-size: 13px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.8) !important;
  }

  :deep(.ant-collapse-content) {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    background-color: rgba(15, 23, 42, 0.35);
    color: rgba(255, 255, 255, 0.8);
  }
}

.tool-call-content {
  .tool-status {
    margin-bottom: 12px;
  }

  .tool-input,
  .tool-output {
    margin-bottom: 12px;

    h5 {
      margin-bottom: 6px;
      color: rgba(255, 255, 255, 0.6);
      font-size: 13px;
      font-weight: 500;
    }
  }

  .code-block {
    background-color: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    padding: 8px;
    font-size: 12px;
    line-height: 1.4;
    color: #e2e8f0;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
    margin: 0;
  }
}

// 消息类型标签
.message-type {
  margin-top: 8px;
}

// 空状态
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px 0;
  
  :deep(.ant-empty-description) {
    color: rgba(255, 255, 255, 0.5);
  }
}

// 错误状态
.error-state {
  padding: 20px 0;
}

// 模态框样式
:deep(.conversation-detail-modal) {
  .ant-modal-content {
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .ant-modal-header {
    background: transparent;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  .ant-modal-title {
    color: #fff;
  }

  .ant-modal-close {
    color: rgba(255, 255, 255, 0.6);
    &:hover {
      color: #fff;
    }
  }

  .ant-modal-body {
    max-height: 80vh;
    overflow-y: auto;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .messages-container {
    max-height: 400px;
  }

  .message-item {
    padding: 12px;
  }

  .message-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .tool-call-content .code-block {
    max-height: 150px;
    font-size: 11px;
  }
}

// 消息区域
.messages-section {
  .section-title {
    margin-bottom: 16px;
    color: var(--gray-800);
    font-size: 16px;
    font-weight: 600;
  }
}

.messages-container {
  max-height: 600px;
  overflow-y: auto;
  padding-right: 8px;
  border: var(--glass-border);
  border-radius: 8px;
  background-color: rgba(15, 23, 42, 0.35);

  // 滚动条样式
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.06);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.14);
    border-radius: 3px;

    &:hover {
      background: rgba(255, 255, 255, 0.22);
    }
  }
}

// 消息项
.message-item {
  padding: 16px;
  border-bottom: 1px solid var(--gray-200);

  &:last-child {
    border-bottom: none;
  }

  &.user-message {
    background-color: rgba(24, 144, 255, 0.12);

    .message-role .role-text {
      color: #1890ff;
    }
  }

  &.assistant-message {
    background-color: rgba(82, 196, 26, 0.12);

    .message-role .role-text {
      color: #52c41a;
    }
  }
}

// 消息头部
.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.message-role {
  display: flex;
  align-items: center;
  gap: 8px;

  .role-text {
    font-weight: 500;
    font-size: 13px;
  }
}

.message-time {
  font-size: 12px;
  color: var(--gray-500);
}

// 消息内容
.message-content {
  .content-text {
    line-height: 1.6;
    color: var(--gray-800);
    margin-bottom: 12px;
    word-break: break-word;

    :deep(code) {
      background-color: rgba(255, 255, 255, 0.1);
      padding: 2px 4px;
      border-radius: 3px;
      font-size: 12px;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    }
  }
}

// 工具调用区域
.tool-calls-section {
  margin-top: 12px;

  :deep(.ant-collapse) {
    background: transparent;
    border: none;
  }

  :deep(.ant-collapse-item) {
    border: var(--glass-border);
    border-radius: 6px;
    margin-bottom: 8px;
  }

  :deep(.ant-collapse-header) {
    background-color: rgba(15, 23, 42, 0.45);
    border-radius: 6px 6px 0 0;
    font-size: 13px;
    font-weight: 500;
  }

  :deep(.ant-collapse-content) {
    border-top: var(--glass-border);
    background-color: rgba(15, 23, 42, 0.35);
  }
}

.tool-call-content {
  .tool-status {
    margin-bottom: 12px;
  }

  .tool-input,
  .tool-output {
    margin-bottom: 12px;

    h5 {
      margin-bottom: 6px;
      color: var(--gray-700);
      font-size: 13px;
      font-weight: 500;
    }
  }

  .code-block {
    background-color: rgba(15, 23, 42, 0.35);
    border: var(--glass-border);
    border-radius: 4px;
    padding: 8px;
    font-size: 12px;
    line-height: 1.4;
    color: var(--gray-800);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
    margin: 0;
  }
}

// 消息类型标签
.message-type {
  margin-top: 8px;
}

// 空状态
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px 0;
}

// 错误状态
.error-state {
  padding: 20px 0;
}

// 模态框样式
:deep(.conversation-detail-modal) {
  .ant-modal-body {
    max-height: 80vh;
    overflow-y: auto;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .messages-container {
    max-height: 400px;
  }

  .message-item {
    padding: 12px;
  }

  .message-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .tool-call-content .code-block {
    max-height: 150px;
    font-size: 11px;
  }
}
</style>
