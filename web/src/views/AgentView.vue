<template>
  <div class="agent-view">
    <div class="agent-view-body">
      <!-- 智能体选择弹窗 -->
      <a-modal
        v-model:open="state.agentModalOpen"
        title="选择智能体"
        :width="800"
        :footer="null"
        :maskClosable="true"
        class="agent-modal"
      >
        <div class="agent-modal-content">
          <div class="agents-grid">
            <div
              v-for="(agent, id) in agents"
              :key="id"
              class="agent-card"
              :class="{ 'selected': id === selectedAgentId }"
              @click="selectAgentFromModal(id)"
            >
              <div class="agent-card-header">
                <div class="agent-card-title">
                  <span class="agent-card-name">{{ agent.name }}</span>
                  <StarFilled v-if="id === defaultAgentId" class="default-icon" />
                  <StarOutlined v-else @click.prevent="setAsDefaultAgent(id)" class="default-icon" />
                </div>
              </div>
              <div class="agent-card-description">{{ agent.description }}</div>
            </div>
          </div>
        </div>
      </a-modal>

      <!-- 中间内容区域 -->
      <div class="content">
        <AgentChatComponent
          ref="chatComponentRef"
          :state="state"
          :single-mode="false"
          @open-agent-modal="openAgentModal"
        >
        </AgentChatComponent>
      </div>

      <!-- 自定义更多菜单 -->
      <Teleport to="body">
        <Transition name="menu-fade">
          <div
            v-if="state.moreMenuOpen"
            ref="moreMenuRef"
            class="more-popup-menu"
            :style="{
              left: state.moreMenuPosition.x + 'px',
              top: state.moreMenuPosition.y + 'px'
            }"
          >
            <div class="menu-item" @click="handleShareChat">
              <ShareAltOutlined class="menu-icon" />
              <span class="menu-text">分享对话</span>
            </div>

            <div class="menu-divider"></div>
            <div class="menu-item" @click="handlePreview">
              <EyeOutlined class="menu-icon" />
              <span class="menu-text">预览页面</span>
            </div>
          </div>
        </Transition>
      </Teleport>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import { StarOutlined, StarFilled, ShareAltOutlined, EyeOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import AgentChatComponent from '@/components/AgentChatComponent.vue';

import { useUserStore } from '@/stores/user';
import { useAgentStore } from '@/stores/agent';
import { ChatExporter } from '@/utils/chatExporter';
import { handleChatError } from '@/utils/errorHandler';
import { onClickOutside } from '@vueuse/core';

import { storeToRefs } from 'pinia';

// 组件引用

const chatComponentRef = ref(null)
const userStore = useUserStore();
const agentStore = useAgentStore();

// 从store中获取响应式状态
const {
  agents,
  selectedAgentId,
  defaultAgentId,
} = storeToRefs(agentStore);
const state = reactive({
  agentModalOpen: false,
  moreMenuOpen: false,
  moreMenuPosition: { x: 0, y: 0 }
});



// 本地状态（仅UI相关）

// 设置为默认智能体
const setAsDefaultAgent = async (agentId) => {
  if (!agentId || !userStore.isAdmin) return;

  try {
    await agentStore.setDefaultAgent(agentId);
    message.success('已将当前智能体设为默认');
  } catch (error) {
    console.error('设置默认智能体错误:', error);
    message.error(error.message || '设置默认智能体时发生错误');
  }
};





// 这些方法现在由agentStore处理，无需在组件中定义

const loadAgentConfig = async () => {
  try {
    await agentStore.loadAgentConfig();
  } catch (error) {
    console.error('加载配置出错:', error);
    message.error('加载配置失败');
  }
};

// 监听智能体选择变化
watch(
  () => selectedAgentId.value,
  () => {
    loadAgentConfig();
  }
);

// 选择智能体（使用store方法）
const selectAgent = (agentId) => {
  agentStore.selectAgent(agentId);
  // 加载该智能体的配置
  loadAgentConfig();
};

// 打开智能体选择弹窗
const openAgentModal = () => {
  state.agentModalOpen = true;
};

// 从弹窗中选择智能体
const selectAgentFromModal = (agentId) => {
  selectAgent(agentId);
  state.agentModalOpen = false;
};


// 更多菜单相关
const moreMenuRef = ref(null);

const toggleMoreMenu = (event) => {
  event.stopPropagation();
  // 切换状态，而不是只打开
  state.moreMenuOpen = !state.moreMenuOpen;

  if (state.moreMenuOpen) {
    // 只在打开时计算位置
    const rect = event.currentTarget.getBoundingClientRect();
    state.moreMenuPosition = {
      x: rect.right - 130, // 菜单宽度180px，右对齐
      y: rect.bottom + 8
    };
  }
};

const closeMoreMenu = () => {
  state.moreMenuOpen = false;
};

// 使用 VueUse 的 onClickOutside
onClickOutside(moreMenuRef, () => {
  if (state.moreMenuOpen) {
    closeMoreMenu();
  }
});

const handleShareChat = async () => {
  closeMoreMenu();

  try {
    // 从聊天组件获取导出数据
    const exportData = chatComponentRef.value?.getExportPayload?.();


    if (!exportData) {
      message.warning('当前没有可导出的对话内容');
      return;
    }

    // 检查是否有实际的消息内容
    const hasMessages = exportData.messages && exportData.messages.length > 0;
    const hasOngoingMessages = exportData.onGoingMessages && exportData.onGoingMessages.length > 0;

    if (!hasMessages && !hasOngoingMessages) {
      console.warn('[AgentView] Export data has no messages:', {
        messages: exportData.messages,
        onGoingMessages: exportData.onGoingMessages
      });
      message.warning('当前对话暂无内容可导出，请先进行对话');
      return;
    }

    const result = await ChatExporter.exportToHTML(exportData);
    message.success(`对话已导出为HTML文件: ${result.filename}`);
  } catch (error) {
    console.error('[AgentView] Export error:', error);
    if (error?.message?.includes('没有可导出的对话内容')) {
      message.warning('当前对话暂无内容可导出，请先进行对话');
      return;
    }
    handleChatError(error, 'export');
  }
};

const handlePreview = () => {
  closeMoreMenu();
  if (selectedAgentId.value) {
    window.open(`/agent/${selectedAgentId.value}`, '_blank');
  }
};
</script>

<style lang="less" scoped>
.agent-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.agent-view-body {
  display: flex;
  flex-direction: row;
  width: 100%;
  flex: 1;
  height: 100%;
  overflow: hidden;
  position: relative;
  background: transparent;

  .content {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: transparent;
  }

  .no-agent-selected {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
  }

  .no-agent-content {
    text-align: center;
    color: rgba(255, 255, 255, 0.5);

    svg {
      margin-bottom: 16px;
      opacity: 0.6;
      color: #06b6d4;
    }

    h3 {
      margin-bottom: 16px;
      color: #fff;
      text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
    }
  }
}

.content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

// 智能体选择弹窗样式
.agent-modal {
  :deep(.ant-modal-content) {
    background: rgba(15, 23, 42, 0.9);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    overflow: hidden;
  }

  :deep(.ant-modal-header) {
    background: transparent;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding: 16px 20px;

    .ant-modal-title {
      font-size: 16px;
      font-weight: 600;
      color: #fff;
    }
  }

  :deep(.ant-modal-body) {
    padding: 20px;
    background: transparent;
  }

  .agent-modal-content {
    .agents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 16px;
      max-height: 500px;
      overflow-y: auto;
      padding-right: 8px;

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

    .agent-card {
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 12px;
      padding: 16px;
      cursor: pointer;
      transition: all 0.3s ease;
      background: rgba(30, 41, 59, 0.4);
      position: relative;
      overflow: hidden;

      &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, transparent 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
      }

      &:hover {
        border-color: rgba(6, 182, 212, 0.5);
        background: rgba(30, 41, 59, 0.6);
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(6, 182, 212, 0.15);

        &::before {
          opacity: 1;
        }

        .agent-card-header .agent-card-title .agent-card-name {
          color: #fff;
          text-shadow: 0 0 8px rgba(6, 182, 212, 0.5);
        }
      }

      .agent-card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
        position: relative;
        z-index: 1;

        .agent-card-title {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;

          .agent-card-name {
            font-size: 16px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.9);
            line-height: 1.4;
            transition: all 0.3s ease;
          }

          .default-icon {
            color: #f59e0b;
            font-size: 16px;
            flex-shrink: 0;
            filter: drop-shadow(0 0 5px rgba(245, 158, 11, 0.5));
          }
        }
      }

      .agent-card-description {
        font-size: 14px;
        color: rgba(255, 255, 255, 0.5);
        line-height: 1.6;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
        position: relative;
        z-index: 1;
        transition: color 0.3s ease;
      }

      &.selected {
        border-color: #06b6d4;
        background: rgba(6, 182, 212, 0.1);
        box-shadow: 0 0 20px rgba(6, 182, 212, 0.2);

        &::after {
          content: '';
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          height: 2px;
          background: #06b6d4;
          box-shadow: 0 0 10px #06b6d4;
        }

        .agent-card-header .agent-card-title .agent-card-name {
          color: #06b6d4;
          text-shadow: 0 0 10px rgba(6, 182, 212, 0.4);
        }

        .agent-card-description {
          color: rgba(255, 255, 255, 0.8);
        }
      }
    }
  }
}

// 自定义更多菜单样式
.more-popup-menu {
  position: fixed;
  min-width: 130px;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(12px);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 6px;
  z-index: 9999;

  .menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 14px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);
    user-select: none;

    .menu-icon {
      font-size: 16px;
      color: rgba(255, 255, 255, 0.5);
    }

    &:hover {
      background: rgba(6, 182, 212, 0.15);
      color: #06b6d4;

      .menu-icon {
        color: #06b6d4;
      }
    }
  }

  .menu-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.05);
    margin: 4px 8px;
  }
}

// 菜单淡入淡出动画
.menu-fade-enter-active {
  animation: menuSlideIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.menu-fade-leave-active {
  animation: menuSlideOut 0.15s cubic-bezier(0.4, 0, 1, 1);
}

@keyframes menuSlideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes menuSlideOut {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-4px);
  }
}
</style>
