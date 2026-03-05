<template>
  <div class="input-box" :class="[customClasses, { 'single-line': isSingleLine }]" @click="focusInput">
    <!-- 输入区域：选项按钮 + 输入框 + 发送按钮 -->
    <div class="input-area">
      <div class="expand-options" v-if="hasOptionsLeft">
        <a-popover
          v-model:open="optionsExpanded"
          placement="bottomLeft"
          trigger="click"
        >
          <template #content>
            <div class="popover-options">
              <slot name="options-left">
                <div class="no-options">没有配置 options</div>
              </slot>
            </div>
          </template>
          <a-button
            type="text"
            size="small"
            class="expand-btn"
          >
            <template #icon>
              <PlusOutlined :class="{ 'rotated': optionsExpanded }" />
            </template>
          </a-button>
        </a-popover>
      </div>

      <textarea
        ref="inputRef"
        class="user-input"
        :value="inputValue"
        @keydown="handleKeyPress"
        @input="handleInput"
        @focus="focusInput"
        :placeholder="placeholder"
        :disabled="disabled"
      />

      <div class="send-button-container">
        <a-tooltip :title="isLoading ? '停止回答' : ''">
          <a-button
            @click="handleSendOrStop"
            :disabled="sendButtonDisabled"
            type="link"
            class="send-button"
          >
            <template #icon>
              <component :is="getIcon" class="send-btn"/>
            </template>
          </a-button>
        </a-tooltip>
      </div>
    </div>

    <!-- 检索模式选择器 - 紧贴输入框下方，从左侧开始 -->
    <div class="retrieval-mode-selector" v-if="showRetrievalModes">
      <div class="retrieval-mode-buttons">
        <a-tooltip
          v-for="mode in retrievalModes"
          :key="mode.value"
          :title="mode.description"
          placement="top"
          :mouse-enter-delay="0.5"
        >
          <button
            :class="['retrieval-mode-btn', { 'active': retrievalMode === mode.value }]"
            @click="handleRetrievalModeChange(mode.value)"
            :style="{ '--mode-color': mode.color }"
          >
            <div class="retrieval-mode-icon">
              <component :is="mode.icon" />
            </div>
            <span class="retrieval-mode-text">{{ mode.label }}</span>
            <div class="retrieval-mode-indicator" v-if="retrievalMode === mode.value"></div>
          </button>
        </a-tooltip>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch, onBeforeUnmount, useSlots } from 'vue';
import {
  SendOutlined,
  ArrowUpOutlined,
  LoadingOutlined,
  PauseOutlined,
  PlusOutlined,
  MergeCellsOutlined,
  DatabaseOutlined,
  GlobalOutlined,
  RobotOutlined
} from '@ant-design/icons-vue';


const inputRef = ref(null);
const isSingleLine = ref(true);
const optionsExpanded = ref(false);
const singleLineHeight = ref(0); // Add this
// 用于防抖的定时器
const debounceTimer = ref(null);
const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '输入问题...'
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  sendButtonDisabled: {
    type: Boolean,
    default: false
  },
  autoSize: {
    type: Object,
    default: () => ({ minRows: 2, maxRows: 6 })
  },
  sendIcon: {
    type: String,
    default: 'ArrowUpOutlined'
  },
  customClasses: {
    type: Object,
    default: () => ({})
  },
  showRetrievalModes: {
    type: Boolean,
    default: false
  },
  retrievalMode: {
    type: String,
    default: 'mix'
  }
});

const emit = defineEmits([
  'update:modelValue',
  'send',
  'keydown',
  'update:retrieval-mode'
]);
const slots = useSlots();
const hasOptionsLeft = computed(() => {
  const slot = slots['options-left'];
  if (!slot) {
    return false;
  }
  const renderedNodes = slot();
  return Boolean(renderedNodes && renderedNodes.length);
});

// 图标映射


// ????
const iconComponents = {
  'SendOutlined': SendOutlined,
  'ArrowUpOutlined': ArrowUpOutlined,
  'PauseOutlined': PauseOutlined,
  'MergeCellsOutlined': MergeCellsOutlined,
  'DatabaseOutlined': DatabaseOutlined,
  'GlobalOutlined': GlobalOutlined,
  'RobotOutlined': RobotOutlined
};

