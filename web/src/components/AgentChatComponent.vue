<template>
  <div class="chat-container" ref="chatContainerRef">
    <ChatSidebarComponent
      :current-chat-id="currentChatId"
      :chats-list="chatsList"
      :is-sidebar-open="uiState.isSidebarOpen"
      :is-initial-render="uiState.isInitialRender"
      :single-mode="props.singleMode"
      :agents="agents"
      :selected-agent-id="currentAgentId"
      :retrieval-mode="retrievalMode"
      v-model="resourceSelection"
      @create-chat="createNewChat"
      @select-chat="selectChat"
      @delete-chat="deleteChat"
      @rename-chat="renameChat"
      @toggle-sidebar="toggleSidebar"
      @open-agent-modal="openAgentModal"
      :class="{
        'floating-sidebar': isSmallContainer,
        'sidebar-open': uiState.isSidebarOpen,
        'no-transition': uiState.isInitialRender,
        'collapsed': isSmallContainer && !uiState.isSidebarOpen
      }"
    />
    <div class="sidebar-backdrop" v-if="uiState.isSidebarOpen && isSmallContainer" @click="toggleSidebar"></div>
    <div class="chat">
      <div class="chat-header">
        <div class="header__left">
          <slot name="header-left" class="nav-btn"></slot>
          <div type="button" class="agent-nav-btn" v-if="!uiState.isSidebarOpen" @click="toggleSidebar">
            <PanelLeftOpen  class="nav-btn-icon" size="18"/>
          </div>
          <div type="button" class="agent-nav-btn" v-if="!uiState.isSidebarOpen" @click="createNewChat" :disabled="isProcessing">
            <MessageCirclePlus  class="nav-btn-icon"  size="18"/>
            <span class="text" :class="{'hide-text': isMediumContainer}">新对话</span>
          </div>
        </div>
        <div class="header__right">
          <!-- <div class="nav-btn" @click="shareChat" v-if="currentChatId && currentAgent">
            <ShareAltOutlined style="font-size: 18px;"/>
          </div> -->
          <!-- <div class="nav-btn test-history" @click="getAgentHistory" v-if="currentChatId && currentAgent">
            <ThunderboltOutlined />
          </div> -->
          <slot name="header-right"></slot>
        </div>
      </div>

      <div v-if="isLoadingThreads || isLoadingMessages" class="chat-loading">
        <LoadingOutlined />
        <span>正在加载历史记录...</span>
      </div>

      <div v-else-if="!conversations.length" class="chat-examples">
        <img v-if="currentAgentMetadata?.icon" class="agent-icons" :src="currentAgentMetadata?.icon" alt="智能体图标" />
        <div v-else style="margin-bottom: 150px"></div>
        <h1>您好，我是{{ currentAgentName }}！有什么可以帮您？</h1>
        <!-- <h1>{{ currentAgent ? currentAgent.name : '请选择一个智能体开始对话' }}</h1>
        <p>{{ currentAgent ? currentAgent.description : '不同的智能体有不同的专长和能力' }}</p> -->

        <div class="inputer-init">
          <!-- 检索模式选择器 - 独立显示 -->
          <!-- <div class="retrieval-mode-wrapper" v-if="currentAgent">
            <div class="retrieval-mode-selector-standalone">
              <div class="retrieval-mode-buttons">
                <button
                  :class="['retrieval-mode-btn', { 'active': retrievalMode === 'mix' }]"
                  @click="retrievalMode = 'mix'"
                >
                  <div class="retrieval-mode-icon">
                    <MergeCellsOutlined />
                  </div>
                  <span class="retrieval-mode-text">混合检索</span>
                </button>
                <button
                  :class="['retrieval-mode-btn', { 'active': retrievalMode === 'local' }]"
                  @click="retrievalMode = 'local'"
                >
                  <div class="retrieval-mode-icon">
                    <DatabaseOutlined />
                  </div>
                  <span class="retrieval-mode-text">知识库检索</span>
                </button>
                <button
                  :class="['retrieval-mode-btn', { 'active': retrievalMode === 'global' }]"
                  @click="retrievalMode = 'global'"
                >
                  <div class="retrieval-mode-icon">
                    <GlobalOutlined />
                  </div>
                  <span class="retrieval-mode-text">知识图谱检索</span>
                </button>
                <button
                  :class="['retrieval-mode-btn', { 'active': retrievalMode === 'llm' }]"
                  @click="retrievalMode = 'llm'"
                >
                  <div class="retrieval-mode-icon">
                    <RobotOutlined />
                  </div>
                  <span class="retrieval-mode-text">大模型检索</span>
                </button>
              </div>
            </div>
          </div> -->

          <!-- 输入框 -->
          <MessageInputComponent
            v-model="userInput"
            v-model:retrieval-mode="retrievalMode"
            :is-loading="isProcessing"
            :disabled="!currentAgent"
            :send-button-disabled="(!userInput || !currentAgent) && !isProcessing"
            :show-retrieval-modes="true"
            placeholder="输入问题..."
            @send="handleSendOrStop"
            @keydown="handleKeyDown"
          />

          <!-- 示例问题 -->
          <div class="example-questions" v-if="exampleQuestions.length > 0">
            <div class="example-title">或试试这些问题：</div>
            <div class="example-chips">
              <div
                v-for="question in exampleQuestions"
                :key="question.id"
                class="example-chip"
                @click="handleExampleClick(question.text)"
              >
                {{ question.text }}
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="chat-box" ref="messagesContainer">
        <div class="conv-box" v-for="(conv, index) in conversations" :key="index">
          <AgentMessageComponent
            v-for="(message, msgIndex) in conv.messages"
            :message="message"
            :key="msgIndex"
            :is-processing="isProcessing && conv.status === 'streaming' && msgIndex === conv.messages.length - 1"
            :show-refs="showMsgRefs(message)"
            @retry="retryMessage(message)"
          >
          </AgentMessageComponent>

        </div>

        <!-- 生成中的加载状态 -->
        <div class="generating-status" v-if="isProcessing && conversations.length > 0">
          <div class="generating-indicator">
            <div class="loading-dots">
              <div></div>
              <div></div>
              <div></div>
            </div>
            <span class="generating-text">正在生成回复...</span>
          </div>
        </div>
      </div>
      <div class="bottom">
        <div class="message-input-wrapper" v-if="conversations.length > 0">
          <MessageInputComponent
            v-model="userInput"
            v-model:retrieval-mode="retrievalMode"
            :is-loading="isProcessing"
            :disabled="!currentAgent"
            :send-button-disabled="(!userInput || !currentAgent) && !isProcessing"
            :show-retrieval-modes="true"
            placeholder="输入问题..."
            @send="handleSendOrStop"
            @keydown="handleKeyDown"
          />
          <div class="bottom-actions">
            <!-- <p class="note">请注意辨别内容的可靠性</p> -->
          </div>
        </div>
      </div>

    </div>

  </div>

