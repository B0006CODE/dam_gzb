<template>
  <a-drawer
    :open="isOpen"
    :width="620"
    title="任务中心"
    placement="right"
    @close="handleClose"
  >
    <div class="task-center">
      <div class="task-toolbar">
        <div class="task-filter-group">
          <a-segmented
            v-model:value="statusFilter"
            :options="taskFilterOptions"
          />
        </div>
        <div class="task-toolbar-actions">
          <a-button
            v-if="selectedTasks.length > 0"
            type="text"
            danger
            @click="handleBatchDelete"
            :loading="batchDeleting"
          >
            删除选中 ({{ selectedTasks.length }})
          </a-button>
          <a-dropdown>
            <template #overlay>
              <a-menu>
                <a-menu-item key="cleanup-success" @click="handleCleanup('success')">
                  清理已完成
                </a-menu-item>
                <a-menu-item key="cleanup-failed" @click="handleCleanup('failed')">
                  清理失败任务
                </a-menu-item>
                <a-menu-item key="cleanup-old" @click="handleCleanupOld">
                  清理旧任务
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item key="cleanup-all" danger @click="handleCleanupAll">
                  清空所有任务
                </a-menu-item>
              </a-menu>
            </template>
            <a-button type="text">
              批量操作
              <DownOutlined />
            </a-button>
          </a-dropdown>
          <a-button
            type="text"
            @click="handleRefresh"
            :loading="loadingState"
          >
            刷新
          </a-button>
        </div>
      </div>

      <a-alert
        v-if="lastErrorState"
        type="error"
        show-icon
        class="task-alert"
        :message="lastErrorState.message || '加载任务信息失败'"
      />

      <div v-if="hasTasks" class="task-list">
        <div
          v-for="task in paginatedTasks"
          :key="task.id"
          class="task-card"
          :class="taskCardClasses(task)"
        >
          <div class="task-card-header">
            <div class="task-card-checkbox">
              <a-checkbox
                :checked="selectedTasks.includes(task.id)"
                @change="(e) => handleTaskSelect(task.id, e.target.checked)"
              />
            </div>
            <div class="task-card-info">
              <div class="task-card-title">{{ task.name }}</div>
              <div class="task-card-subtitle">
                <span class="task-card-id">#{{ formatTaskId(task.id) }}</span>
                <span class="task-card-type">{{ taskTypeLabel(task.type) }}</span>
                <span class="task-card-id" v-if="getTaskDuration(task)">{{ getTaskDuration(task) }}</span>
              </div>
            </div>
            <a-tag :color="statusColor(task.status)" class="task-card-status">
              {{ statusLabel(task.status) }}
            </a-tag>
          </div>

          <div v-if="!isTaskCompleted(task)" class="task-card-progress">
            <a-progress
              :percent="Math.round(task.progress || 0)"
              :status="progressStatus(task.status)"
              stroke-width="6"
              />
            <!-- <span class="task-card-progress-value">{{ Math.round(task.progress || 0) }}%</span> -->
          </div>

          <div v-if="task.message && !isTaskCompleted(task)" class="task-card-message">
            {{ task.message }}
          </div>
          <div v-if="task.error" class="task-card-error">
            {{ task.error }}
          </div>

          <div class="task-card-footer">
            <div class="task-card-timestamps">
              <span v-if="task.started_at">开始: {{ formatTime(task.started_at, 'short') }}</span>
              <span v-if="task.completed_at">完成: {{ formatTime(task.completed_at, 'short') }}</span>
              <span v-if="!task.started_at">创建: {{ formatTime(task.created_at, 'short') }}</span>
            </div>
            <div class="task-card-actions">
              <a-button type="link" size="small" @click="handleDetail(task.id)">
                详情
              </a-button>
              <a-button
                type="link"
                size="small"
                danger
                :disabled="!canCancel(task)"
                @click="handleCancel(task.id)"
              >
                取消
              </a-button>
              <a-popconfirm
                title="确定要删除这个任务吗？"
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleDelete(task.id)"
              >
                <a-button
                  type="link"
                  size="small"
                  danger
                >
                  删除
                </a-button>
              </a-popconfirm>
            </div>
          </div>
        </div>
        <!-- 分页器 -->
        <div class="task-pagination" v-if="filteredTasks.length > pageSize">
          <a-pagination
            v-model:current="currentPage"
            :total="filteredTasks.length"
            :pageSize="pageSize"
            size="small"
            :showSizeChanger="false"
            :showQuickJumper="false"
            :showTotal="(total) => `共 ${total} 个任务`"
          />
        </div>
      </div>

      <div v-else class="task-empty">
        <div class="task-empty-icon">🗂️</div>
        <div class="task-empty-title">暂无任务</div>
        <div class="task-empty-subtitle">当你提交知识库导入或其他后台任务时，会在这里展示实时进度。</div>
      </div>
    </div>
  </a-drawer>
