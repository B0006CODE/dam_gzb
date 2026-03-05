<template>
  <div class="dashboard-container">
    <!-- 顶部状态条 -->

    <!-- 现代化顶部统计栏 -->
    <div class="modern-stats-header">
      <StatusBar />
      <StatsOverviewComponent :basic-stats="basicStats" />
    </div>

    <!-- Grid布局的主要内容区域 -->
    <div class="dashboard-grid">
      <!-- 调用统计模块 - 占据2x1网格 -->
      <CallStatsComponent :loading="loading" ref="callStatsRef" />

      <!-- 用户活跃度分析 - 占据1x1网格 -->
      <div class="grid-item user-stats">
        <UserStatsComponent
          :user-stats="allStatsData?.users"
          :loading="loading"
          ref="userStatsRef"
        />
      </div>

      <!-- 知识库使用情况 - 占据1x1网格 -->
      <div class="grid-item knowledge-stats">
        <KnowledgeStatsComponent
          :knowledge-stats="allStatsData?.knowledge"
          :loading="loading"
          ref="knowledgeStatsRef"
        />
      </div>

      <!-- 对话记录 - 占据1x1网格 -->
      <div class="grid-item conversations">
        <a-card class="conversations-section" title="对话记录" :loading="loading">
          <template #extra>
            <a-space>
              <a-select
                v-model:value="filters.user_id"
                :options="userOptions"
                placeholder="搜索用户名或ID"
                size="small"
                style="width: 150px"
                @change="handleFilterChange"
                allow-clear
                show-search
                :filter-option="filterUserOption"
                :not-found-content="userSearchText ? '无匹配用户' : '请输入搜索'"
              />
              <a-select
                v-model:value="filters.status"
                placeholder="状态"
                size="small"
                style="width: 100px"
                @change="handleFilterChange"
              >
                <a-select-option value="active">活跃</a-select-option>
                <a-select-option value="deleted">已删除</a-select-option>
                <a-select-option value="all">全部</a-select-option>
              </a-select>
              <a-button size="small" @click="loadConversations" :loading="loading">
                刷新
              </a-button>

            </a-space>
          </template>

          <a-table
            :columns="conversationColumns"
            :data-source="conversations"
            :loading="loading"
            :pagination="conversationPagination"
            @change="handleTableChange"
            row-key="thread_id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'title'">
                <a @click="handleViewDetail(record)" class="conversation-title" :class="{ 'loading': loadingDetail }">{{ record.title || '未命名对话' }}</a>
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'active' ? 'green' : 'red'" size="small">
                  {{ record.status === 'active' ? '活跃' : '已删除' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'updated_at'">
                <span class="time-text">{{ formatDate(record.updated_at) }}</span>
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="link" size="small" @click="handleViewDetail(record)" :loading="loadingDetail">
                  详情
                </a-button>
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
    </div>



    <!-- 对话详情模态框 -->
    <ConversationDetailModal ref="conversationDetailModal" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { dashboardApi } from '@/apis/dashboard_api'
import dayjs, { parseToShanghai } from '@/utils/time'

// 导入子组件
import StatusBar from '@/components/StatusBar.vue'
import UserStatsComponent from '@/components/dashboard/UserStatsComponent.vue'
import KnowledgeStatsComponent from '@/components/dashboard/KnowledgeStatsComponent.vue'
import CallStatsComponent from '@/components/dashboard/CallStatsComponent.vue'
import StatsOverviewComponent from '@/components/dashboard/StatsOverviewComponent.vue'

import ConversationDetailModal from '@/components/dashboard/ConversationDetailModal.vue'

// 组件引用

const conversationDetailModal = ref(null)

// 统计数据 - 使用新的响应式结构
const basicStats = ref({})
const allStatsData = ref({
  users: null,
  knowledge: null
})

// 过滤器
const filters = reactive({
  user_id: '',
  agent_id: '',
  status: 'active',
})

// 对话列表
const conversations = ref([])
const loading = ref(false)
const loadingDetail = ref(false)

// 用户列表（用于筛选）
const userList = ref([])
const userSearchText = ref('')

// 用户选项（静态列表，搜索由select组件处理）
const userOptions = computed(() => {
  return userList.value.map(user => ({
    label: user.username,
    value: String(user.id),  // 使用数据库主键作为筛选值（conversations表存储的是这个）
    username: user.username,
    user_id: user.user_id,
    db_id: user.id  // 保存数据库主键用于搜索
  }))
})

// 调用统计子组件引用
const callStatsRef = ref(null)

// 分页
const conversationPagination = reactive({
  current: 1,
  pageSize: 8,
  total: 0,
  showSizeChanger: false,
  showQuickJumper: false,
  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`,
})

// 表格列定义
const conversationColumns = [
  {
    title: '对话标题',
    dataIndex: 'title',
    key: 'title',
    ellipsis: true,
  },
  {
    title: '用户',
    dataIndex: 'username',
    key: 'username',
    width: '120px',
    ellipsis: true,
  },
  {
    title: '消息数',
    dataIndex: 'message_count',
    key: 'message_count',
    width: '60px',
    align: 'center',
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: '70px',
    align: 'center',
  },
  {
    title: '更新时间',
    dataIndex: 'updated_at',
    key: 'updated_at',
    width: '120px',
  },
  {
    title: '操作',
    key: 'actions',
    width: '60px',
    align: 'center',
  },
]

// 子组件引用
const userStatsRef = ref(null)
const knowledgeStatsRef = ref(null)

// 加载统计数据 - 使用并行API调用
const loadAllStats = async () => {
  loading.value = true
  try {
    // 使用并行API调用获取所有统计数据
    const response = await dashboardApi.getAllStats()

    // 更新基础统计数据
    basicStats.value = response.basic

    // 更新详细统计数据
    allStatsData.value = {
      users: response.users,
      knowledge: response.knowledge
    }

    message.success('数据加载成功')
  } catch (error) {
    message.error('加载统计数据失败')

    // 如果并行请求失败，尝试单独加载基础数据
    try {
      const basicResponse = await dashboardApi.getStats()
      basicStats.value = basicResponse
      message.warning('详细数据加载失败，仅显示基础统计')
    } catch (basicError) {
      message.error('无法加载任何统计数据')
    }
  } finally {
    loading.value = false
  }
}

// 保留原有的loadStats函数以兼容旧代码
const loadStats = loadAllStats

// 加载用户列表
const loadUsers = async () => {
  try {
    const response = await dashboardApi.getUsers()
    userList.value = response || []
  } catch (error) {
    console.error('Failed to load users:', error)
    message.error('加载用户列表失败')
  }
}

// 加载对话列表
const loadConversations = async () => {
  try {
    const params = {
      user_id: filters.user_id || undefined,
      agent_id: filters.agent_id || undefined,
      status: filters.status,
      limit: conversationPagination.pageSize,
      offset: (conversationPagination.current - 1) * conversationPagination.pageSize,
    }

    const response = await dashboardApi.getConversations(params)
    conversations.value = response
    // Note: 由于后端没有返回总数，这里暂时设置为当前数据长度
    conversationPagination.total = response.length
  } catch (error) {
    console.error('加载对话列表失败:', error)
    message.error('加载对话列表失败')
  }
}

// 日期格式化
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const parsed = parseToShanghai(dateString)
  if (!parsed) return '-'
  const now = dayjs().tz('Asia/Shanghai')
  const diffDays = now.startOf('day').diff(parsed.startOf('day'), 'day')

  if (diffDays === 0) {
    return parsed.format('HH:mm')
  }
  if (diffDays === 1) {
    return '昨天'
  }
  if (diffDays < 7) {
    return `${diffDays}天前`
  }
  return parsed.format('MM-DD')
}

// 查看对话详情
const handleViewDetail = async (record) => {
  try {
    loadingDetail.value = true
    // 使用模态框显示对话详情
    conversationDetailModal.value.show(record.thread_id)
    // 延迟重置loading状态，给模态框一些加载时间
    setTimeout(() => {
      loadingDetail.value = false
    }, 500)
  } catch (error) {
    console.error('获取对话详情失败:', error)
    message.error('获取对话详情失败')
    loadingDetail.value = false
  }
}

// 自定义用户搜索过滤函数
const filterUserOption = (input, option) => {
  if (!input) return true

  const searchLower = input.toLowerCase()
  const user = option

  // 匹配用户名、user_id或数据库ID
  const usernameMatch = user.username?.toLowerCase().includes(searchLower)
  const userIdMatch = String(user.user_id || '').toLowerCase().includes(searchLower)
  const dbIdMatch = String(user.db_id || '').includes(searchLower)

  return usernameMatch || userIdMatch || dbIdMatch
}

// 处理用户搜索
const handleUserSearch = (searchText) => {
  userSearchText.value = searchText
}

// 处理过滤器变化
const handleFilterChange = () => {
  conversationPagination.current = 1
  loadConversations()
}

// 处理表格变化
const handleTableChange = (pag) => {
  conversationPagination.current = pag.current
  conversationPagination.pageSize = pag.pageSize
  loadConversations()
}


// 清理函数 - 清理所有子组件的图表实例
const cleanupCharts = () => {
  if (userStatsRef.value?.cleanup) userStatsRef.value.cleanup()
  if (knowledgeStatsRef.value?.cleanup) knowledgeStatsRef.value.cleanup()
  if (callStatsRef.value?.cleanup) callStatsRef.value.cleanup()
}

// 初始化
onMounted(() => {
  loadAllStats()
  loadUsers()
  loadConversations()
})

// 组件卸载时清理图表
onUnmounted(() => {
  cleanupCharts()
})
</script>

<style scoped lang="less">

.dashboard-container {
  background: transparent;
  min-height: 100vh;
  overflow-x: hidden;
}

// Dashboard 特有的网格布局
.dashboard-grid {
  display: grid;
  padding: 16px;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 16px;
  margin-bottom: 16px;
  min-height: 0;

  .grid-item {
    border-radius: 16px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 260px;
    background: var(--glass-bg-light);
    backdrop-filter: blur(12px);
    border: var(--border-default);
    transition: all 0.3s ease;

    &:hover {
      border-color: rgba(6, 182, 212, 0.4);
      box-shadow: var(--glow-subtle);
    }

    // 布局：第一行调用统计(2列) + 用户活跃度(1列)，第二行知识库(1列) + 对话记录(1列)
    &.call-stats {
      grid-column: 1 / 2;
      grid-row: 1 / 2;
      min-height: 340px;
    }

    &.user-stats {
      grid-column: 2 / 3;
      grid-row: 1 / 2;
      min-height: 340px;
    }

    &.knowledge-stats {
      grid-column: 1 / 2;
      grid-row: 2 / 3;
      min-height: 300px;
    }

    &.conversations {
      grid-column: 2 / 3;
      grid-row: 2 / 3;
      min-height: 280px;
    }
  }
}

// Dashboard 特有的卡片样式
.conversations-section,
.call-stats-section {
  background: transparent;
  border: none;
  border-radius: 16px;
  transition: all 0.3s ease;
  box-shadow: none;

  :deep(.ant-card-head) {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    min-height: 52px;
    padding: 0 16px;
    background: transparent;

    .ant-card-head-title {
      font-size: 16px;
      font-weight: 600;
      color: #fff;
      text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
    }
  }

  :deep(.ant-card-body) {
    padding: 12px 16px;
    background: transparent;
  }

  :deep(.ant-card-extra) {
    .ant-space {
      gap: 8px;
    }
  }

  // 表格样式覆盖
  :deep(.ant-table) {
    background: transparent;
    color: #fff;
  }

  :deep(.ant-table-thead > tr > th) {
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.7);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    font-weight: 600;
  }

  :deep(.ant-table-tbody > tr > td) {
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.9);
    transition: all 0.3s;
  }

  :deep(.ant-table-tbody > tr:hover > td) {
    background: rgba(6, 182, 212, 0.1) !important;
  }

  :deep(.ant-table-placeholder) {
    background: transparent !important;
    
    .ant-empty-description {
      color: rgba(255, 255, 255, 0.5);
    }
  }

  :deep(.ant-pagination-item),
  :deep(.ant-pagination-prev),
  :deep(.ant-pagination-next) {
    background: transparent;
    border-color: rgba(255, 255, 255, 0.2);
    
    a {
      color: rgba(255, 255, 255, 0.7);
    }

    &:hover {
      border-color: #06b6d4;
      a {
        color: #06b6d4;
      }
    }
  }

  :deep(.ant-pagination-item-active) {
    background: rgba(6, 182, 212, 0.2);
    border-color: #06b6d4;
    
    a {
      color: #06b6d4;
    }
  }
}

// Dashboard 特有的占位符样式
.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: rgba(255, 255, 255, 0.5);

  .placeholder-icon {
    width: 64px;
    height: 64px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;

    .icon {
      width: 32px;
      height: 32px;
      color: #06b6d4;
    }
  }

  .placeholder-text {
    font-size: 18px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 8px;
  }

  .placeholder-subtitle {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.4);
  }
}

// Dashboard 特有的对话记录样式
.conversations-section {
  .conversation-title {
    color: #06b6d4;
    text-decoration: none;
    font-weight: 500;
    font-size: 13px;
    transition: all 0.2s ease;

    &:hover {
      color: #22d3ee;
      text-shadow: 0 0 8px rgba(6, 182, 212, 0.4);
    }
  }

  .time-text {
    color: rgba(255, 255, 255, 0.5);
    font-size: 12px;
  }
}

// 调用统计模块样式
.call-stats-section {
  .call-stats-container {
    .call-summary {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 16px;

      .summary-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        transition: all 0.3s ease;

        &:hover {
          background: rgba(6, 182, 212, 0.05);
          border-color: rgba(6, 182, 212, 0.2);
        }

        .summary-value {
          font-size: 18px;
          font-weight: 700;
          color: #fff;
          margin-bottom: 4px;
          text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
        }

        .summary-label {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.5);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
      }
    }

    .chart-container {
      .chart {
        width: 100%;
        height: 260px;
        border-radius: 12px;
        overflow: hidden;
      }
    }
  }
}

// Dashboard 特有的响应式设计
@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto auto;
    gap: 14px;

    .grid-item {
      &.call-stats,
      &.user-stats,
      &.knowledge-stats,
      &.conversations {
        grid-column: 1 / 2;
        grid-row: auto;
        min-height: 250px;
      }
    }
  }
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 12px;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 8px;

    .grid-item {
      &.call-stats,
      &.user-stats,
      &.knowledge-stats,
      &.conversations {
        grid-column: 1 / 2;
        grid-row: auto;
        min-height: 240px;
      }
    }
  }

  .call-stats-section {
    .call-stats-container {
      .call-summary {
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;

        .summary-card {
          padding: 10px;

          .summary-value {
            font-size: 18px;
          }

          .summary-label {
            font-size: 11px;
          }
        }
      }

      .chart-container {
        .chart {
          height: 200px;
        }
      }
    }
  }
}
</style>