</template>


<script setup>
import { ref, reactive, onMounted, watch, nextTick, computed, onUnmounted, onActivated } from 'vue';
import { LoadingOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import MessageInputComponent from '@/components/MessageInputComponent.vue'
import AgentMessageComponent from '@/components/AgentMessageComponent.vue'
import ChatSidebarComponent from '@/components/ChatSidebarComponent.vue'

import { PanelLeftOpen, MessageCirclePlus } from 'lucide-vue-next';
import CnkiResourceSelector from '@/components/CnkiResourceSelector.vue';
import { MergeCellsOutlined, DatabaseOutlined, GlobalOutlined, RobotOutlined } from '@ant-design/icons-vue';
import { handleChatError, handleValidationError } from '@/utils/errorHandler';
import { ScrollController } from '@/utils/scrollController';
import { AgentValidator } from '@/utils/agentValidator';
import { useAgentStore } from '@/stores/agent';
import { storeToRefs } from 'pinia';
import { MessageProcessor } from '@/utils/messageProcessor';
import { agentApi, threadApi } from '@/apis';

// ==================== PROPS & EMITS ====================
const props = defineProps({
  state: { type: Object, default: () => ({}) },
  agentId: { type: String, default: '' },
  singleMode: { type: Boolean, default: true }
});
const emit = defineEmits(['open-config', 'open-agent-modal']);

// ==================== STORE MANAGEMENT ====================
const agentStore = useAgentStore();
const {
  agents,
  selectedAgentId,
} = storeToRefs(agentStore);
const defaultAgent = computed(() => agentStore.defaultAgent);

// ==================== LOCAL CHAT & UI STATE ====================
const userInput = ref('');
const retrievalMode = ref('mix');
const selectedKbIds = ref([]);
const selectedGraph = ref('');

// resourceSelection 与 selectedKbIds/selectedGraph 双向同步
const resourceSelection = computed({
  get: () => ({ kbIds: selectedKbIds.value, graph: selectedGraph.value }),
  set: (val) => {
    if (val.kbIds !== undefined) selectedKbIds.value = val.kbIds;
    if (val.graph !== undefined) selectedGraph.value = val.graph;
  }
});

// 从智能体元数据获取示例问题
const exampleQuestions = computed(() => {
  const examples = currentAgentMetadata.value?.examples || [];
  return examples.map((text, index) => ({
    id: index + 1,
    text: text
  }));
});


const chatState = reactive({
  currentThreadId: null,
  isLoadingThreads: false,
  isLoadingMessages: false,
  creatingNewChat: false,
  // 以threadId为键的线程状态
  threadStates: {}
});

// 组件级别的线程和消息状态
const threads = ref([]);
const threadMessages = ref({});

const uiState = reactive({
  ...props.state,
  isSidebarOpen: localStorage.getItem('chat_sidebar_open') !== 'false',
  isInitialRender: true,
  containerWidth: 0,
});

// ==================== COMPUTED PROPERTIES ====================
const firstAgentId = computed(() => Object.keys(agents.value || {})[0] || '');

const currentAgentId = computed(() => {
  if (props.singleMode) {
    return props.agentId || defaultAgent.value?.id || firstAgentId.value;
  }

  if (selectedAgentId.value && agents.value[selectedAgentId.value]) {
    return selectedAgentId.value;
  }

  return defaultAgent.value?.id || firstAgentId.value;
});

const currentAgentMetadata = computed(() => {
  const agentId = currentAgentId.value;
  const metadata = agentStore?.metadata || {};
  return agentId && metadata[agentId] ? metadata[agentId] : {};
});
const currentAgentName = computed(() => currentAgentMetadata.value?.name || currentAgent.value?.name || '智能体');

const currentAgent = computed(() => agents.value[currentAgentId.value] || null);
const chatsList = computed(() => threads.value || []);
const currentChatId = computed(() => chatState.currentThreadId);
const currentThread = computed(() => {
  if (!currentChatId.value) return null;
  return threads.value.find(thread => thread.id === currentChatId.value) || null;
});

const currentThreadMessages = computed(() => threadMessages.value[currentChatId.value] || []);

// 当前线程状态的computed属性
const currentThreadState = computed(() => {
  return getThreadState(currentChatId.value);
});

const onGoingConvMessages = computed(() => {
  const threadState = currentThreadState.value;
  if (!threadState || !threadState.onGoingConv) return [];

  const msgs = Object.values(threadState.onGoingConv.msgChunks).map(MessageProcessor.mergeMessageChunk);
  return msgs.length > 0
    ? MessageProcessor.convertToolResultToMessages(msgs).filter(msg => msg.type !== 'tool')
    : [];
});

const conversations = computed(() => {
  const historyConvs = MessageProcessor.convertServerHistoryToMessages(currentThreadMessages.value);
  const threadState = currentThreadState.value;

  let combinedConvs = historyConvs;

  // 如果有进行中的消息且线程状态显示正在流式处理，添加进行中的对话
  if (onGoingConvMessages.value.length > 0 && threadState?.isStreaming) {
    const onGoingConv = {
      messages: onGoingConvMessages.value,
      status: 'streaming'
    };
    combinedConvs = [...historyConvs, onGoingConv];
  } else if (historyConvs.length === 0 && onGoingConvMessages.value.length > 0 && !threadState?.isStreaming) {
    // 即使流式结束，如果历史记录为空但还有消息没有完全同步，也保持显示
    const finalConv = {
      messages: onGoingConvMessages.value,
      status: 'finished'
    };
    combinedConvs = [finalConv];
  }

  const withGraphData = attachKnowledgeGraphData(combinedConvs);
  return MessageProcessor.attachCitationsToConversations(withGraphData);
});

const isLoadingThreads = computed(() => chatState.isLoadingThreads);
const isLoadingMessages = computed(() => chatState.isLoadingMessages);
const isStreaming = computed(() => {
  const threadState = currentThreadState.value;
  return threadState ? threadState.isStreaming : false;
});
const isProcessing = computed(() => isStreaming.value || chatState.creatingNewChat);
const isSmallContainer = computed(() => uiState.containerWidth <= 520);
const isMediumContainer = computed(() => uiState.containerWidth <= 768);
const retrievalModeLabels = {
  mix: '混合检索',
  local: '知识库检索',
  global: '知识图谱检索',
  llm: '大模型检索'
};
const retrievalModeHintsMap = {
  mix: '同时利用知识库与知识图谱进行智能混合检索',
  local: '只使用知识库进行向量检索',
  global: '只使用知识图谱进行检索',
  llm: '调用大模型自身知识，不访问知识库或图谱'
};
const retrievalModeLabel = computed(() => retrievalModeLabels[retrievalMode.value] || '检索模式');
const retrievalModeHint = computed(() => retrievalModeHintsMap[retrievalMode.value] || '选择合适的检索模式');

// ==================== SCROLL & RESIZE HANDLING ====================
const chatContainerRef = ref(null);
const scrollController = new ScrollController('.chat');
let resizeObserver = null;

onMounted(() => {
  nextTick(() => {
    if (chatContainerRef.value) {
      uiState.containerWidth = chatContainerRef.value.offsetWidth;
      resizeObserver = new ResizeObserver(entries => {
        for (let entry of entries) {
          uiState.containerWidth = entry.contentRect.width;
        }
      });
      resizeObserver.observe(chatContainerRef.value);
    }
    const chatContainer = document.querySelector('.chat');
    if (chatContainer) {
      chatContainer.addEventListener('scroll', scrollController.handleScroll, { passive: true });
    }
  });
  setTimeout(() => { uiState.isInitialRender = false; }, 300);
});

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect();
  scrollController.cleanup();
  // 清理所有线程状态
  resetOnGoingConv();
});