</template>

<script setup>
import { computed, h, onBeforeUnmount, watch, ref } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import { useTaskerStore } from '@/stores/tasker'
import { storeToRefs } from 'pinia'
import { formatFullDateTime, formatRelative, parseToShanghai } from '@/utils/time'

const taskerStore = useTaskerStore()
const { isDrawerOpen, sortedTasks, loading, lastError } = storeToRefs(taskerStore)
const isOpen = isDrawerOpen

const tasks = computed(() => sortedTasks.value)
const loadingState = computed(() => Boolean(loading.value))
const lastErrorState = computed(() => lastError.value)
const statusFilter = ref('all')
const selectedTasks = ref([])
const batchDeleting = ref(false)
const currentPage = ref(1)
const pageSize = 5
const inProgressCount = computed(
  () => tasks.value.filter((task) => ACTIVE_CLASS_STATUSES.has(task.status)).length
)
const completedCount = computed(() => tasks.value.filter((task) => task.status === 'success').length)
const failedCount = computed(
  () => tasks.value.filter((task) => FAILED_STATUSES.has(task.status)).length
)
const totalCount = computed(() => tasks.value.length)
const taskFilterOptions = computed(() => [
  {
    label: () =>
      h('span', { class: 'task-filter-option' }, [
        '全部',
        h('span', { class: 'filter-count' }, totalCount.value)
      ]),
    value: 'all'
  },
  {
    label: () =>
      h('span', { class: 'task-filter-option' }, [
        '进行中',
        h('span', { class: 'filter-count' }, inProgressCount.value)
      ]),
    value: 'active'
  },
  {
    label: () =>
      h('span', { class: 'task-filter-option' }, [
        '已完成',
        h('span', { class: 'filter-count' }, completedCount.value)
      ]),
    value: 'success'
  },
  {
    label: () =>
      h('span', { class: 'task-filter-option' }, [
        '失败',
        h('span', { class: 'filter-count' }, failedCount.value)
      ]),
    value: 'failed'
  }
])

const filteredTasks = computed(() => {
  const list = tasks.value
  switch (statusFilter.value) {
    case 'active':
      return list.filter((task) => ACTIVE_CLASS_STATUSES.has(task.status))
    case 'success':
      return list.filter((task) => task.status === 'success')
    case 'failed':
      return list.filter((task) => FAILED_STATUSES.has(task.status))
    default:
      return list
  }
})

// 分页后的任务列表
const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredTasks.value.slice(start, end)
})

const hasTasks = computed(() => filteredTasks.value.length > 0)

// 当筛选条件变化时，重置到第一页
watch(statusFilter, () => {
  currentPage.value = 1
})

const ACTIVE_CLASS_STATUSES = new Set(['pending', 'queued', 'running'])
const FAILED_STATUSES = new Set(['failed', 'cancelled'])
const TASK_TYPE_LABELS = {
  knowledge_ingest: '知识库导入',
  graph_task: '图谱处理',
  agent_job: '智能体任务'
}

function taskCardClasses(task) {
  return {
    'task-card--active': ACTIVE_CLASS_STATUSES.has(task.status),
    'task-card--success': task.status === 'success',
    'task-card--failed': task.status === 'failed'
  }
}

function taskTypeLabel(type) {
  if (!type) return '后台任务'
  return TASK_TYPE_LABELS[type] || type
}

function formatTaskId(id) {
  if (!id) return '--'
  return id.slice(0, 8)
}

watch(
  isOpen,
  (open) => {
    if (open) {
      taskerStore.loadTasks()
      taskerStore.startPolling()
    } else {
      taskerStore.stopPolling()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  taskerStore.stopPolling()
})

function handleClose() {
  taskerStore.closeDrawer()
}

function handleRefresh() {
  taskerStore.loadTasks()
}

function handleDetail(taskId) {
  const task = tasks.value.find(item => item.id === taskId)
  if (!task) {
    return
  }
  const detail = h('div', { class: 'task-detail' }, [
    h('p', [h('strong', '状态：'), statusLabel(task.status)]),
    h('p', [h('strong', '进度：'), `${Math.round(task.progress || 0)}%`]),
    h('p', [h('strong', '更新时间：'), formatTime(task.updated_at)]),
    h('p', [h('strong', '描述：'), task.message || '-']),
    h('p', [h('strong', '错误：'), task.error || '-'])
  ])
  Modal.info({
    title: task.name,
    width: 520,
    content: detail
  })
}

function handleCancel(taskId) {
  taskerStore.cancelTask(taskId)
}

function handleDelete(taskId) {
  taskerStore.deleteTask(taskId)
}

function handleTaskSelect(taskId, checked) {
  if (checked) {
    if (!selectedTasks.value.includes(taskId)) {
      selectedTasks.value.push(taskId)
    }
  } else {
    const index = selectedTasks.value.indexOf(taskId)
    if (index >= 0) {
      selectedTasks.value.splice(index, 1)
    }
  }
}

function handleBatchDelete() {
  if (selectedTasks.value.length === 0) return

  Modal.confirm({
    title: '批量删除任务',
    content: `确定要删除选中的 ${selectedTasks.value.length} 个任务吗？此操作不可恢复。`,
    okText: '确定删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      batchDeleting.value = true
      try {
        await taskerStore.deleteTasksBatch(selectedTasks.value)
        selectedTasks.value = []
      } catch (error) {
        console.error('批量删除失败:', error)
      } finally {
        batchDeleting.value = false
      }
    }
  })
}

