<template>
  <transition name="modal">
    <div v-if="reservoir" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-container" @click.stop>
        <div class="modal-header">
          <h2>{{ reservoir.name }}</h2>
          <button @click="$emit('close')" class="close-btn">
            <span>✕</span>
          </button>
        </div>

        <div class="modal-content">
          <div class="info-grid">
            <!-- Location Information -->
            <div class="info-section">
              <h3>📍 位置信息</h3>
              <div class="info-items">
                <div v-if="reservoir.province" class="info-item">
                  <span class="label">省份</span>
                  <span class="value">{{ reservoir.province }}</span>
                </div>
                <div v-if="reservoir.city" class="info-item">
                  <span class="label">城市</span>
                  <span class="value">{{ reservoir.city }}</span>
                </div>
                <div v-if="reservoir.county" class="info-item">
                  <span class="label">县区</span>
                  <span class="value">{{ reservoir.county }}</span>
                </div>
              </div>
            </div>

            <!-- Basic Information -->
            <div class="info-section">
              <h3>ℹ️ 基本信息</h3>
              <div class="info-items">
                <div v-if="reservoir.type" class="info-item">
                  <span class="label">水库型别</span>
                  <span class="value">{{ reservoir.type }}</span>
                </div>
                <div v-if="reservoir.basin" class="info-item">
                  <span class="label">所在流域</span>
                  <span class="value">{{ reservoir.basin }}</span>
                </div>
              </div>
            </div>

            <!-- Technical Information -->
            <div class="info-section">
              <h3>🏗️ 技术参数</h3>
              <div class="info-items">
                <div v-if="reservoir.damType" class="info-item">
                  <span class="label">主坝坝型</span>
                  <span class="value highlight">{{ reservoir.damType }}</span>
                </div>
                <div v-if="reservoir.capacity" class="info-item">
                  <span class="label">总库容</span>
                  <span class="value highlight">{{ reservoir.capacity.toLocaleString() }} 万方</span>
                </div>
                <div v-if="reservoir.maxHeight" class="info-item">
                  <span class="label">最大坝高</span>
                  <span class="value highlight">{{ reservoir.maxHeight }} 米</span>
                </div>
              </div>
            </div>

            <!-- Coordinates (if available) -->
            <div v-if="reservoir.coordinates" class="info-section">
              <h3>🗺️ 坐标信息</h3>
              <div class="info-items">
                <div class="info-item">
                  <span class="label">经度</span>
                  <span class="value">{{ reservoir.coordinates[0].toFixed(4) }}°</span>
                </div>
                <div class="info-item">
                  <span class="label">纬度</span>
                  <span class="value">{{ reservoir.coordinates[1].toFixed(4) }}°</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="$emit('close')" class="btn-primary">关闭</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import type { Reservoir } from '@/data/reservoirData';

// Props
interface Props {
  reservoir: Reservoir | null;
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
  close: [];
}>();

// Methods
const handleOverlayClick = () => {
  emit('close');
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-container {
  background: rgba(6, 42, 92, 0.98);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 28px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.15), rgba(0, 136, 255, 0.15));
  border-bottom: 1px solid rgba(0, 212, 255, 0.3);
}

.modal-header h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #00d4ff;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.6);
}

.close-btn {
  background: transparent;
  border: 1px solid rgba(0, 212, 255, 0.3);
  color: #00d4ff;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  font-size: 20px;
}

.close-btn:hover {
  background: rgba(0, 212, 255, 0.2);
  border-color: #00d4ff;
  transform: scale(1.1) rotate(90deg);
}

.modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 28px;
}

.modal-content::-webkit-scrollbar {
  width: 8px;
}

.modal-content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 255, 0.3);
  border-radius: 4px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 212, 255, 0.5);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.info-section {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s ease;
}

.info-section:hover {
  border-color: rgba(0, 212, 255, 0.4);
  box-shadow: 0 4px 16px rgba(0, 212, 255, 0.2);
}

.info-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.info-item:last-child {
  border-bottom: none;
}

.label {
  font-size: 13px;
  color: #8ab4f8;
  font-weight: 500;
}

.value {
  font-size: 14px;
  color: #ffffff;
  font-weight: 600;
  text-align: right;
}

.value.highlight {
  color: #00d4ff;
  text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

.modal-footer {
  padding: 20px 28px;
  background: rgba(0, 0, 0, 0.2);
  border-top: 1px solid rgba(0, 212, 255, 0.2);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-primary {
  padding: 10px 24px;
  background: linear-gradient(135deg, #00d4ff, #0088ff);
  border: none;
  border-radius: 8px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 212, 255, 0.5);
}

/* Animations */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.9) translateY(-20px);
}

/* Responsive */
@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .modal-header h2 {
    font-size: 20px;
  }

  .modal-content {
    padding: 20px;
  }
}
</style>
