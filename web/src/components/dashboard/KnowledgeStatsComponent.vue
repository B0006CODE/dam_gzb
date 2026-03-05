<template>
  <a-card class="knowledge-stats-card" :loading="loading">
    <template #title>
      <div class="card-title">
        <span>📚 知识库统计</span>
      </div>
    </template>

    <!-- 核心数据统计 -->
    <div class="stats-overview">
      <a-row :gutter="16">
        <a-col :span="8">
          <a-statistic
            title="知识库总数"
            :value="knowledgeStats?.total_databases || 0"
            :value-style="{ color: '#06b6d4', fontWeight: 'bold', textShadow: '0 0 10px rgba(6, 182, 212, 0.3)' }"
            suffix="个"
            class="neon-stat"
          />
        </a-col>
        <a-col :span="8">
          <a-statistic
            title="文件总数"
            :value="knowledgeStats?.total_files || 0"
            :value-style="{ color: '#10b981', fontWeight: 'bold', textShadow: '0 0 10px rgba(16, 185, 129, 0.3)' }"
            suffix="个"
            class="neon-stat"
          />
        </a-col>
        <a-col :span="8">
          <a-statistic
            title="存储容量"
            :value="formattedStorageSize"
            :value-style="{ color: '#f59e0b', fontWeight: 'bold', textShadow: '0 0 10px rgba(245, 158, 11, 0.3)' }"
            class="neon-stat"
          />
        </a-col>
      </a-row>
    </div>

    <a-divider />

    <!-- 图表区域：拆分为两行 -->
    <a-row :gutter="24" style="margin-bottom: 16px;">
      <!-- 数据库类型分布 -->
      <a-col :span="24">
        <div class="chart-container">
          <div class="chart-header">
            <h4>类型分布</h4>
            <div class="legend" v-if="dbTypeLegend.length">
              <div class="legend-item" v-for="(item, idx) in dbTypeLegend" :key="item.name">
                <span class="legend-color" :style="{ backgroundColor: getLegendColorByIndex(idx) }"></span>
                <span class="legend-label">{{ item.name }}</span>
              </div>
            </div>
          </div>
          <div ref="dbTypeChartRef" class="chart chart--thin"></div>
        </div>
      </a-col>
    </a-row>

    <a-row :gutter="24">
      <!-- 文件类型分布 -->
      <a-col :span="24">
        <div class="chart-container">
          <h4>文件类型分布</h4>
          <div ref="fileTypeChartRef" class="chart"></div>
        </div>
      </a-col>
    </a-row>

    <!-- 详细统计信息 -->
    <!-- <a-divider />
    <a-row :gutter="16">
      <a-col :span="8">
        <a-statistic
          title="平均每库文件数"
          :value="averageFilesPerDatabase"
          suffix="个"
          :precision="1"
        />
      </a-col>
      <a-col :span="8">
        <a-statistic
          title="平均每文件节点数"
          :value="averageNodesPerFile"
          suffix="个"
          :precision="1"
        />
      </a-col>
      <a-col :span="8">
        <a-statistic
          title="平均节点大小"
          :value="averageNodeSize"
          suffix="KB"
          :precision="2"
        />
      </a-col>
    </a-row> -->
  </a-card>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { getColorByIndex, getChartColor, getColorPalette } from '@/utils/chartColors'

