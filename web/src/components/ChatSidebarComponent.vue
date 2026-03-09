<template>
  <div class="chat-sidebar" :class="{'sidebar-open': isSidebarOpen, 'no-transition': isInitialRender}">
    <div class="sidebar-content">
      <!-- 头部区域 -->
      <div class="sidebar-header">
        <div class="header-title" v-if="singleMode">
          <div class="logo-area">
            <span class="logo-icon"><i class="header-icon">🤖</i></span> <!-- 可替换为您系统的Logo -->
            <span class="title-text">{{ selectedAgentName }}</span>
          </div>
        </div>
        <div
          v-if="false"
          class="agent-selector"
          @click="openAgentModal"
        >
          <span class="agent-name">{{ selectedAgentName || '选择智能体' }}</span>
          <ChevronDown size="16" class="switch-icon" />
        </div>
        <div class="header-actions">
          <div class="toggle-sidebar nav-btn" v-if="isSidebarOpen" @click="toggleCollapse">
            <PanelLeftClose size="18" color="#666"/>
          </div>
        </div>
      </div>

      <!-- 折叠分组：知识资源 -->
      <div class="collapsible-section">
        <div class="section-header" @click="resourcesCollapsed = !resourcesCollapsed">
          <ChevronRight v-if="resourcesCollapsed" size="14" class="collapse-icon" />
          <ChevronDown v-else size="14" class="collapse-icon" />
          <span class="section-title">知识资源</span>
        </div>
        <div class="section-content" v-show="!resourcesCollapsed">
          <CnkiResourceSelector
            :retrieval-mode="retrievalMode"
            :model-value="modelValue"
            @update:model-value="handleResourceUpdate"
          />
        </div>
      </div>

      <!-- 折叠分组：历史记录 -->
      <div class="collapsible-section history-section">
        <div class="section-header" @click="historyCollapsed = !historyCollapsed">
          <ChevronRight v-if="historyCollapsed" size="14" class="collapse-icon" />
          <ChevronDown v-else size="14" class="collapse-icon" />
          <span class="section-title">历史记录</span>
        </div>
        <div class="section-content history-content" v-show="!historyCollapsed">
          <!-- 新建对话按钮 -->
          <div class="action-bar">
            <button class="new-chat-btn" @click="createNewChat">
              <PlusOutlined class="icon-plus" />
              <span>开启新对话</span>
            </button>
          </div>

          <!-- 对话列表 -->
          <div class="conversation-list scrollbar-custom">
        <template v-if="Object.keys(groupedChats).length > 0">
          <div v-for="(group, groupName) in groupedChats" :key="groupName" class="chat-group">
            <div class="chat-group-title">{{ groupName }}</div>
            <div
              v-for="chat in group"
              :key="chat.id"
              class="conversation-item"
              :class="{
                'active': currentChatId === chat.id
              }"
              @click="handleItemClick(chat)"
            >
              <div class="chat-icon">
                <MessageOutlined />
              </div>
              
              <div class="conversation-title">{{ chat.title || '新的对话' }}</div>

              <!-- 更多操作按钮 (悬浮显示) -->
              <div class="conversation-actions">
                <a-dropdown :trigger="['click']" placement="bottomRight" overlayClassName="deepseek-dropdown">
                  <div class="more-btn" @click.stop>
                    <MoreOutlined />
                  </div>
                  <template #overlay>
                    <a-menu class="deepseek-menu">
                      <a-menu-item key="rename" @click="renameChat(chat.id)">
                        <template #icon><EditOutlined /></template>
                        <span>重命名</span>
                      </a-menu-item>
                      <a-menu-item key="pin" @click="handlePinChat(chat.id)">
                        <template #icon><PushpinOutlined /></template>
                        <span>置顶</span>
                      </a-menu-item>
                      <a-menu-item key="share" @click="handleShareChat(chat.id)">
                         <template #icon><ShareAltOutlined /></template>
                        <span>分享</span>
                      </a-menu-item>
                      <a-menu-divider />
                      <a-menu-item key="delete" @click="deleteChat(chat.id)" class="danger-item">
                        <template #icon><DeleteOutlined /></template>
                        <span>删除</span>
                      </a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="empty-list">
          <div class="empty-icon"><MessageOutlined /></div>
          <div>暂无历史记录</div>
        </div>
          </div>
        </div>
      </div>
      
      <!-- 底部用户区域 (仿 DeepSeek) -->
      <!-- <div class="sidebar-footer">
        <div class="user-profile">
            <div class="avatar-circle">U</div>
            <div class="user-info">
                <div class="user-name">用户设置</div>
            </div>
            <SettingOutlined class="setting-icon" />
        </div>
      </div> -->
    </div>
  </div>