// ==================== THREAD STATE MANAGEMENT ====================
// 获取指定线程的状态，如果不存在则创建
const getThreadState = (threadId) => {
  if (!threadId) return null;
  if (!chatState.threadStates[threadId]) {
    chatState.threadStates[threadId] = {
      isStreaming: false,
      streamAbortController: null,
      onGoingConv: { msgChunks: {} }
    };
  }
  return chatState.threadStates[threadId];
};

// 清理指定线程的状态
const cleanupThreadState = (threadId) => {
  if (!threadId) return;
  const threadState = chatState.threadStates[threadId];
  if (threadState) {
    if (threadState.streamAbortController) {
      threadState.streamAbortController.abort();
    }
    delete chatState.threadStates[threadId];
  }
};

// ==================== STREAM HANDLING LOGIC ====================
const resetOnGoingConv = (threadId = null, preserveMessages = false) => {
  if (threadId) {
    // 清理指定线程的状态
    const threadState = getThreadState(threadId);
    if (threadState) {
      if (threadState.streamAbortController) {
        threadState.streamAbortController.abort();
        threadState.streamAbortController = null;
      }
      // 如果指定要保留消息，则延迟清空
      if (preserveMessages) {
        // 延迟清空消息，给历史记录加载足够时间
        setTimeout(() => {
          if (threadState.onGoingConv) {
            threadState.onGoingConv = { msgChunks: {} };
          }
        }, 100);
      } else {
        threadState.onGoingConv = { msgChunks: {} };
      }
    }
  } else {
    // 清理当前线程或所有线程的状态
    const targetThreadId = currentChatId.value;
    if (targetThreadId) {
      const threadState = getThreadState(targetThreadId);
      if (threadState) {
        if (threadState.streamAbortController) {
          threadState.streamAbortController.abort();
          threadState.streamAbortController = null;
        }
        if (preserveMessages) {
          setTimeout(() => {
            if (threadState.onGoingConv) {
              threadState.onGoingConv = { msgChunks: {} };
            }
          }, 100);
        } else {
          threadState.onGoingConv = { msgChunks: {} };
        }
      }
    } else {
      // 如果没有当前线程，清理所有线程状态
      Object.keys(chatState.threadStates).forEach(tid => {
        cleanupThreadState(tid);
      });
    }
  }
};

const _processStreamChunk = (chunk, threadId) => {
  const { status, msg, request_id, message } = chunk;
  const threadState = getThreadState(threadId);

  if (!threadState) return false;

  switch (status) {
    case 'init':
      threadState.onGoingConv.msgChunks[request_id] = [msg];
      return false;
    case 'loading':
      if (msg.id) {
        if (!threadState.onGoingConv.msgChunks[msg.id]) {
          threadState.onGoingConv.msgChunks[msg.id] = [];
        }
        threadState.onGoingConv.msgChunks[msg.id].push(msg);
      }
      return false;
    case 'error':
      handleChatError({ message }, 'stream');
      // Stop the loading indicator
      if (threadState) {
        threadState.isStreaming = false;

        // Abort the stream controller to stop processing further events
        if (threadState.streamAbortController) {
          threadState.streamAbortController.abort();
          threadState.streamAbortController = null;
        }
      }

      // Reload messages to show any partial content saved by the backend
      fetchThreadMessages({ agentId: currentAgentId.value, threadId: threadId });
      resetOnGoingConv(threadId);
      return true;
    case 'finished':
      // 先标记流式结束，但保持消息显示直到历史记录加载完成
      if (threadState) {
        threadState.isStreaming = false;
      }
      // 异步加载历史记录，保持当前消息显示直到历史记录加载完成
      fetchThreadMessages({ agentId: currentAgentId.value, threadId: threadId })
        .finally(() => {
          // 历史记录加载完成后，安全地清空当前进行中的对话
          resetOnGoingConv(threadId, true);
        });
      return true;
    case 'interrupted':
      // 中断状态，刷新消息历史
      if (threadState) {
        threadState.isStreaming = false;
      }
      fetchThreadMessages({ agentId: currentAgentId.value, threadId: threadId })
        .finally(() => {
          resetOnGoingConv(threadId, true);
        });
      return true;
  }

  return false;
};

// ==================== 线程管理方法 ====================
// 获取当前智能体的线程列表
const fetchThreads = async (agentId = null) => {
  const targetAgentId = agentId || currentAgentId.value;
  if (!targetAgentId) return;

  chatState.isLoadingThreads = true;
  try {
    const fetchedThreads = await threadApi.getThreads(targetAgentId);
    threads.value = fetchedThreads || [];
  } catch (error) {
    console.error('Failed to fetch threads:', error);
    handleChatError(error, 'fetch');
    throw error;
  } finally {
    chatState.isLoadingThreads = false;
  }
};

// 创建新线程
const createThread = async (agentId, title = '新的对话') => {
  if (!agentId) return null;

  chatState.isCreatingThread = true;
  try {
    const thread = await threadApi.createThread(agentId, title);
    if (thread) {
      threads.value.unshift(thread);
      threadMessages.value[thread.id] = [];
    }
    return thread;
  } catch (error) {
    console.error('Failed to create thread:', error);
    handleChatError(error, 'create');
    throw error;
  } finally {
    chatState.isCreatingThread = false;
  }
};

