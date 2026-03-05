<template>
  <transition name="slide-in">
    <aside
      v-if="province"
      class="province-info-card"
      role="complementary"
      :aria-label="`${province}水库信息面板`"
    >
      <div class="card-header">
        <div class="header-main">
          <p class="header-kicker">省份概览</p>
          <h2>{{ province }}</h2>
        </div>
        <button @click="$emit('close')" class="close-btn">
          <span>✕</span>
        </button>
      </div>

      <div class="card-content">
        <!-- Statistics Overview -->
        <section class="stats-overview card-section">
          <div class="stat-item stat-item-main">
            <div class="stat-label">水库总数</div>
            <div class="stat-value">{{ stats?.totalCount || 0 }}</div>
          </div>
          <div class="stat-item stat-item-sub">
            <div class="stat-label">坝型种类</div>
            <div class="stat-sub-value">{{ damTypeCount }}</div>
          </div>
          <div class="stat-item stat-item-sub">
            <div class="stat-label">流域种类</div>
            <div class="stat-sub-value">{{ basinCount }}</div>
          </div>
        </section>

        <!-- Dam Types Chart -->
        <section v-if="damTypeDistribution.length > 0" class="chart-section card-section">
          <h3>坝型分布</h3>
          <div class="chart-grid">
            <div 
              v-for="item in damTypeDistribution"
              :key="item.name"
              class="chart-bar-item"
            >
              <div class="bar-head">
                <div class="bar-label">{{ item.name }}</div>
                <div class="bar-ratio">{{ item.ratio.toFixed(1) }}%</div>
              </div>
              <div class="bar-container">
                <div class="bar-track">
                  <div 
                    class="bar-fill"
                    :style="{ width: `${item.ratio}%` }"
                  ></div>
                </div>
                <span class="bar-value">{{ item.count }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Basin Distribution -->
        <section v-if="basinDistribution.length > 0" class="chart-section card-section">
          <h3>流域分布</h3>
          <div class="chart-grid">
            <div 
              v-for="item in basinDistribution"
              :key="item.name"
              class="chart-bar-item"
            >
              <div class="bar-head">
                <div class="bar-label">{{ item.name }}</div>
                <div class="bar-ratio">{{ item.ratio.toFixed(1) }}%</div>
              </div>
              <div class="bar-container">
                <div class="bar-track">
                  <div 
                    class="bar-fill basin"
                    :style="{ width: `${item.ratio}%` }"
                  ></div>
                </div>
                <span class="bar-value">{{ item.count }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Reservoir List -->
        <section class="reservoir-list-section card-section">
          <h3>水库列表 ({{ provinceReservoirs.length }})</h3>
          <div class="reservoir-list">
            <div 
              v-for="reservoir in provinceReservoirs" 
              :key="reservoir.id"
              class="reservoir-item"
              @click="$emit('reservoirClick', reservoir)"
            >
              <div class="reservoir-head">
                <div class="reservoir-name">{{ reservoir.name }}</div>
                <div v-if="reservoir.city || reservoir.county" class="reservoir-location">
                  {{ reservoir.city || reservoir.county }}<span v-if="reservoir.city && reservoir.county"> · {{ reservoir.county }}</span>
                </div>
              </div>
              <div class="reservoir-meta">
                <span v-if="reservoir.damType" class="meta-tag">{{ reservoir.damType }}</span>
                <span v-if="reservoir.type" class="meta-tag">{{ reservoir.type }}</span>
                <span v-if="reservoir.capacity" class="meta-tag">
                  {{ reservoir.capacity.toLocaleString() }} 万方
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </aside>
  </transition>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { getReservoirsByProvince, loadProvinceStats, loadReservoirs } from '@/data/reservoirData';
import type { Reservoir, ProvinceStatsMap } from '@/data/reservoirData';

// Props
interface Props {
  province: string | null;
}

const props = defineProps<Props>();

// Emits
defineEmits<{
  close: [];
  reservoirClick: [reservoir: Reservoir];
}>();

// State
const provinceStatsData = ref<ProvinceStatsMap>({});
const reservoirsData = ref<Reservoir[]>([]);

// Load data
const loadData = async () => {
  try {
    [provinceStatsData.value, reservoirsData.value] = await Promise.all([
      loadProvinceStats(),
      loadReservoirs()
    ]);
  } catch (error) {
    console.error('Failed to load data:', error);
  }
};

loadData();

// Computed
const stats = computed(() => {
  return props.province ? provinceStatsData.value[props.province] : null;
});

const provinceReservoirs = computed(() => {
  if (!props.province) return [];
  return [...getReservoirsByProvince(reservoirsData.value, props.province)].sort((a, b) => {
    return (b.capacity || 0) - (a.capacity || 0);
  });
});

interface DistributionItem {
  name: string;
  count: number;
  ratio: number;
}

const toDistribution = (source?: Record<string, number>): DistributionItem[] => {
  if (!source || !stats.value?.totalCount) return [];
  const total = stats.value.totalCount;

  return Object.entries(source)
    .map(([name, count]) => ({
      name,
      count,
      ratio: total > 0 ? (count / total) * 100 : 0
    }))
    .sort((a, b) => b.count - a.count);
};

const damTypeDistribution = computed(() => toDistribution(stats.value?.damTypes));
const basinDistribution = computed(() => toDistribution(stats.value?.basins));

const damTypeCount = computed(() => damTypeDistribution.value.length);
const basinCount = computed(() => basinDistribution.value.length);
</script>

<style scoped>
.province-info-card {
  position: absolute;
  top: 16px;
  right: 16px;
  bottom: 16px;
  width: min(420px, calc(100vw - 32px));
  background: rgba(6, 42, 92, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 14px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 18px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(0, 136, 255, 0.1));
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  flex-shrink: 0;
}

.header-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-kicker {
  margin: 0;
  font-size: 11px;
  color: #8ab4f8;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #00d4ff;
  text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
}

.close-btn {
  background: transparent;
  border: 1px solid rgba(0, 212, 255, 0.3);
  color: #00d4ff;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  font-size: 18px;
}

.close-btn:hover {
  background: rgba(0, 212, 255, 0.1);
  border-color: #00d4ff;
  transform: scale(1.1);
}

.card-content {
  padding: 14px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-content::-webkit-scrollbar {
  width: 6px;
}

.card-content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.card-content::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 255, 0.3);
  border-radius: 3px;
}

.card-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 212, 255, 0.5);
}