// Props
const props = defineProps({
  knowledgeStats: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

// Chart refs
const dbTypeChartRef = ref(null)
const fileTypeChartRef = ref(null)
let dbTypeChart = null
let fileTypeChart = null

// 计算属性
const formattedStorageSize = computed(() => {
  const size = props.knowledgeStats?.total_storage_size || 0
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`
  if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(2)} MB`
  return `${(size / (1024 * 1024 * 1024)).toFixed(2)} GB`
})

// const averageFilesPerDatabase = computed(() => {
//   const databases = props.knowledgeStats?.total_databases || 0
//   const files = props.knowledgeStats?.total_files || 0
//   return databases > 0 ? files / databases : 0
// })

// const averageNodeSize = computed(() => {
//   const nodes = props.knowledgeStats?.total_nodes || 0
//   const size = props.knowledgeStats?.total_storage_size || 0
//   return nodes > 0 ? size / (nodes * 1024) : 0 // 转换为KB
// })

// 使用统一的调色盘
const getLegendColorByIndex = (index) => getColorByIndex(index)


// 初始化数据库类型分布图 - 横向分段条
const dbTypeLegend = ref([])
const initDbTypeChart = () => {
  if (!dbTypeChartRef.value || !props.knowledgeStats?.databases_by_type) return

  const entries = Object.entries(props.knowledgeStats.databases_by_type)
    .map(([type, count]) => ({ name: type || '未知', value: count }))
    .filter(item => item.value > 0)

  // update legend data
  dbTypeLegend.value = entries

  if (!dbTypeChart) {
    dbTypeChart = echarts.init(dbTypeChartRef.value)
  }

  const total = entries.reduce((sum, item) => sum + item.value, 0)

  // Build stacked bar series, but render with neutral color and separators
  const series = entries.map((item, idx) => ({
    name: item.name,
    type: 'bar',
    stack: 'total',
    barWidth: 28,
    data: [item.value],
    itemStyle: {
      color: getLegendColorByIndex(idx),
      borderColor: '#ffffff',
      borderWidth: 2,
      borderJoin: 'miter'
    },
    emphasis: {
      itemStyle: {
        color: getLegendColorByIndex(idx)
      }
    }
  }))

  const option = {
    animation: false,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: 'rgba(6, 182, 212, 0.3)',
      borderWidth: 1,
      textStyle: { color: '#fff' },
      formatter: (params) => {
        const value = params.value || 0
        return `<div style="color:#fff;font-weight:600">${params.seriesName}</div><div style="color:rgba(255,255,255,0.8)">${value}/${total}</div>`
      }
    },
    grid: { left: 0, right: 0, top: 10, bottom: 10, containLabel: false },
    xAxis: {
      type: 'value',
      show: false,
      max: total > 0 ? total : undefined
    },
    yAxis: {
      type: 'category',
      show: false,
      data: ['all']
    },
    series: series.map(s => ({
      ...s,
      itemStyle: {
        ...s.itemStyle,
        borderColor: 'rgba(15, 23, 42, 0.8)',
        shadowBlur: 5,
        shadowColor: s.itemStyle.color
      }
    }))
  }

  dbTypeChart.setOption(option, true)
}

// 初始化文件类型分布图
const initFileTypeChart = () => {
  if (!fileTypeChartRef.value) return

  fileTypeChart = echarts.init(fileTypeChartRef.value)

  // 检查是否有文件类型数据 - 兼容旧字段名和新字段名
  const fileTypesData = props.knowledgeStats?.files_by_type || props.knowledgeStats?.file_type_distribution || {}
  if (Object.keys(fileTypesData).length > 0) {
    const data = Object.entries(fileTypesData).map(([type, count]) => ({
      name: type || '未知',
      value: count
    }))

    const option = {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        borderColor: 'rgba(6, 182, 212, 0.3)',
        borderWidth: 1,
        textStyle: {
          color: '#fff'
        },
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      series: [{
        name: '文件类型',
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: 'rgba(15, 23, 42, 0.8)',
          borderWidth: 2,
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        },
        label: {
          show: true,
          formatter: '{b}: {c}',
          fontSize: 12,
          color: 'rgba(255, 255, 255, 0.8)'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '14',
            fontWeight: 'bold',
            color: '#fff',
            textShadow: '0 0 10px rgba(255, 255, 255, 0.5)'
          },
          itemStyle: {
            shadowBlur: 20,
            shadowOffsetX: 0,
            shadowColor: 'rgba(6, 182, 212, 0.5)'
          }
        },
        labelLine: {
          show: true,
          length: 10,
          length2: 15,
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.3)'
          }
        },
        data: data,
        color: getColorPalette()
      }]
    }

    fileTypeChart.setOption(option)
  } else {
    // 如果没有文件类型数据，显示一个占位图表
    const option = {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e8e8e8',
        borderWidth: 1,
        textStyle: {
          color: '#666'
        },
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      series: [{
        name: '文件类型',
        type: 'pie',
        radius: ['25%', '55%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c}',
          fontSize: 12
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '14',
            fontWeight: 'bold',
            color: '#333'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        labelLine: {
          show: true,
          length: 10,
          length2: 15
        },
        data: [
          { name: '暂无数据', value: 1 }
        ],
        color: ['#e1f6fb']
      }]
    }

    fileTypeChart.setOption(option)
  }
}

// 更新图表
const updateCharts = () => {
  nextTick(() => {
    initDbTypeChart()
    initFileTypeChart()
  })
}

// 监听数据变化
watch(() => props.knowledgeStats, () => {
  updateCharts()
}, { deep: true })

// 窗口大小变化时重新调整图表
const handleResize = () => {
  if (dbTypeChart) dbTypeChart.resize()
  if (fileTypeChart) fileTypeChart.resize()
}

onMounted(() => {
  updateCharts()
  window.addEventListener('resize', handleResize)
})

// 组件卸载时清理
const cleanup = () => {
  window.removeEventListener('resize', handleResize)
  if (dbTypeChart) {
    dbTypeChart.dispose()
    dbTypeChart = null
  }
  if (fileTypeChart) {
    fileTypeChart.dispose()
    fileTypeChart = null
  }
}

// 导出清理函数供父组件调用
defineExpose({
  cleanup
})
</script>

<style scoped lang="less">
// KnowledgeStatsComponent 特有的样式

.chart-container {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);

  .chart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    h4 {
      margin: 0;
      color: #fff;
      font-size: 14px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;

      &::before {
        content: '';
        display: block;
        width: 4px;
        height: 14px;
        background: #06b6d4;
        border-radius: 2px;
        box-shadow: 0 0 8px #06b6d4;
      }
    }

    .legend {
      display: flex;
      gap: 12px;
      align-items: center;

      .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
      }

      .legend-color {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        box-shadow: 0 0 5px currentColor;
      }
    }
  }

  h4 {
    margin: 0 0 12px 0;
    color: #fff;
    font-size: 14px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;

    &::before {
      content: '';
      display: block;
      width: 4px;
      height: 14px;
      background: #06b6d4;
      border-radius: 2px;
      box-shadow: 0 0 8px #06b6d4;
    }
  }

  .chart {
    height: 220px;
    width: 100%;
  }

  .chart--thin {
    height: 80px;
  }
}

:deep(.ant-statistic-title) {
  color: rgba(255, 255, 255, 0.5) !important;
  font-size: 12px !important;
  margin-bottom: 4px !important;
}

:deep(.ant-statistic-content-suffix) {
  color: rgba(255, 255, 255, 0.4) !important;
  font-size: 12px !important;
}

:deep(.ant-divider) {
  border-top-color: rgba(255, 255, 255, 0.1) !important;
  margin: 16px 0 !important;
}
</style>