function handleCleanup(status) {
  const statusText = status === 'success' ? '已完成' : '失败'
  Modal.confirm({
    title: '清理任务',
    content: `确定要清理所有${statusText}的任务吗？此操作不可恢复。`,
    okText: '确定',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await taskerStore.cleanupTasks({ status })
      } catch (error) {
        // Error is already handled by the store
      }
    }
  })
}

function handleCleanupOld() {
  Modal.confirm({
    title: '清理旧任务',
    content: '确定要清理超过7天的任务吗？此操作不可恢复。',
    okText: '确定',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        const sevenDaysAgo = new Date()
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
        const cleanupTime = sevenDaysAgo.toISOString()
        await taskerStore.cleanupTasks({ older_than: cleanupTime })
      } catch (error) {
        // Error is already handled by the store
      }
    }
  })
}

function handleCleanupAll() {
  Modal.confirm({
    title: '清空所有任务',
    content: '确定要清空所有任务吗？此操作不可恢复，请谨慎操作！',
    okText: '确定清空',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await taskerStore.cleanupTasks()
      } catch (error) {
        // Error is already handled by the store
      }
    }
  })
}

function formatTime(value, mode = 'full') {
  if (!value) return '-'
  if (mode === 'short') {
    return formatRelative(value)
  }
  return formatFullDateTime(value)
}

function getTaskDuration(task) {
  if (!task.started_at || !task.completed_at) return null
  try {
    const start = parseToShanghai(task.started_at)
    const end = parseToShanghai(task.completed_at)
    if (!start || !end) {
      return null
    }

    const diffSeconds = Math.max(0, Math.floor(end.diff(start, 'second')))
    const hours = Math.floor(diffSeconds / 3600)
    const minutes = Math.floor((diffSeconds % 3600) / 60)
    const seconds = diffSeconds % 60

    if (hours > 0) {
      return `${hours}小时${minutes}分钟`
    }
    if (minutes > 0) {
      return `${minutes}分钟${seconds}秒`
    }
    if (seconds > 0) {
      return `${seconds}秒`
    }
    return '小于1秒'
  } catch {
    return null
  }
}

function isTaskCompleted(task) {
  return ['success', 'failed', 'cancelled'].includes(task.status)
}

function getCompletionIcon(status) {
  const icons = {
    success: '✓',
    failed: '✗',
    cancelled: '○'
  }
  return icons[status] || '?'
}

function statusLabel(status) {
  const map = {
    pending: '等待中',
    queued: '已排队',
    running: '进行中',
    success: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return map[status] || status
}

function statusColor(status) {
  const map = {
    pending: 'blue',
    queued: 'blue',
    running: 'processing',
    success: 'green',
    failed: 'red',
    cancelled: 'gray'
  }
  return map[status] || 'default'
}

function progressStatus(status) {
  if (status === 'failed') return 'exception'
  if (status === 'cancelled') return 'normal'
  return 'active'
}

function canCancel(task) {
  return ['pending', 'running', 'queued'].includes(task.status) && !task.cancel_requested
}

</script>
<style scoped lang="less">
.task-center {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.task-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
  flex-wrap: wrap;
}

.task-filter-group {
  flex-shrink: 0;
}

.task-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

:deep(.filter-count) {
  margin-left: 2px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.task-toolbar-actions :deep(.ant-btn) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 10px;
  color: rgba(255, 255, 255, 0.8);
  
  &:hover {
    color: #06b6d4;
    background: rgba(6, 182, 212, 0.1);
  }
  
  &.ant-btn-dangerous {
    color: #ef4444;
    &:hover {
      background: rgba(239, 68, 68, 0.1);
    }
  }
}

.task-alert {
  margin-bottom: 4px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  
  :deep(.ant-alert-message) {
    color: #fca5a5;
  }
  :deep(.anticon) {
    color: #ef4444;
  }
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  padding-right: 4px;
  padding-bottom: 20px;
  
  // Custom scrollbar
  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.02);
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
    &:hover {
      background: rgba(255, 255, 255, 0.2);
    }
  }
}

