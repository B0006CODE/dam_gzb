<template>
<div class="database-info-container">
  <DatabaseHeader />
  <BreadcrumbNav />

  <!-- Maximize Graph Modal -->
  <a-modal
    v-model:open="isGraphMaximized"
    :footer="null"
    :closable="false"
    width="100%"
    wrap-class-name="full-modal"
    :mask-closable="false"
  >
    <template #title>
      <div class="maximized-graph-header">
        <h3>知识图谱 (最大化)</h3>
        <a-button type="text" @click="toggleGraphMaximize">
          <CompressOutlined /> 退出最大化
        </a-button>
      </div>
    </template>
    <div class="maximized-graph-content">
      <div v-if="!isGraphSupported" class="graph-disabled">
        <div class="disabled-content">
          <h4>知识图谱不可用</h4>
          <p>当前知识库类型 "{{ getKbTypeLabel(database.kb_type || 'lightrag') }}" 不支持知识图谱功能。</p>
          <p>只有 LightRAG 类型的知识库支持知识图谱。</p>
        </div>
      </div>
      <KnowledgeGraphViewer
        v-else-if="isGraphMaximized"
        :initial-database-id="databaseId"
        :hide-db-selector="true"
      />
    </div>
  </a-modal>

  <FileDetailModal />

  <FileUploadModal
    v-model:visible="addFilesModalVisible"
  />

  <div class="unified-layout" :class="{ 'single-column': !isRightPanelActive }">
    <div class="left-panel" :style="leftPanelStyle">
      <FileTable
        :right-panel-visible="state.rightPanelVisible"
        @show-add-files-modal="showAddFilesModal"
        @toggle-right-panel="toggleRightPanel"
      />
    </div>

    <div class="resize-handle" ref="resizeHandle" v-show="isRightPanelActive"></div>

    <div class="right-panel" v-show="isRightPanelActive" :style="rightPanelStyle">
      <KnowledgeGraphSection
        :visible="panels.graph.visible"
        :style="styleGraph"
        @toggle-visible="togglePanel('graph')"
      />
    </div>
  </div>
</div>
</template>

<script setup>
import { onMounted, reactive, ref, watch, onUnmounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useDatabaseStore } from '@/stores/database';
import { getKbTypeLabel } from '@/utils/kb_utils';
import { CompressOutlined } from '@ant-design/icons-vue';
import KnowledgeGraphViewer from '@/components/KnowledgeGraphViewer.vue';
import DatabaseHeader from '@/components/DatabaseHeader.vue';
import FileTable from '@/components/FileTable.vue';
import FileDetailModal from '@/components/FileDetailModal.vue';
import FileUploadModal from '@/components/FileUploadModal.vue';
import KnowledgeGraphSection from '@/components/KnowledgeGraphSection.vue';
import BreadcrumbNav from '@/components/BreadcrumbNav.vue';

const route = useRoute();
const store = useDatabaseStore();

const databaseId = computed(() => store.databaseId);
const database = computed(() => store.database);
const state = computed(() => store.state);
const isGraphMaximized = computed({
    get: () => store.state.isGraphMaximized,
    set: (val) => store.state.isGraphMaximized = val
});

// 计算属性：是否支持知识图谱
const isGraphSupported = computed(() => {
  const kbType = database.value.kb_type?.toLowerCase();
  return kbType === 'lightrag';
});

// 面板可见性控制
const panels = reactive({
  graph: { visible: true },
});

const togglePanel = (panel) => {
  panels[panel].visible = !panels[panel].visible;
};

// 切换右侧面板显示/隐藏
const toggleRightPanel = () => {
  store.state.rightPanelVisible = !store.state.rightPanelVisible;
};

// 拖拽调整大小
const leftPanelWidth = ref(60);
const isDragging = ref(false);
const resizeHandle = ref(null);

const isRightPanelActive = computed(() =>
  store.state.rightPanelVisible && isGraphSupported.value
);

const leftPanelStyle = computed(() => {
  if (!isRightPanelActive.value) {
    return {
      width: '100%',
      maxWidth: '1200px',
      margin: '0 auto',
    };
  }
  return { width: `${leftPanelWidth.value}%` };
});

const rightPanelStyle = computed(() => ({
  width: `${100 - leftPanelWidth.value}%`,
}));

const styleGraph = computed(() => ({
  height: '100%',
  flex: '1'
}));

// 添加文件弹窗
const addFilesModalVisible = ref(false);

// 显示添加文件弹窗
const showAddFilesModal = () => {
  addFilesModalVisible.value = true;
};

// 切换图谱最大化状态
const toggleGraphMaximize = () => {
  isGraphMaximized.value = !isGraphMaximized.value;
};

watch(() => route.params.database_id, async (newId) => {
    store.databaseId = newId;
    store.stopAutoRefresh();
    await store.getDatabaseInfo(newId);
    store.startAutoRefresh();
  },
  { immediate: true }
);