// 删除线程
const deleteThread = async (threadId) => {
  if (!threadId) return;

  chatState.isDeletingThread = true;
  try {
    await threadApi.deleteThread(threadId);
    threads.value = threads.value.filter(thread => thread.id !== threadId);
    delete threadMessages.value[threadId];

    if (chatState.currentThreadId === threadId) {
      chatState.currentThreadId = null;
    }
  } catch (error) {
    console.error('Failed to delete thread:', error);
    handleChatError(error, 'delete');
    throw error;
  } finally {
    chatState.isDeletingThread = false;
  }
};

// 更新线程标题
const updateThread = async (threadId, title) => {
  if (!threadId || !title) return;

  chatState.isRenamingThread = true;
  try {
    await threadApi.updateThread(threadId, title);
    const thread = threads.value.find(t => t.id === threadId);
    if (thread) {
      thread.title = title;
    }
  } catch (error) {
    console.error('Failed to update thread:', error);
    handleChatError(error, 'update');
    throw error;
  } finally {
    chatState.isRenamingThread = false;
  }
};

// 获取线程消息
const fetchThreadMessages = async ({ agentId, threadId }) => {
  if (!threadId || !agentId) return;

  try {
    const response = await agentApi.getAgentHistory(agentId, threadId);
    threadMessages.value[threadId] = response.history || [];
  } catch (error) {
    handleChatError(error, 'load');
    throw error;
  }
};

// 发送消息并处理流式响应
const sendMessage = async ({ agentId, threadId, text, signal = undefined }) => {
  if (!agentId || !threadId || !text) {
    const error = new Error("Missing agent, thread, or message text");
    handleChatError(error, 'send');
    return Promise.reject(error);
  }

  // 如果是新对话，用消息内容作为标题
  if ((threadMessages.value[threadId] || []).length === 0) {
    updateThread(threadId, text);
  }

  const requestData = {
    query: text,
    config: {
      thread_id: threadId,
      retrieval_mode: retrievalMode.value,
    },
  };

  const kbIds = selectedKbIds.value.filter(Boolean);
  if (kbIds.length > 0 && ['mix', 'local'].includes(retrievalMode.value)) {
    requestData.config.kb_whitelist = kbIds;
  }
  if (selectedGraph.value && ['mix', 'global'].includes(retrievalMode.value)) {
    requestData.config.graph_name = selectedGraph.value;
  }

  try {
    return await agentApi.sendAgentMessage(agentId, requestData, signal ? { signal } : undefined);
  } catch (error) {
    handleChatError(error, 'send');
    throw error;
  }
};


// ==================== CHAT ACTIONS ====================
// 检查第一个对话是否为空
const isFirstChatEmpty = () => {
  if (threads.value.length === 0) return false;
  const firstThread = threads.value[0];
  const firstThreadMessages = threadMessages.value[firstThread.id] || [];
  return firstThreadMessages.length === 0;
};

// 如果第一个对话为空，直接切换到第一个对话
const switchToFirstChatIfEmpty = async () => {
  if (threads.value.length > 0 && isFirstChatEmpty()) {
    await selectChat(threads.value[0].id);
    return true;
  }
  return false;
};

const createNewChat = async () => {
  if (!AgentValidator.validateAgentId(currentAgentId.value, '创建对话') || isProcessing.value) return;

  // 如果第一个对话为空，直接切换到第一个对话而不是创建新对话
  if (await switchToFirstChatIfEmpty()) return;

  // 只有当当前对话是第一个对话且为空时，才阻止创建新对话
  const currentThreadIndex = threads.value.findIndex(thread => thread.id === currentChatId.value);
  if (currentChatId.value && conversations.value.length === 0 && currentThreadIndex === 0) return;

  chatState.creatingNewChat = true;
  try {
    const newThread = await createThread(currentAgentId.value, '新的对话');
    if (newThread) {
      chatState.currentThreadId = newThread.id;
    }
  } catch (error) {
    handleChatError(error, 'create');
  } finally {
    chatState.creatingNewChat = false;
  }
};

const selectChat = async (chatId) => {
  if (!AgentValidator.validateAgentIdWithError(currentAgentId.value, '选择对话', handleValidationError)) return;

  // 切换线程时，不再中断上一个线程的流式输出
  // resetOnGoingConv(chatState.currentThreadId);
  chatState.currentThreadId = chatId;
  chatState.isLoadingMessages = true;
  try {
    await fetchThreadMessages({ agentId: currentAgentId.value, threadId: chatId });
  } catch (error) {
    handleChatError(error, 'load');
  } finally {
    chatState.isLoadingMessages = false;
  }

  await nextTick();
  scrollController.scrollToBottomStaticForce();
};

const deleteChat = async (chatId) => {
  if (!AgentValidator.validateAgentIdWithError(currentAgentId.value, '删除对话', handleValidationError)) return;
  try {
    // 如果是批量删除（参数为null），重新加载所有对话
    if (chatId === null) {
      await fetchThreads(currentAgentId.value);
      message.success('对话列表已刷新');
      return;
    }

    // 单个删除逻辑
    await deleteThread(chatId);

    // 从本地列表中移除已删除的线程，提供即时反馈
    const originalLength = threads.value.length;
    threads.value = threads.value.filter(thread => thread.id !== chatId);

    // 清理对应的消息缓存
    if (threadMessages.value[chatId]) {
      delete threadMessages.value[chatId];
    }

    // 如果删除的是当前选中的线程，需要切换到其他线程
    if (chatState.currentThreadId === chatId) {
      chatState.currentThreadId = null;
      if (threads.value.length > 0) {
        await selectChat(threads.value[0].id);
      }
    }

    // 如果确实删除了对话，显示成功提示
    if (originalLength > threads.value.length) {
      message.success('对话删除成功');
    }
  } catch (error) {
    handleChatError(error, 'delete');
  }
};

const renameChat = async (data) => {
  let { chatId, title } = data;
  if (!AgentValidator.validateRenameOperation(chatId, title, currentAgentId.value, handleValidationError)) return;
  if (title.length > 30) title = title.slice(0, 30);
  try {
    await updateThread(chatId, title);
  } catch (error) {
    handleChatError(error, 'rename');
  }
};