// ??????????????
const getIcon = computed(() => {
  if (props.isLoading) {
    return PauseOutlined;
  }
  return iconComponents[props.sendIcon] || ArrowUpOutlined;
});

// ??????

const retrievalModes = [
  {
    value: 'mix',
    label: '混合检索',
    shortLabel: '混合',
    icon: 'MergeCellsOutlined',
    description: '结合知识库与知识图谱的智能混合检索',
    color: '#6366f1'
  },
  {
    value: 'local',
    label: '知识库检索',
    shortLabel: '知识库',
    icon: 'DatabaseOutlined',
    description: '仅使用选定知识库进行检索（语义/向量）',
    color: '#8b5cf6'
  },
  {
    value: 'global',
    label: '知识图谱检索',
    shortLabel: '图谱',
    icon: 'GlobalOutlined',
    description: '仅使用选定知识图谱进行检索',
    color: '#3b82f6'
  },
  {
    value: 'llm',
    label: '大模型检索',
    shortLabel: '大模型',
    icon: 'RobotOutlined',
    description: '调用大模型自身知识，不检索知识库或知识图谱',
    color: '#10b981'
  }
];






// 创建本地引用以进行双向绑定
const inputValue = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

// 检索模式的双向绑定
const localRetrievalMode = computed({
  get: () => props.retrievalMode,
  set: (val) => emit('update:retrieval-mode', val)
});

// 处理键盘事件
const handleKeyPress = (e) => {
  emit('keydown', e);
};

// 处理输入事件
const handleInput = (e) => {
  const value = e.target.value;
  emit('update:modelValue', value);
};

// 处理发送按钮点击
const handleSendOrStop = () => {
  emit('send');
};

// 处理检索模式切换
const handleRetrievalModeChange = (mode) => {
  localRetrievalMode.value = mode;
};

// 用于存储固定的单行宽度基准
const singleLineWidth = ref(0);

