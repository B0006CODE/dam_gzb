<template>
  <a-modal
    v-model:open="visible"
    :title="file?.filename || '文件详情'"
    width="1200px"
    :footer="null"
    wrap-class-name="file-detail"
    @after-open-change="afterOpenChange"
    :bodyStyle="{ height: '80vh', padding: '0', background: 'transparent' }"
  >
    <div class="file-detail-content" v-if="file">
      <div class="file-content-section" v-if="file.lines && file.lines.length > 0">
        <MarkdownContentViewer :chunks="file.lines" />
      </div>

      <div v-else-if="loading" class="loading-container">
        <a-spin />
      </div>

      <div v-else class="empty-content">
        <p>暂无文件内容</p>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { computed } from 'vue';
import { useDatabaseStore } from '@/stores/database';

const store = useDatabaseStore();

const visible = computed({
  get: () => store.state.fileDetailModalVisible,
  set: (value) => store.state.fileDetailModalVisible = value
});

const file = computed(() => store.selectedFile);
const loading = computed(() => store.state.fileDetailLoading);

const afterOpenChange = (open) => {
  if (!open) {
    store.selectedFile = null;
  }
};

// 导入工具函数
import { getStatusText, formatStandardTime } from '@/utils/file_utils';
import MarkdownContentViewer from './MarkdownContentViewer.vue';
</script>

<style scoped>
.file-detail-content {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.file-content-section h4 {
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 600;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.empty-content {
  text-align: center;
  padding: 40px 0;
  color: #999;
}
</style>

<style lang="less">
.file-detail {
  .ant-modal {
    top: 20px;
    padding-bottom: 0;
  }

  .ant-modal-content {
    background: var(--bg-elevated) !important;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    padding: 0;
    
    .ant-modal-header {
      background: transparent;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      
      .ant-modal-title {
        color: #e2e8f0;
      }
    }
    
    .ant-modal-close {
      color: #94a3b8;
      
      &:hover {
        color: #e2e8f0;
      }
    }
  }
}
</style>