const handleSendMessage = async () => {
  const text = userInput.value.trim();
  if (!text || !currentAgent.value || isProcessing.value) return;

  // 根据检索模式验证资源选择
  const mode = retrievalMode.value;
  if (['mix', 'local'].includes(mode)) {
    // 混合检索或知识库检索模式需要选择知识库
    if (selectedKbIds.value.length === 0) {
      message.warning('请至少选择一个知识库');
      return;
    }
  }
  if (['mix', 'global'].includes(mode)) {
    // 混合检索或知识图谱检索模式需要选择图谱
    if (!selectedGraph.value) {
      message.warning('请选择一个知识图谱');
      return;
    }
  }

  // 如果没有当前线程，先创建一个新线程
  if (!currentChatId.value) {
    try {
      const newThread = await createThread(currentAgentId.value, text);
      if (newThread) {
        chatState.currentThreadId = newThread.id;
      } else {
        message.error('创建对话失败，请重试');
        return;
      }
    } catch (error) {
      handleChatError(error, 'create');
      return;
    }
  }

  userInput.value = '';
  await nextTick();
  scrollController.scrollToBottom(true);

  const threadId = currentChatId.value;
  const threadState = getThreadState(threadId);
  if (!threadState) return;

  threadState.isStreaming = true;
  resetOnGoingConv(threadId);
  threadState.streamAbortController = new AbortController();

  try {
    const response = await sendMessage({
      agentId: currentAgentId.value,
      threadId: currentChatId.value,
      text: text,
      signal: threadState.streamAbortController?.signal
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let stopReading = false;

    while (!stopReading) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmedLine = line.trim();
        if (trimmedLine) {
          try {
            const chunk = JSON.parse(trimmedLine);
            if (_processStreamChunk(chunk, threadId)) {
              stopReading = true;
              break;
            }
          } catch (e) { console.warn('Failed to parse stream chunk JSON:', e); }
        }
      }
    }
    if (!stopReading && buffer.trim()) {
      try {
        const chunk = JSON.parse(buffer.trim());
        if (_processStreamChunk(chunk, threadId)) {
          stopReading = true;
        }
      } catch (e) { console.warn('Failed to parse final stream chunk JSON:', e); }
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      handleChatError(error, 'send');
    }
  } finally {
    threadState.isStreaming = false;
    threadState.streamAbortController = null;
    resetOnGoingConv(threadId);
  }
};

// 发送或中断
const handleSendOrStop = async () => {
  const threadId = currentChatId.value;
  const threadState = getThreadState(threadId);
  if (isProcessing.value && threadState && threadState.streamAbortController) {
    // 中断生成
    threadState.streamAbortController.abort();

    // 中断后刷新消息历史，确保显示最新的状态
    try {
      await fetchThreadMessages({ agentId: currentAgentId.value, threadId: threadId });
      message.info('已中断对话生成');
    } catch (error) {
      console.error('刷新消息历史失败:', error);
      message.info('已中断对话生成');
    }
    return;
  }
  await handleSendMessage();
};

// ==================== UI HANDLERS ====================
const handleKeyDown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
};

// 处理示例问题点击
const handleExampleClick = (questionText) => {
  userInput.value = questionText;
  nextTick(() => {
    handleSendMessage();
  });
};

const buildExportPayload = () => {
  const payload = {
    chatTitle: currentThread.value?.title || '新对话',
    agentName: currentAgentName.value || currentAgent.value?.name || '智能助手',
    agentDescription: currentAgentMetadata.value?.description || currentAgent.value?.description || '',
    messages: conversations.value ? JSON.parse(JSON.stringify(conversations.value)) : [],
    onGoingMessages: onGoingConvMessages.value ? JSON.parse(JSON.stringify(onGoingConvMessages.value)) : []
  };

  return payload;
};

defineExpose({
  getExportPayload: buildExportPayload
});

const toggleSidebar = () => {
  uiState.isSidebarOpen = !uiState.isSidebarOpen;
  localStorage.setItem('chat_sidebar_open', uiState.isSidebarOpen);
};
const openAgentModal = () => emit('open-agent-modal');

// ==================== HELPER FUNCTIONS ====================
const getLastMessage = (conv) => {
  if (!conv?.messages?.length) return null;
  for (let i = conv.messages.length - 1; i >= 0; i--) {
    if (conv.messages[i].type === 'ai') return conv.messages[i];
  }
  return null;
};

const tryParseJson = (value) => {
  if (typeof value !== 'string') return null;
  try {
    return JSON.parse(value);
  } catch (_error) {
    return null;
  }
};

const toLabel = (value) => {
  if (value === null || value === undefined) return null;
  if (typeof value === 'object') {
    if (value.name) return String(value.name).trim();
    if (value.label) return String(value.label).trim();
    if (value.type) return String(value.type).trim();
    if (value.value) return String(value.value).trim();
    if (value.title) return String(value.title).trim();
    if (value.id) return String(value.id).trim();
  }
  return String(value).trim();
};

const normalizeTriple = (rawTriple) => {
  if (Array.isArray(rawTriple)) {
    const [subject, relation, object] = rawTriple;
    if (subject !== undefined && relation !== undefined && object !== undefined) {
      const s = toLabel(subject);
      const p = toLabel(relation);
      const o = toLabel(object);
      if (s && p && o) return [s, p, o];
    }
    return null;
  }

  if (rawTriple && typeof rawTriple === 'object') {
    let subject =
      rawTriple.subject ??
      rawTriple.source ??
      rawTriple.head ??
      rawTriple.from ??
      rawTriple.h ??
      rawTriple.entity ??
      rawTriple.entity1 ??
      rawTriple.node1 ??
      rawTriple.start ??
      rawTriple.a;
    let relation =
      rawTriple.relation ??
      rawTriple.relationship ??
      rawTriple.predicate ??
      rawTriple.type ??
      rawTriple.rel ??
      rawTriple.r ??
      rawTriple.edge ??
      rawTriple.description;
    let object =
      rawTriple.object ??
      rawTriple.target ??
      rawTriple.tail ??
      rawTriple.to ??
      rawTriple.t ??
      rawTriple.neighbor ??
      rawTriple.entity2 ??
      rawTriple.node2 ??
      rawTriple.end ??
      rawTriple.b;

    if (!subject && rawTriple.h) {
      subject = rawTriple.h.name ?? rawTriple.h.label ?? rawTriple.h.value ?? rawTriple.h.id ?? rawTriple.h;
    }
    if (!relation && rawTriple.r) {
      relation = rawTriple.r.type ?? rawTriple.r.name ?? rawTriple.r.label ?? rawTriple.r.value ?? rawTriple.r;
    }
    if (!object && rawTriple.t) {
      object = rawTriple.t.name ?? rawTriple.t.label ?? rawTriple.t.value ?? rawTriple.t.id ?? rawTriple.t;
    }

    if (subject !== undefined && relation !== undefined && object !== undefined) {
      const s = toLabel(subject);
      const p = toLabel(relation);
      const o = toLabel(object);
      if (s && p && o) return [s, p, o];
    }
  }

  return null;
};

