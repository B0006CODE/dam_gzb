<template>
  <div class="reservoir-map-container">
    <div ref="mapRef" class="map-canvas"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';
import type { ECharts } from 'echarts';
import type { Reservoir } from '@/data/reservoirData';

// Props
interface Props {
  selectedProvince?: string | null;
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
  provinceClick: [province: string];
  reservoirClick: [reservoir: Reservoir];
}>();

// Refs
const mapRef = ref<HTMLElement | null>(null);
let chartInstance: ECharts | null = null;
const reservoirs = ref<Reservoir[]>([]);
const DATA_BASE_URL = import.meta.env.BASE_URL || '/';

// Load reservoir data
const loadData = async () => {
  try {
    const response = await fetch(`${DATA_BASE_URL}data/reservoirs.json`);
    reservoirs.value = await response.json();
  } catch (error) {
    console.error('Failed to load reservoir data:', error);
  }
};

const fetchJson = async (url: string) => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
};

const loadChinaGeoJson = async () => {
  const localUrl = `${DATA_BASE_URL}maps/china_100000_full.json`;
  return fetchJson(localUrl);
};

// Initialize map
const initMap = async () => {
  if (!mapRef.value) return;

  // Create chart instance
  chartInstance = echarts.init(mapRef.value);

  try {
    const chinaGeoJson = await loadChinaGeoJson();
    
    // Register China map
    echarts.registerMap('china', chinaGeoJson);

    // Prepare reservoir scatter data
    const scatterData = reservoirs.value
      .filter((r: Reservoir) => r.coordinates)
      .map((r: Reservoir) => ({
        name: r.name,
        value: [...r.coordinates!, r.capacity || 0],
        reservoir: r
      }));

    // Configure chart options
    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(6, 42, 92, 0.95)',
        borderColor: '#00d4ff',
        borderWidth: 1,
        textStyle: {
          color: '#ffffff',
          fontSize: 13
        },
        formatter: (params: any) => {
          if (params.componentSubType === 'scatter') {
            const reservoir = params.data.reservoir as Reservoir;
            let html = `<div style="padding: 4px;">
              <div style="font-weight: bold; font-size: 14px; margin-bottom: 6px; color: #00d4ff;">
                ${reservoir.name}
              </div>`;
            
            if (reservoir.province) html += `<div>📍 ${reservoir.province}${reservoir.city ? ' · ' + reservoir.city : ''}${reservoir.county ? ' · ' + reservoir.county : ''}</div>`;
            if (reservoir.damType) html += `<div>🏗️ ${reservoir.damType}</div>`;
            if (reservoir.type) html += `<div>📊 ${reservoir.type}</div>`;
            if (reservoir.capacity) html += `<div>💧 库容: ${reservoir.capacity.toLocaleString()} 万方</div>`;
            if (reservoir.basin) html += `<div>🌊 ${reservoir.basin}</div>`;
            
            html += '</div>';
            return html;
          } else if (params.componentSubType === 'map') {
            return `<div style="padding: 4px;">
              <div style="font-weight: bold; font-size: 14px; color: #00d4ff;">
                ${params.name}
              </div>
              <div style="margin-top: 4px;">点击查看水库信息</div>
            </div>`;
          }
          return params.name;
        }
      },
      geo: {
        map: 'china',
        roam: true,
        scaleLimit: {
          min: 1,
          max: 10
        },
        // Fill the viewport more tightly to reduce empty space around the map.
        layoutCenter: ['50%', '52%'],
        layoutSize: '112%',
        zoom: 1.05,
        center: [104.5, 35.8],
        itemStyle: {
          areaColor: 'rgba(6, 42, 92, 0.3)',
          borderColor: '#00d4ff',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: {
            areaColor: 'rgba(0, 212, 255, 0.2)',
            borderColor: '#00d4ff',
            borderWidth: 2,
            shadowColor: 'rgba(0, 212, 255, 0.5)',
            shadowBlur: 20
          },
          label: {
            show: true,
            color: '#ffffff',
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        select: {
          itemStyle: {
            areaColor: 'rgba(0, 212, 255, 0.3)',
            borderColor: '#00d4ff',
            borderWidth: 2
          },
          label: {
            show: true,
            color: '#00d4ff',
            fontSize: 14,
            fontWeight: 'bold'
          }
        }
      },
      series: [
        {
          name: '水库分布',
          type: 'scatter',
          coordinateSystem: 'geo',
          data: scatterData,
          symbolSize: (val: number[]) => {
            // Size based on capacity
            const capacity = val[2] || 0;
            return Math.max(6, Math.min(20, Math.sqrt(capacity) / 10));
          },
          itemStyle: {
            color: '#00d4ff',
            shadowBlur: 10,
            shadowColor: 'rgba(0, 212, 255, 0.5)'
          },
          emphasis: {
            itemStyle: {
              color: '#00ff88',
              borderColor: '#ffffff',
              borderWidth: 2,
              shadowBlur: 20,
              shadowColor: 'rgba(0, 255, 136, 0.8)'
            },
            scale: 1.5
          }
        }
      ]
    };

    chartInstance.setOption(option);

    // Handle clicks
    chartInstance.on('click', (params: any) => {
      if (params.componentType === 'geo') {
        // Province clicked (geo component)
        emit('provinceClick', params.name);
      } else if (params.componentType === 'series' && params.seriesType === 'scatter') {
        // Reservoir clicked (scatter series)
        emit('reservoirClick', params.data.reservoir);
      }
    });

    // Handle window resize
    window.addEventListener('resize', handleResize);
  } catch (error) {
    console.error('Failed to load China map:', error);
  }
};

const handleResize = () => {
  chartInstance?.resize();
};

// Watch for selected province changes
watch(() => props.selectedProvince, (newProvince) => {
  if (!chartInstance) return;
  
  if (newProvince) {
    // Highlight selected province
    chartInstance.dispatchAction({
      type: 'select',
      name: newProvince
    });
  } else {
    // Unselect all
    chartInstance.dispatchAction({
      type: 'unselect'
    });
  }
});

// Lifecycle
onMounted(async () => {
  await loadData();
  initMap();
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  chartInstance?.dispose();
});
</script>

<style scoped>
.reservoir-map-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.map-canvas {
  width: 100%;
  height: 100%;
  min-height: 600px;
}
</style>