// 组件挂载时启动示例轮播
onMounted(() => {
  store.databaseId = route.params.database_id;
  store.getDatabaseInfo();
  store.startAutoRefresh();

  // 添加拖拽事件监听
  if (resizeHandle.value) {
    resizeHandle.value.addEventListener('mousedown', handleMouseDown);
  }
});

// 组件卸载时停止示例轮播
onUnmounted(() => {
  store.stopAutoRefresh();
  if (resizeHandle.value) {
    resizeHandle.value.removeEventListener('mousedown', handleMouseDown);
  }
  document.removeEventListener('mousemove', handleMouseMove);
  document.removeEventListener('mouseup', handleMouseUp);
});

// 拖拽调整大小功能
const handleMouseDown = () => {
  isDragging.value = true;
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
};

const handleMouseMove = (e) => {
  if (!isDragging.value) return;

  const container = document.querySelector('.unified-layout');
  if (!container) return;

  const containerRect = container.getBoundingClientRect();
  const newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
  leftPanelWidth.value = Math.max(20, Math.min(60, newWidth));
};

const handleMouseUp = () => {
  isDragging.value = false;
  document.removeEventListener('mousemove', handleMouseMove);
  document.removeEventListener('mouseup', handleMouseUp);
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
};

</script>

<style lang="less" scoped>
.db-main-container {
  display: flex;
  width: 100%;
}

.ant-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.auto-refresh-control {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 6px;

  span {
    color: var(--gray-700);
    font-weight: 500;
    font-size: 14px;
  }

  .ant-switch {
    &.ant-switch-checked {
      background-color: var(--main-color);
    }
  }
}

/* Unified Layout Styles */
.unified-layout {
  display: flex;
  height: calc(100vh - 54px); /* Adjust based on actual header height */
  gap: 0;

  &.single-column {
    justify-content: center;
    padding: 0 24px 16px;
  }

  .left-panel,
  .right-panel {
    background-color: var(--glass-bg);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .left-panel {
    flex-shrink: 0;
    flex-grow: 1;
    background-color: rgba(15, 23, 42, 0.3);
    padding: 8px;
    border-right: 1px solid rgba(255, 255, 255, 0.1);
  }

  .right-panel {
    flex-grow: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* 当右侧面板可见时，确保它正确分配空间 */
  .right-panel > * {
    flex: 1;
    min-height: 0;
  }

  .resize-handle {
    width: 1px;
    cursor: col-resize;
    background-color: var(--gray-200);
    transition: background-color 0.2s ease;
    position: relative;
    z-index: 10;
    flex-shrink: 0;

    &:hover {
      background-color: var(--main-40);
    }
  }

}


/* Improve the resize handle visibility */
.resize-handle {
  transition: all 0.2s ease;
  opacity: 0.6;

  &:hover {
    opacity: 1;
    background-color: var(--main-color);
  }
}

/* Responsive design for smaller screens */
@media (max-width: 768px) {
  .unified-layout {
    flex-direction: column;
  }

  .unified-layout .left-panel {
    border-right: none;
    border-bottom: 1px solid var(--gray-200);
  }

  .unified-layout .resize-handle {
    width: 100%;
    height: 2px;
    cursor: row-resize;
  }
}


</style>

<style lang="less">
:deep(.full-modal) {
  .ant-modal {
    max-width: 100%;
    top: 0;
    padding-bottom: 0;
    margin: 0;
    padding: 0;
  }

  .ant-modal-content {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 200px);
  }

  .ant-modal-body {
    flex: 1;
  }
}



.maximized-graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  h3 {
    margin: 0;
    color: var(--gray-800);
  }
}


.maximized-graph-content {
  height: calc(100vh - 300px);
  border-radius: 6px;
  overflow: hidden;
}


/* 全局样式作为备用方案 */
.ant-popover .query-params-compact {
  width: 220px;
}

.ant-popover .query-params-compact .params-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80px;
}

.ant-popover .query-params-compact .params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}

.ant-popover .query-params-compact .param-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}

.ant-popover .query-params-compact .param-item label {
  font-weight: 500;
  color: var(--gray-700);
  margin-right: 8px;
}


/* Improve panel transitions */
.panel-section {
  display: flex;
  flex-direction: column;
  border-radius: 4px;
  transition: all 0.3s;
  min-height: 0;

  &.collapsed {
    height: 36px;
    flex: none;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border-bottom: var(--glass-border);
    background-color: rgba(15, 23, 42, 0.45);

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .section-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary);
      margin: 0;
    }

    .panel-actions {
      display: flex;
      gap: 0px;
    }
  }

  .content {
    flex: 1;
    min-height: 0;
  }
}

.query-section,
.graph-section {
  .panel-section();

  .content {
    padding: 8px;
    flex: 1;
    overflow: hidden;
  }
}
</style>