const parseKnowledgeGraphContent = (rawContent) => {
  if (!rawContent) return null;

  let data = rawContent;

  if (typeof data === 'string') {
    const trimmed = data.trim();
    if (!trimmed) return null;

    let parsed = tryParseJson(trimmed);
    if (!parsed) {
      const fencedMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
      if (fencedMatch && fencedMatch[1]) {
        parsed = tryParseJson(fencedMatch[1]);
      }
    }

    if (parsed !== null) {
      data = parsed;
    } else {
      const fallbackTriples = parseTriplesFromJsonBlocks(trimmed);
      if (fallbackTriples.length > 0) {
        return { triples: fallbackTriples, query_type: 'search' };
      }
      return null;
    }
  }

  if (Array.isArray(data)) {
    const triples = data.map(normalizeTriple).filter(Boolean);
    return triples.length ? { triples, query_type: 'search' } : null;
  }

  if (data && typeof data === 'object') {
    // 处理统计结果（直接返回，保留所有元数据）
    if (data.query_type === 'statistics') {
      return data;
    }
    
    // 处理搜索结果（保留 query_type）
    if (data.query_type === 'search') {
      if (Array.isArray(data.triples)) {
        const triples = data.triples.map(normalizeTriple).filter(Boolean);
        if (triples.length) return { ...data, triples };
      }
      if (typeof data.content === 'string' && data.content.trim()) {
        return { ...data, triples: Array.isArray(data.triples) ? data.triples : [] };
      }
    }
    
    if (Array.isArray(data.triples)) {
      const triples = data.triples.map(normalizeTriple).filter(Boolean);
      if (triples.length) return { triples, query_type: data.query_type || 'search' };
    }

    if (data.result && Array.isArray(data.result.triples)) {
      const triples = data.result.triples.map(normalizeTriple).filter(Boolean);
      if (triples.length) return { triples, query_type: 'search' };
    }

    if (Array.isArray(data.data)) {
      const triples = data.data.map(normalizeTriple).filter(Boolean);
      if (triples.length) return { triples, query_type: 'search' };
    }

    // 处理嵌套图谱结果结构（如 hybrid 返回的 knowledge_graph_results）
    const nestedFields = ['knowledge_graph_results', 'result', 'output', 'data', 'content', 'json'];
    for (const field of nestedFields) {
      const nested = data[field];
      if (nested === undefined || nested === null || nested === data) continue;
      const parsedNested = parseKnowledgeGraphContent(nested);
      if (parsedNested) return parsedNested;
    }

    const singleTriple = normalizeTriple(data);
    if (singleTriple) return { triples: [singleTriple], query_type: 'search' };
  }

  return null;
};

const parseTriplesFromJsonBlocks = (text) => {
  if (!text) return [];
  const triples = [];
  const blockRegex = /```(?:json)?\s*([\s\S]*?)```/gi;
  let blockMatch;

  while ((blockMatch = blockRegex.exec(text))) {
    const blockContent = blockMatch[1];
    if (!blockContent) continue;

    blockContent
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .forEach((line) => {
        let parsedLine = null;
        try {
          parsedLine = JSON.parse(line);
        } catch (_error) {
          // ignore invalid json line
        }

        if (!parsedLine) return;

        if (Array.isArray(parsedLine)) {
          const normalized = normalizeTriple(parsedLine);
          if (normalized) {
            triples.push(normalized);
          }
          return;
        }

        const normalized = normalizeTriple(parsedLine);
        if (normalized) {
          triples.push(normalized);
        }
      });
  }

  return triples;
};

const normalizeToolResultPayload = (payload) => {
  if (payload === null || payload === undefined) {
    return null;
  }

  if (typeof payload === 'string') {
    const trimmed = payload.trim();
    return trimmed || null;
  }

  if (Array.isArray(payload)) {
    const flattened = payload
      .map((item) => normalizeToolResultPayload(item))
      .filter(Boolean);
    if (flattened.length === 0) return null;
    if (flattened.length === 1) return flattened[0];
    return flattened.join('\n');
  }

  if (typeof payload === 'object') {
    if (payload.type === 'text' && typeof payload.text === 'string') {
      return payload.text;
    }

    if (payload.content !== undefined) {
      const nested = normalizeToolResultPayload(payload.content);
      if (nested) return nested;
    }

    if (payload.data !== undefined) {
      const nested = normalizeToolResultPayload(payload.data);
      if (nested) return nested;
    }

    if (payload.result !== undefined) {
      const nested = normalizeToolResultPayload(payload.result);
      if (nested) return nested;
    }

    if (payload.output !== undefined) {
      const nested = normalizeToolResultPayload(payload.output);
      if (nested) return nested;
    }

    if (payload.json !== undefined) {
      const nested = normalizeToolResultPayload(payload.json);
      if (nested) return nested;
    }

    if (Array.isArray(payload.triples)) {
      return payload;
    }

    return payload;
  }

  return payload;
};

const extractGraphPayloadFromToolCall = (toolCall) => {
  if (!toolCall) return null;

  const candidates = [
    toolCall?.tool_call_result?.content,
    toolCall?.tool_call_result?.data,
    toolCall?.tool_call_result?.result,
    toolCall?.tool_call_result?.output,
    toolCall?.tool_call_result?.json,
    toolCall?.tool_call_result,
    toolCall?.result,
    toolCall?.output,
  ];

  for (const candidate of candidates) {
    const normalized = normalizeToolResultPayload(candidate);
    if (normalized) {
      return normalized;
    }
  }

  return null;
};

const collectKnowledgeGraphData = (messages) => {
  if (!Array.isArray(messages)) return null;

  const triples = [];
  const tripleKeys = new Set();
  let statisticsResult = null;  // 保存最后一个统计结果
  let searchResultMeta = null;

  messages.forEach((msg) => {
    if (!msg || msg.type !== 'ai') return;

    const toolCalls = Array.isArray(msg.tool_calls)
      ? msg.tool_calls
      : Object.values(msg.tool_calls || {});

    toolCalls.forEach((toolCall) => {
      const rawContent = extractGraphPayloadFromToolCall(toolCall);
      if (!rawContent) return;

      const parsed = parseKnowledgeGraphContent(rawContent);
      if (!parsed) return;
      
      // 处理统计结果
      if (parsed.query_type === 'statistics') {
        statisticsResult = parsed;
        return;
      }

      // 缓存搜索结果元数据（用于保留 query/content/graph_type 等字段）
      if (parsed.query_type === 'search') {
        searchResultMeta = {
          ...(searchResultMeta || { query_type: 'search' }),
          ...parsed,
        };
      }
      
      // 处理搜索结果（三元组）
      if (parsed?.triples?.length) {
        parsed.triples.forEach((triple) => {
          const key = triple.join('||');
          if (!tripleKeys.has(key)) {
            tripleKeys.add(key);
            triples.push(triple);
          }
        });
      }
    });
  });

  // 优先返回统计结果（如果存在）
  if (statisticsResult) {
    return statisticsResult;
  }
  
  // 返回搜索结果（三元组优先）
  if (triples.length > 0) {
    return {
      ...(searchResultMeta || {}),
      query_type: 'search',
      triples,
    };
  }

  // 支持 content-only 图谱结果（如部分 LightRAG 返回）
  if (searchResultMeta && typeof searchResultMeta.content === 'string' && searchResultMeta.content.trim()) {
    return {
      ...searchResultMeta,
      query_type: 'search',
      triples: Array.isArray(searchResultMeta.triples) ? searchResultMeta.triples : [],
    };
  }

  return null;
};

