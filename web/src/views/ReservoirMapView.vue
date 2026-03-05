<template>
  <div class="reservoir-map-view">
    <div class="page-header">
      <h1>🗺️ 水库分布图</h1>
      <div class="header-stats">
        <div class="stat-badge">
          <span class="stat-label">总水库数</span>
          <span class="stat-value">1,512</span>
        </div>
        <div class="stat-badge">
          <span class="stat-label">覆盖省份</span>
          <span class="stat-value">29</span>
        </div>
      </div>
    </div>

    <div class="map-wrapper">
      <ReservoirMapComponent
        :selected-province="selectedProvince"
        @province-click="handleProvinceClick"
        @reservoir-click="handleReservoirClick"
      />

      <ProvinceInfoCard
        :province="selectedProvince"
        @close="selectedProvince = null"
        @reservoir-click="handleReservoirClick"
      />
    </div>

    <ReservoirDetailModal
      :reservoir="selectedReservoir"
      @close="selectedReservoir = null"
    />

    <!-- Legend -->
    <div class="map-legend">
      <h4>图例</h4>
      <div class="legend-items">
        <div class="legend-item">
          <div class="legend-symbol province"></div>
          <span>省份边界</span>
        </div>
        <div class="legend-item">
          <div class="legend-symbol reservoir"></div>
          <span>水库位置</span>
        </div>
      </div>
      <div class="legend-note">
        💡 点击省份查看统计信息<br/>
        💡 点击水库查看详细信息
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import ReservoirMapComponent from '@/components/ReservoirMapComponent.vue';
import ProvinceInfoCard from '@/components/ProvinceInfoCard.vue';
import ReservoirDetailModal from '@/components/ReservoirDetailModal.vue';
import type { Reservoir } from '@/data/reservoirData';
import { loadProvinceStats } from '@/data/reservoirData';

// State
const selectedProvince = ref<string | null>(null);
const selectedReservoir = ref<Reservoir | null>(null);
const provinceStats = ref<any>({});

// Load province stats
loadProvinceStats().then(stats => {
  provinceStats.value = stats;
});

// Methods
const normalizeProvinceName = (name: string) => {
  return name.replace(/(?:省|市|自治区|壮族自治区|回族自治区|维吾尔自治区|特别行政区)$/, '');
};

const handleProvinceClick = (province: string) => {
  const normalizedProvince = normalizeProvinceName(province);
  
  // Only show info card if province has reservoir data
  if (provinceStats.value[normalizedProvince]) {
    selectedProvince.value = normalizedProvince;
  }
};

const handleReservoirClick = (reservoir: Reservoir) => {
  selectedReservoir.value = reservoir;
};
</script>

<style scoped>
.reservoir-map-view {
  width: 100%;
  height: 100vh;
  background: linear-gradient(135deg, #0a1628 0%, #062a5c 50%, #0a1628 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  padding: 16px 22px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-stats {
  display: flex;
  gap: 10px;
}

.stat-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 14px;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 8px;
  min-width: 88px;
}

.stat-label {
  font-size: 12px;
  color: #8ab4f8;
  margin-bottom: 2px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #00d4ff;
  text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
}

.map-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.map-legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  background: rgba(6, 42, 92, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 12px;
  padding: 12px;
  min-width: 180px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  z-index: 50;
}

.map-legend h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  color: #00d4ff;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #ffffff;
}

.legend-symbol {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  flex-shrink: 0;
}

.legend-symbol.province {
  background: rgba(0, 212, 255, 0.3);
  border: 1px solid #00d4ff;
}

.legend-symbol.reservoir {
  background: #00d4ff;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
}

.legend-note {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 212, 255, 0.2);
  font-size: 11px;
  color: #8ab4f8;
  line-height: 1.5;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }

  .page-header h1 {
    font-size: 22px;
  }

  .header-stats {
    width: 100%;
    justify-content: space-around;
  }

  .map-legend {
    bottom: 8px;
    left: 8px;
    right: 8px;
    min-width: auto;
  }
}
</style>