.card-section {
  padding: 12px;
  background: rgba(2, 16, 35, 0.45);
  border: 1px solid rgba(0, 212, 255, 0.16);
  border-radius: 10px;
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
}

.stat-item-main {
  grid-column: 1 / -1;
}

.stat-label {
  font-size: 12px;
  color: #8ab4f8;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 34px;
  font-weight: 700;
  color: #00d4ff;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
}

.stat-sub-value {
  font-size: 20px;
  font-weight: 700;
  color: #c6f1ff;
}

.chart-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chart-section h3 {
  font-size: 16px;
  color: #ffffff;
  margin: 0;
  font-weight: 600;
}

.chart-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chart-bar-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.bar-label {
  font-size: 12px;
  color: #8ab4f8;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-ratio {
  font-size: 11px;
  color: #c6f1ff;
  flex-shrink: 0;
}

.bar-container {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
}

.bar-track {
  position: relative;
  height: 10px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 999px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00d4ff, #0088ff);
  border-radius: 999px;
  transition: width 0.6s ease;
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
  min-width: 2px;
}

.bar-fill.basin {
  background: linear-gradient(90deg, #00ff88, #00cc66);
  box-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
}

.bar-value {
  font-size: 12px;
  font-weight: 600;
  color: #ffffff;
  min-width: 28px;
  text-align: right;
}

.reservoir-list-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reservoir-list-section h3 {
  font-size: 16px;
  color: #ffffff;
  margin: 0;
  font-weight: 600;
}

.reservoir-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reservoir-item {
  padding: 10px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.reservoir-item:hover {
  background: rgba(0, 212, 255, 0.1);
  border-color: #00d4ff;
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(0, 212, 255, 0.3);
}

.reservoir-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.reservoir-name {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 6px;
  flex: 1;
}

.reservoir-location {
  font-size: 11px;
  color: #8ab4f8;
  white-space: nowrap;
  flex-shrink: 0;
}

.reservoir-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-tag {
  font-size: 11px;
  padding: 3px 8px;
  background: rgba(0, 212, 255, 0.15);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 999px;
  color: #8ab4f8;
}

/* Animations */
.slide-in-enter-active,
.slide-in-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-in-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.slide-in-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

@media (max-width: 1024px) {
  .province-info-card {
    width: min(360px, calc(100vw - 24px));
    top: 12px;
    right: 12px;
    bottom: 12px;
  }
}

@media (max-width: 768px) {
  .province-info-card {
    top: auto;
    right: 10px;
    left: 10px;
    bottom: 10px;
    width: auto;
    max-height: 72vh;
    border-radius: 14px;
  }

  .card-header h2 {
    font-size: 20px;
  }

  .card-content {
    padding: 12px;
    gap: 10px;
  }

  .stats-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .slide-in-enter-from,
  .slide-in-leave-to {
    transform: translateY(100%);
  }
}
</style>