</template>

<script setup>
import { computed, h, ref } from 'vue';
import {
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  CheckSquareOutlined,
  ClearOutlined,
  CalendarOutlined,
  DownOutlined,
  LeftOutlined,
  PlusOutlined,
  MessageOutlined,
  PushpinOutlined,
  ShareAltOutlined,
  SettingOutlined
} from '@ant-design/icons-vue';
import { message, Modal } from 'ant-design-vue';
import { PanelLeftClose, ChevronDown, ChevronRight } from 'lucide-vue-next';
import CnkiResourceSelector from '@/components/CnkiResourceSelector.vue';
import dayjs, { parseToShanghai } from '@/utils/time';

const props = defineProps({
  currentAgentId: { type: String, default: null },
  currentChatId: { type: String, default: null },
  chatsList: { type: Array, default: () => [] },
  isSidebarOpen: { type: Boolean, default: false },
  isInitialRender: { type: Boolean, default: false },
  singleMode: { type: Boolean, default: true },
  agents: { type: Object, default: () => ({}) },
  selectedAgentId: { type: String, default: null },
  retrievalMode: { type: String, default: 'mix' },
  modelValue: { type: Object, default: () => ({ kbIds: [], graph: '' }) }
});

// 折叠分组状态
const resourcesCollapsed = ref(false);
const historyCollapsed = ref(false);

// 资源选择更新
const handleResourceUpdate = (val) => {
  emit('update:modelValue', val);
};

const emit = defineEmits(['create-chat', 'select-chat', 'delete-chat', 'rename-chat', 'toggle-sidebar', 'open-agent-modal', 'update:modelValue']);

const selectedAgentName = computed(() => {
  if (props.selectedAgentId && props.agents && props.agents[props.selectedAgentId]) {
    return props.agents[props.selectedAgentId].name;
  }
  return 'DeepSeek';
});

const groupedChats = computed(() => {
  const groups = {
    '今天': [],
    '七天内': [],
    '三十天内': [],
  };

  const now = dayjs().tz('Asia/Shanghai');
  const today = now.startOf('day');
  const sevenDaysAgo = now.subtract(7, 'day').startOf('day');
  const thirtyDaysAgo = now.subtract(30, 'day').startOf('day');

  const sortedChats = [...props.chatsList].sort((a, b) => {
    const dateA = parseToShanghai(b.created_at);
    const dateB = parseToShanghai(a.created_at);
    if (!dateA || !dateB) return 0;
    return dateA.diff(dateB);
  });

  sortedChats.forEach(chat => {
    const chatDate = parseToShanghai(chat.created_at);
    if (!chatDate) return;
    
    if (chatDate.isAfter(today)) {
      groups['今天'].push(chat);
    } else if (chatDate.isAfter(sevenDaysAgo)) {
      groups['七天内'].push(chat);
    } else if (chatDate.isAfter(thirtyDaysAgo)) {
      groups['三十天内'].push(chat);
    } else {
      const monthKey = chatDate.format('YYYY-MM');
      if (!groups[monthKey]) groups[monthKey] = [];
      groups[monthKey].push(chat);
    }
  });

  for (const key in groups) {
    if (groups[key].length === 0) delete groups[key];
  }
  return groups;
});

const handleItemClick = (chat) => {
  emit('select-chat', chat.id);
};

const createNewChat = () => emit('create-chat');
const deleteChat = (chatId) => emit('delete-chat', chatId);