// 检查行数
const checkLineCount = () => {
  if (!inputRef.value || singleLineHeight.value === 0) {
    return;
  }
  const textarea = inputRef.value;
  const content = inputValue.value;

  // 主要判断依据：内容是否包含换行符
  const hasNewlines = content.includes('\n');

  // 辅助判断：内容是否超出单行宽度（使用固定的单行宽度基准）
  let contentExceedsWidth = false;
  if (!hasNewlines && content.trim() && singleLineWidth.value > 0) {
    // 使用固定的单行宽度作为测量基准，避免因模式切换导致的宽度变化
    const measureDiv = document.createElement('div');
    measureDiv.style.cssText = `
      position: absolute;
      visibility: hidden;
      white-space: nowrap;
      font-family: ${getComputedStyle(textarea).fontFamily};
      font-size: ${getComputedStyle(textarea).fontSize};
      line-height: ${getComputedStyle(textarea).lineHeight};
      padding: 0;
      border: none;
      width: ${singleLineWidth.value}px;
    `;
    measureDiv.textContent = content;
    document.body.appendChild(measureDiv);

    // 检查内容是否会换行（基于固定的单行宽度）
    contentExceedsWidth = measureDiv.scrollWidth > measureDiv.clientWidth;
    document.body.removeChild(measureDiv);
  }

  const shouldBeMultiLine = hasNewlines || contentExceedsWidth;
  isSingleLine.value = !shouldBeMultiLine;

  // 根据模式调整高度
  if (shouldBeMultiLine) {
    // 多行模式：让textarea自适应内容高度
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.max(textarea.scrollHeight, singleLineHeight.value)}px`;
  } else {
    // 单行模式：清除内联样式，让CSS控制高度
    textarea.style.height = '';
  }
};



// 聚焦输入框
const focusInput = () => {
  if (inputRef.value && !props.disabled) {
    inputRef.value.focus();
  }
};

// 监听输入值变化
watch(inputValue, () => {
  nextTick(() => {
    checkLineCount();
  });
});

// 监听输入框尺寸变化
/* const observeTextareaResize = () => {
  if (inputRef.value) {
    const textarea = inputRef.value;
    if (textarea) {
      // 创建 ResizeObserver 来监听文本域尺寸变化
      const resizeObserver = new ResizeObserver(() => {
        checkLineCount();
      });
      resizeObserver.observe(textarea);

      // 在组件卸载时断开观察器
      onBeforeUnmount(() => {
        resizeObserver.disconnect();
      });
    }
  }
}; */

// Wait for component to mount before setting up onStartTyping
onMounted(() => {
  // console.log('Component mounted');
  nextTick(() => {
    if (inputRef.value) {
      // 记录单行模式下的高度和宽度基准
      singleLineHeight.value = inputRef.value.clientHeight;
      singleLineWidth.value = inputRef.value.clientWidth;
      checkLineCount();
      inputRef.value.focus();
    }
  });
  // observeTextareaResize();
});

// 组件卸载时清除定时器
onBeforeUnmount(() => {
  if (debounceTimer.value) {
    clearTimeout(debounceTimer.value);
  }
});

</script>

<style lang="less" scoped>
.input-box {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin: 0 auto;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  gap: 0;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  /* Default: Multi-line layout */
  padding: 1.6rem 1rem 1.2rem 1rem;

  .input-area {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    width: 100%;
  }

  .expand-options {
    flex-shrink: 0;
  }

  .send-button-container {
    flex-shrink: 0;
  }

  &:focus-within {
    border-color: #06b6d4;
    background: rgba(15, 23, 42, 0.6);
    box-shadow: 0 0 25px rgba(6, 182, 212, 0.15);
  }

  &:hover {
    border-color: rgba(6, 182, 212, 0.3);
  }

  &.single-line {
    padding: 1.4rem 1rem;

    .input-area {
      align-items: center;
    }

    .user-input {
      min-height: 44px;
      height: 44px;
      align-self: center;
      white-space: nowrap;
      overflow: hidden;
      line-height: 1.5;
    }

    .expand-options, .send-button-container {
      align-self: center;
    }
  }
}

.expand-options {
  display: flex;
  align-items: center;
}

.user-input {
  flex: 1;
  width: 100%;
  padding: 0;
  background-color: transparent;
  border: none;
  margin: 0;
  color: var(--text-primary);
  font-size: 15px;
  outline: none;
  resize: none;
  line-height: 1.5;
  font-family: inherit;
  min-height: 70px; /* Default min-height for multi-line (increased by 56% total) */
  max-height: 310px; /* Also increase max-height proportionally */

  &:focus {
    outline: none;
    box-shadow: none;
  }

  &::placeholder {
    color: var(--text-tertiary);
  }
}

.send-button-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.expand-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: all 0.2s ease;

  &:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: var(--main-color);
  }

  .anticon {
    font-size: 12px;
    transition: transform 0.2s ease;

    &.rotated {
      transform: rotate(45deg);
    }
  }
}

// Popover 选项样式
.popover-options {
  min-width: 200px;
  max-width: 300px;

  .no-options {
    color: var(--text-secondary);
    font-size: 12px;
    text-align: center;
  }

  :deep(.opt-item) {
    border-radius: 12px;
    border: 1px solid var(--border-color-base);
    padding: 5px 10px;
    cursor: pointer;
    font-size: 12px;
    color: var(--text-secondary);
    transition: all 0.2s ease;
    margin: 4px;
    display: inline-block;

    &:hover {
      background-color: rgba(6, 182, 212, 0.1);
      color: var(--main-color);
    }

    &.active {
      color: var(--main-color);
      border: 1px solid var(--main-color);
      background-color: rgba(6, 182, 212, 0.1);
    }
  }
}

.send-button.ant-btn-icon-only {
  height: 36px;
  width: 36px;
  cursor: pointer;
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);
  color: white;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  position: relative;

  &:hover {
    background: linear-gradient(135deg, #22d3ee 0%, #06b6d4 100%);
    box-shadow: 0 4px 16px rgba(6, 182, 212, 0.4);
  }

  &:active {
    box-shadow: 0 2px 4px rgba(6, 182, 212, 0.2);
  }

  &:disabled {
    background: var(--text-tertiary);
    cursor: not-allowed;
    box-shadow: none;
    opacity: 0.7;
  }

  .send-btn {
    position: relative;
    z-index: 1;
  }
}

// 检索模式选择器样式 - 紧贴左下角设计
.retrieval-mode-selector {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin: 0;
  padding: 0;
  position: relative;
  width: 100%;
  box-sizing: border-box;

  .retrieval-mode-buttons {
    display: flex;
    align-items: center;
    gap: 1px;
    background: transparent;
    padding: 0;
    border-radius: 0;
    border: none;
    backdrop-filter: none;
    box-shadow: none;
    margin: 0;
  }

  .retrieval-mode-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 6px 8px;
    background: transparent;
    border: none;
    border-radius: 0;
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

    .retrieval-mode-text {
      white-space: nowrap;
      font-weight: 400;
    }

    &:hover {
      background: rgba(255, 255, 255, 0.05);
      color: var(--main-color);

      .retrieval-mode-icon {
        color: var(--main-color);
      }

      .retrieval-mode-text {
        color: var(--main-color);
      }
    }

    &.active {
      background: var(--main-color);
      color: white;
      border-radius: 6px;

      .retrieval-mode-icon {
        color: white;
      }

      .retrieval-mode-text {
        color: white;
        font-weight: 500;
      }
    }
  }
}


@media (max-width: 520px) {
  .input-box {
    border-radius: 14px;
    padding: 1.2rem 0.875rem;

    &.single-line {
      padding: 1.2rem 0.875rem;
    }

    .input-area {
      gap: 6px;
    }

    &:focus-within {
      box-shadow: 0 0 15px rgba(6, 182, 212, 0.1);
    }

    &:hover {
      box-shadow: 0 0 10px rgba(6, 182, 212, 0.05);
    }
  }

  .user-input {
    font-size: 16px; /* Prevents zoom on iOS */
    min-height: 32px;
    padding: 2px 0;
  }

  .send-button.ant-btn-icon-only {
    height: 32px;
    width: 32px;
    font-size: 14px;

    &:hover {
      transform: translateY(-0.5px) scale(1.02);
    }
  }

  .retrieval-mode-selector {
    margin: 0;
    padding: 0;

    .retrieval-mode-buttons {
      gap: 1px;
      padding: 2px;
      border-radius: 12px;
      background: rgba(0, 0, 0, 0.2);
      box-shadow: none;
    }

    .retrieval-mode-btn {
      padding: 8px 10px;
      font-size: 11px;
      min-width: 60px;
      gap: 4px;
      border-radius: 10px;

      .retrieval-mode-icon {
        font-size: 12px;
      }

      .retrieval-mode-text {
        font-size: 10px;
        font-weight: 500;
      }
    }
  }
}

// 平板设备优化
@media (min-width: 521px) and (max-width: 768px) {
  .input-box {
    padding: 1.4rem 1rem;

    &.single-line {
      padding: 1.4rem 1rem;
    }

    .input-area {
      gap: 7px;
    }
  }

  .retrieval-mode-selector {
    margin: 0;
    padding: 0;

    .retrieval-mode-btn {
      padding: 9px 14px;
      font-size: 12px;
      min-width: 65px;
      gap: 5px;
      border-radius: 11px;

      .retrieval-mode-icon {
        font-size: 13px;
      }

      .retrieval-mode-text {
        font-size: 11px;
      }
    }
  }
}

// 高对比度模式支持
@media (prefers-contrast: high) {
  .retrieval-mode-selector {
    .retrieval-mode-buttons {
      border: 2px solid #fff;
      background: #000;
    }

    .retrieval-mode-btn {
      color: #fff;
      border: 1px solid #666;

      &:hover {
        background: #f0f0f0;
        color: #000;
      }

      &.active {
        background: #000;
        color: #fff;
        border-color: #000;
      }
    }
  }
}

// 减少动画模式支持
@media (prefers-reduced-motion: reduce) {
  .retrieval-mode-selector {
    .retrieval-mode-buttons,
    .retrieval-mode-btn {
      transition: none;
    }

    .retrieval-mode-btn.active {
      animation: none;

      &::after {
        animation: none;
      }
    }
  }
}
</style>