.task-card {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: transparent;
    transition: all 0.3s ease;
  }
}

.task-card:hover {
  border-color: rgba(6, 182, 212, 0.3);
  background: rgba(30, 41, 59, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.task-card--active {
  background: linear-gradient(to right, rgba(6, 182, 212, 0.05), rgba(30, 41, 59, 0.4));
  &::before {
    background: #06b6d4;
    box-shadow: 0 0 8px #06b6d4;
  }
}

.task-card--success {
  background: linear-gradient(to right, rgba(16, 185, 129, 0.05), rgba(30, 41, 59, 0.4));
  &::before {
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }
}

.task-card--failed {
  background: linear-gradient(to right, rgba(239, 68, 68, 0.05), rgba(30, 41, 59, 0.4));
  &::before {
    background: #ef4444;
    box-shadow: 0 0 8px #ef4444;
  }
}

.task-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.task-card-checkbox {
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
  
  :deep(.ant-checkbox-inner) {
    background-color: transparent;
    border-color: rgba(255, 255, 255, 0.3);
  }
  
  :deep(.ant-checkbox-checked .ant-checkbox-inner) {
    background-color: #06b6d4;
    border-color: #06b6d4;
  }
}

.task-card-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.task-card-title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
  max-width: 100%;
  display: block;
}

.task-card-subtitle {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  align-items: center;
}

.task-card-id {
  letter-spacing: 0.02em;
  font-family: monospace;
  color: rgba(255, 255, 255, 0.4);
}

.task-card-type {
  padding: 0 6px;
  border-radius: 4px;
  background-color: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  line-height: 18px;
  font-size: 11px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.task-card-status {
  margin-top: 0;
}

.task-card-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: -4px;
}

.task-card-progress :deep(.ant-progress) {
  flex: 1;
  margin-bottom: 0;
  .ant-progress-text {
    color: rgba(255, 255, 255, 0.7);
    font-size: 12px;
  }
  .ant-progress-inner {
    background-color: rgba(255, 255, 255, 0.1);
  }
}

.task-card-progress-value {
  font-size: 12px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  width: 48px;
  text-align: right;
}

.task-card-message,
.task-card-error {
  font-size: 12px;
  line-height: 1.4;
  border-radius: 6px;
  padding: 8px 10px;
}

.task-card-message {
  background: rgba(15, 23, 42, 0.3);
  color: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.task-card-error {
  background: rgba(239, 68, 68, 0.1);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.task-card-footer {
  margin-top: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.task-card-timestamps {
  display: flex;
  flex-direction: row;
  gap: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.task-card-actions {
  display: flex;
  gap: 4px;
  
  :deep(.ant-btn-link) {
    color: rgba(255, 255, 255, 0.6);
    &:hover {
      color: #06b6d4;
    }
    
    &.ant-btn-dangerous {
      color: rgba(239, 68, 68, 0.7);
      &:hover {
        color: #ef4444;
      }
    }
  }
}

.task-card-completion {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.completion-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
}

.completion-badge--success {
  color: #10b981;
}

.completion-badge--success .completion-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.2);
  font-size: 14px;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.3);
}

.completion-badge--failed {
  color: #ef4444;
}

.completion-badge--failed .completion-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.2);
  font-size: 14px;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
}

.completion-badge--cancelled {
  color: #94a3b8;
}

.completion-badge--cancelled .completion-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.2);
  font-size: 14px;
}

.task-duration {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.duration-label {
  font-weight: 500;
}

.duration-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}

.task-empty {
  margin-top: 32px;
  padding: 40px 30px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.2);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.task-empty-icon {
  font-size: 28px;
  opacity: 0.7;
  filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.2));
}

.task-empty-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}

.task-empty-subtitle {
  font-size: 13px;
  max-width: 320px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.4);
}

.task-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 12px 4px;
  margin-top: 4px;
  
  :deep(.ant-pagination) {
    color: rgba(255, 255, 255, 0.6);
    
    .ant-pagination-prev,
    .ant-pagination-next,
    .ant-pagination-item {
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.1);
      
      a {
        color: rgba(255, 255, 255, 0.6);
      }
      
      &:hover {
        border-color: #06b6d4;
        a {
          color: #06b6d4;
        }
      }
    }
    
    .ant-pagination-item-active {
      background: rgba(6, 182, 212, 0.1);
      border-color: #06b6d4;
      
      a {
        color: #06b6d4;
      }
    }
    
    .ant-pagination-disabled {
      .ant-pagination-item-link {
        color: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.05);
      }
    }
    
    .ant-pagination-total-text {
      color: rgba(255, 255, 255, 0.5);
      margin-right: 12px;
    }
  }
}
</style>