const renameChat = (chatId) => {
  const chat = props.chatsList.find(c => c.id === chatId);
  if (!chat) return;
  let newTitle = chat.title;
  
  Modal.confirm({
    title: '重命名',
    icon: h(EditOutlined),
    content: h('div', { style: 'margin-top: 10px' }, [
        h('input', {
            value: newTitle,
            class: 'ant-input',
            style: 'width: 100%',
            onInput: (e) => newTitle = e.target.value
        })
    ]),
    onOk: () => {
        if(!newTitle.trim()) return message.warning('请输入标题');
        emit('rename-chat', { chatId, title: newTitle });
    }
  });
};

const handlePinChat = (chatId) => {
    message.info('置顶功能开发中');
    console.log('Pin chat:', chatId);
};

const handleShareChat = (chatId) => {
    message.success('链接已复制到剪贴板');
    console.log('Share chat:', chatId);
};

const toggleCollapse = () => emit('toggle-sidebar');
const openAgentModal = () => emit('open-agent-modal');
</script>

<style lang="less" scoped>
/* 变量定义 - 适配 Tech Theme */
:deep(:root) {
  --ds-bg: var(--bg-elevated);
  --ds-hover: rgba(255, 255, 255, 0.05);
  --ds-active: rgba(255, 255, 255, 0.1);
  --ds-text: var(--text-primary);
  --ds-text-sub: var(--text-secondary);
  --ds-primary: var(--main-color);
}

.chat-sidebar {
  width: 0;
  height: 100%;
  background: var(--glass-bg-medium);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: var(--border-subtle);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  overflow: hidden;

  &.sidebar-open {
    width: 260px;
  }
  
  &.no-transition {
    transition: none !important;
  }

  .sidebar-content {
    width: 260px;
    height: 100%;
    display: flex;
    flex-direction: column;
    background: transparent;
  }
}

/* 头部样式 */
.sidebar-header {
  height: 56px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  border-bottom: var(--border-subtle);

  .header-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    
    .logo-area {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .header-icon {
        font-style: normal;
    }
  }
  
  .agent-selector {
    display: flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    font-weight: 600;
    color: var(--text-secondary);
    font-size: 15px;
    &:hover { color: var(--text-primary); }
  }

  .nav-btn {
    cursor: pointer;
    opacity: 0.6;
    color: var(--text-secondary);
    &:hover { opacity: 1; color: var(--text-primary); }
  }
}

/* 开启新对话按钮 */
.action-bar {
  padding: 12px;
  flex-shrink: 0;
  
  .new-chat-btn {
    width: 100%;
    height: 40px;
    background: rgba(6, 182, 212, 0.1);
    border: 1px solid rgba(6, 182, 212, 0.2);
    border-radius: 10px;
    color: #06b6d4;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding-left: 12px;
    gap: 10px;
    transition: all 0.2s;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);

    .icon-plus { font-size: 16px; color: #06b6d4; }

    &:hover {
      background-color: rgba(6, 182, 212, 0.2);
      border-color: #06b6d4;
      color: #06b6d4;
      box-shadow: var(--glow-default);
    }
  }
}

/* 列表样式 */
.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
  
  .chat-group-title {
    padding: 16px 12px 6px;
    font-size: 12px;
    color: var(--text-tertiary);
    font-weight: 500;
  }

  .conversation-item {
    position: relative;
    height: 38px;
    display: flex;
    align-items: center;
    padding: 0 10px;
    margin-bottom: 2px;
    border-radius: 6px;
    cursor: pointer;
    color: var(--text-secondary);
    transition: background-color 0.15s;

    .chat-icon {
        margin-right: 10px;
        font-size: 14px;
        color: var(--text-tertiary);
        display: flex;
        align-items: center;
    }

    .conversation-title {
      flex: 1;
      font-size: 14px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      padding-right: 24px;
    }

    /* 悬浮显示更多按钮 */
    .conversation-actions {
      position: absolute;
      right: 4px;
      top: 50%;
      transform: translateY(-50%);
      display: none;
      
      .more-btn {
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        color: var(--text-secondary);
        &:hover {
          background-color: rgba(255, 255, 255, 0.1);
          color: var(--text-primary);
        }
      }
    }

    &:hover {
      background-color: rgba(255, 255, 255, 0.05);
      color: var(--text-primary);
      
      .conversation-actions {
        display: block;
      }
    }

    &.active {
      background: rgba(6, 182, 212, 0.15);
      color: #06b6d4;
      font-weight: 600;
      box-shadow: inset 0 0 10px rgba(6, 182, 212, 0.1);
      
      .chat-icon { color: #06b6d4; }
    }
  }
}