const findLastAiMessageIndex = (messages) => {
  if (!Array.isArray(messages)) return -1;
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i]?.type === 'ai') return i;
  }
  return -1;
};

const isSameGraphData = (left, right) => {
  if (!left || !right) return false;
  
  // 不同类型的数据不相同
  if (left.query_type !== right.query_type) return false;
  
  // 统计结果比较
  if (left.query_type === 'statistics') {
    return left.total_count === right.total_count && 
           left.keyword === right.keyword;
  }
  
  // 搜索结果比较（三元组）
  const leftTriples = Array.isArray(left.triples) ? left.triples : [];
  const rightTriples = Array.isArray(right.triples) ? right.triples : [];
  if (leftTriples.length !== rightTriples.length) return false;

  for (let i = 0; i < leftTriples.length; i += 1) {
    const lt = leftTriples[i];
    const rt = rightTriples[i];
    if (!Array.isArray(lt) || !Array.isArray(rt)) return false;
    if (lt[0] !== rt[0] || lt[1] !== rt[1] || lt[2] !== rt[2]) return false;
  }
  return true;
};

const attachKnowledgeGraphData = (convList) => {
  if (!Array.isArray(convList)) return [];

  // 仅在“智能混合(mix)”或“知识图谱(global)”检索模式下附加子图
  if (!['mix', 'global'].includes(retrievalMode.value)) {
    return convList;
  }

  return convList.map((conv) => {
    if (!conv?.messages) return conv;

    const graphData = collectKnowledgeGraphData(conv.messages);
    if (!graphData) return conv;

    const lastAiIndex = findLastAiMessageIndex(conv.messages);
    if (lastAiIndex === -1) return conv;

    let messagesChanged = false;
    const enrichedMessages = conv.messages.map((msg, idx) => {
      if (idx !== lastAiIndex || msg?.type !== 'ai') return msg;
      if (isSameGraphData(msg.knowledgeGraphData, graphData)) return msg;
      messagesChanged = true;
      return { ...msg, knowledgeGraphData: graphData };
    });

    if (!messagesChanged) return conv;

    return {
      ...conv,
      messages: enrichedMessages
    };
  });
};

const showMsgRefs = (msg) => {
  if (msg.isLast) return ['copy'];
  return false;
};

// ==================== LIFECYCLE & WATCHERS ====================
const loadChatsList = async () => {
  const agentId = currentAgentId.value;
  if (!agentId) {
    console.warn('No agent selected, cannot load chats list');
    threads.value = [];
    chatState.currentThreadId = null;
    return;
  }

  try {
    await fetchThreads(agentId);
    if (currentAgentId.value !== agentId) return;

    // 如果当前线程不在线程列表中，清空当前线程
    if (chatState.currentThreadId && !threads.value.find(t => t.id === chatState.currentThreadId)) {
      chatState.currentThreadId = null;
    }

    // 进入对话界面默认保持“新对话”状态，不自动选中历史会话
  } catch (error) {
    handleChatError(error, 'load');
  }
};

const initAll = async () => {
  try {
    if (!agentStore.isInitialized) {
      await agentStore.initialize();
    }
  } catch (error) {
    handleChatError(error, 'load');
  }
};

onMounted(async () => {
  await initAll();
  scrollController.enableAutoScroll();
});

onActivated(() => {
  chatState.currentThreadId = null;
});


watch(currentAgentId, async (newAgentId, oldAgentId) => {
  if (newAgentId !== oldAgentId) {
    // 清理当前线程状态
    chatState.currentThreadId = null;
    threadMessages.value = {};
    // 清理所有线程状态
    resetOnGoingConv();

    if (newAgentId) {
      await loadChatsList();
    } else {
      threads.value = [];
    }
  }
}, { immediate: true });

watch(conversations, () => {
  if (isProcessing.value) {
    scrollController.scrollToBottom();
  }
}, { deep: true, flush: 'post' });

</script>

<style lang="less" scoped>
@import '@/assets/css/main.css';

.chat-container {
  display: flex;
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: transparent;
}

.knowledge-panel {
  position: fixed;
  right: 16px;
  top: 96px;
  width: 360px;
  background: var(--glass-bg);
  border: var(--glass-border);
  border-radius: 14px;
  box-shadow: var(--glass-shadow);
  backdrop-filter: var(--glass-blur);
  padding: 18px 18px 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 20;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.panel-title {
  font-weight: 700;
  color: var(--text-primary);
  font-size: 16px;
}

.panel-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.panel-meta {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 11px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.meta-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 8px;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border-radius: 10px;
  font-size: 12px;
  border: 1px solid rgba(99, 102, 241, 0.24);
}

.panel-mode-tag {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  border: 1px solid rgba(99, 102, 241, 0.24);
}

.panel-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px dashed rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 10px;
  background: rgba(15, 23, 42, 0.35);
}

.panel-section {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 12px 14px;
  background: rgba(30, 41, 59, 0.35);
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: var(--text-primary);
}

.section-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: 8px;
}

.section-footer {
  margin-top: 8px;
  color: var(--text-tertiary);
  font-size: 12px;
}

@media (max-width: 1024px) {
  .knowledge-panel {
    position: static;
    width: 100%;
    margin-top: 12px;
  }
}

/* 全局样式变量引用 */
.chat-container {
  display: flex;
  height: 100%;
  width: 100%;
  position: relative;
  overflow: hidden;
  background: transparent;
}

.chat {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  background: transparent; /* 透明背景，显示全局渐变 */
  box-sizing: border-box;
  overflow-y: scroll;
  transition: all 0.3s ease;

  .chat-header {
    user-select: none;
    position: sticky;
    top: 0;
    z-index: 10;
    height: var(--header-height);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 8px;
    background: transparent; /* 透明表头 */
    
    .header__left, .header__right, .header__center {
      display: flex;
      align-items: center;
    }
  }
}