/* 底部样式 */
.sidebar-footer {
    padding: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    
    .user-profile {
        display: flex;
        align-items: center;
        gap: 10px;
        cursor: pointer;
        padding: 6px;
        border-radius: 6px;
        &:hover { background: rgba(255, 255, 255, 0.05); }
        
        .avatar-circle {
            width: 28px;
            height: 28px;
            background: rgba(6, 182, 212, 0.2);
            color: var(--main-color);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
        }
        
        .user-info { flex: 1; }
        .user-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }
        .setting-icon { color: var(--text-secondary); }
    }
}

/* 折叠分组样式 */
.collapsible-section {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  
  .section-header {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    cursor: pointer;
    user-select: none;
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 13px;
    background: rgba(0, 0, 0, 0.2);
    transition: all 0.15s;
    
    &:hover {
      background: rgba(0, 0, 0, 0.3);
      color: var(--text-primary);
    }
    
    .collapse-icon {
      margin-right: 8px;
      color: var(--text-tertiary);
    }
    
    .section-title {
      flex: 1;
    }
  }
  
  .section-content {
    padding: 0;
    background: transparent;
    
    :deep(.cnki-resource-selector) {
      padding: 8px 12px;
      
      .cnki-filter-group {
        border: none;
        border-radius: 6px;
        background: transparent;
        margin-bottom: 4px;
        
        .filter-header {
          padding: 8px 12px;
          background: transparent;
          border-bottom: none;
          border-radius: 6px;
          font-size: 13px;
          color: var(--text-secondary);
          
          &:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
          }
        }
        
        .filter-body {
          max-height: 200px;
          padding: 4px 8px;
        }
        
        .filter-item {
          padding: 6px 10px;
          border-radius: 4px;
          font-size: 13px;
          color: var(--text-secondary);
          
          &:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
          }
        }
      }
      
      .selection-summary {
        display: none;
      }
    }
  }
  
  &.history-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border-bottom: none;
    
    .history-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    
    .action-bar {
      padding: 8px 12px;
      flex-shrink: 0;
    }
    
    .conversation-list {
      flex: 1;
      overflow-y: auto;
    }
  }

}

/* 滚动条美化 */
.scrollbar-custom::-webkit-scrollbar { width: 4px; }
.scrollbar-custom::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
.scrollbar-custom:hover::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); }

</style>

<style lang="less">
/* 这里的样式为了能够作用到挂载在 body 上的 dropdown */
.deepseek-dropdown {
    .ant-dropdown-content {
        background: rgba(15, 23, 42, 0.9);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 6px;
        min-width: 140px;
        
        .ant-dropdown-menu {
            box-shadow: none;
            border-radius: 0;
            padding: 0;
            background: transparent;
        }
        
        .ant-dropdown-menu-item {
            border-radius: 6px;
            padding: 8px 12px;
            margin-bottom: 2px;
            font-size: 13px;
            color: var(--text-secondary);
            
            &:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: var(--text-primary);
            }
            
            .anticon {
                margin-right: 8px;
                color: var(--text-tertiary);
            }
        }
        
        .ant-dropdown-menu-item-divider {
            margin: 4px 6px;
            background-color: rgba(255, 255, 255, 0.1);
        }
        
        /* 红色删除项 */
        .danger-item {
            color: #ef4444;
            &:hover {
                background-color: rgba(239, 68, 68, 0.1);
                color: #ef4444;
            }
            .anticon { color: #ef4444; }
        }
    }
}
</style>