.chat-examples {
  padding: 0 50px;
  text-align: center;
  position: absolute;
  top: 15%;
  width: 100%;
  z-index: 9;
  animation: slideInUp 0.5s ease-out;

  h1 {
    margin-bottom: 20px;
    font-size: 1.3rem;
    color: var(--text-primary);
    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
  }

  p {
    font-size: 1.1rem;
    color: var(--text-secondary);
  }

  .agent-icons {
    height: 180px;
    filter: drop-shadow(0 0 10px rgba(6, 182, 212, 0.3));
  }

  .example-questions {
    margin-top: 16px;
    text-align: center;

    .example-title {
      font-size: 0.85rem;
      color: var(--text-secondary);
      margin-bottom: 12px;
    }

    .example-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
    }

    .example-chip {
      padding: 6px 12px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 16px;
      cursor: pointer;
      font-size: 0.8rem;
      color: var(--text-primary);
      transition: all 0.15s ease;
      white-space: nowrap;
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      backdrop-filter: blur(4px);

      &:hover {
        border-color: var(--main-color);
        color: var(--main-color);
        background: rgba(6, 182, 212, 0.1);
        box-shadow: 0 0 8px rgba(6, 182, 212, 0.2);
      }

      &:active {
        transform: translateY(0);
      }
    }
  }

  .inputer-init {
    margin: 20px auto;
    width: 90%;
    max-width: 720px;
  }
}

.chat-loading {
  padding: 0 50px;
  text-align: center;
  position: absolute;
  top: 20%;
  width: 100%;
  z-index: 9;
  animation: slideInUp 0.5s ease-out;

  span {
    margin-left: 8px;
    color: var(--text-secondary);
  }
}

.chat-box {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  flex-grow: 1;
  padding: 1rem 1.5rem;
  display: flex;
  flex-direction: column;
}

.conv-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bottom {
  position: sticky;
  bottom: 0;
  width: 100%;
  margin: 0 auto;
  padding: 16px 2rem 24px 2rem;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  z-index: 1000;

  .message-input-wrapper {
    width: 100%;
    max-width: 720px;
    margin: 0 auto;

    .bottom-actions {
      display: flex;
      justify-content: center;
      align-items: center;
    }

    .note {
      font-size: small;
      color: var(--text-disabled);
      margin: 4px 0;
      user-select: none;
    }
  }
}

/* 滚动条样式 */
.conversation-list::-webkit-scrollbar,
.chat::-webkit-scrollbar {
  position: absolute;
  width: 4px;
  height: 4px;
}

.conversation-list::-webkit-scrollbar-track,
.chat::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 4px;
}

.conversation-list::-webkit-scrollbar-thumb,
.chat::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.conversation-list::-webkit-scrollbar-thumb:hover,
.chat::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

@media (max-width: 1024px) {
  .chat {
    padding-right: 0;
  }
}

.loading-dots {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}

.loading-dots div {
  width: 6px;
  height: 6px;
  background: linear-gradient(135deg, var(--main-color), var(--main-700));
  border-radius: 50%;
  animation: dotPulse 1.4s infinite ease-in-out both;
  box-shadow: 0 0 5px rgba(6, 182, 212, 0.5);
}

.loading-dots div:nth-child(1) { animation-delay: -0.32s; }
.loading-dots div:nth-child(2) { animation-delay: -0.16s; }
.loading-dots div:nth-child(3) { animation-delay: 0s; }

.generating-status {
  display: flex;
  justify-content: flex-start;
  padding: 1rem 0;
  animation: fadeInUp 0.4s ease-out;
  transition: all 0.2s;
}

.generating-indicator {
  display: flex;
  align-items: center;
  padding: 0.75rem 0rem;

  .generating-text {
    margin-left: 12px;
    color: var(--text-secondary);
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.025em;
  }
}

@keyframes dotPulse {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1.1); opacity: 1; }
}

@keyframes slideInUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1800px) {
  .chat-header {
    background: rgba(15, 23, 42, 0.2);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
}

@media (max-width: 768px) {
  .chat-sidebar.collapsed {
    width: 0;
    border: none;
  }

  .chat-header .header__left .text {
    display: none;
  }
}

@media (max-width: 520px) {
  .sidebar-backdrop {
    display: block;
    background-color: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(2px);
  }

  .chat-box {
    padding: 1rem 1rem;
  }

  .bottom {
    padding: 8px 1rem 16px 1rem;
    background: var(--bg-container);
    border-top: var(--glass-border);
  }

  .retrieval-mode-wrapper {
    width: 95%;
    margin: 0 auto 15px auto;
  }

  .chat-header {
    padding: 0.5rem 0 !important;
  }

  .floating-sidebar {
    background: var(--bg-elevated);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  }
}

.hide-text {
  display: none;
}

/* 独立检索模式选择器样式 */
.retrieval-mode-wrapper {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  width: 90%;
  max-width: 720px;
  margin: 0 auto 15px auto;
}

.retrieval-mode-selector-standalone {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  width: 100%;

  .retrieval-mode-buttons {
    display: flex;
    align-items: center;
    gap: 1px;
    background: transparent;
    padding: 0;
    border: none;
  }

  .retrieval-mode-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 6px 8px;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 11px;
    color: var(--text-secondary);
    font-weight: 400;
    position: relative;
    min-width: 60px;
    white-space: nowrap;
    user-select: none;

    .retrieval-mode-icon {
      font-size: 12px;
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    &:hover {
      background: rgba(6, 182, 212, 0.1);
      color: var(--main-color);
      .retrieval-mode-icon { color: var(--main-color); }
    }

    &.active {
      background: var(--main-color);
      color: white;
      border-radius: 4px;
      .retrieval-mode-icon { color: white; }
    }
  }
}

.sidebar-backdrop {
  display: none;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.4);
  z-index: 99;
  animation: fadeIn 0.3s ease;
}

.floating-sidebar {
  position: absolute !important;
  z-index: 100;
  height: 100%;
  left: 0;
  top: 0;
  transform: translateX(0);
  transition: transform 0.3s ease;
  width: 80% !important;
  max-width: 300px;

  &.no-transition { transition: none !important; }
  &.collapsed { transform: translateX(-100%); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>

<style lang="less">
div.agent-nav-btn {
  display: flex;
  gap: 10px;
  padding: 8px 16px;
  justify-content: center;
  align-items: center;
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  width: auto;
  font-size: 14px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);

  &:hover {
    background: rgba(6, 182, 212, 0.1);
    color: #06b6d4;
    border-color: rgba(6, 182, 212, 0.3);
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.2);
  }

  .nav-btn-icon {
    height: 20px;
  }
}
</style>
