<template>
  <div class="grid-item call-stats">
    <a-card class="dashboard-card call-stats-section" title="调用统计" :loading="loading">
      <template #extra>
        <div class="simple-controls">
          <div class="simple-toggle-group">
            <!-- <span class="simple-toggle-label">时间</span> -->
            <span
              v-for="opt in timeRangeOptions"
              :key="opt.value"
              class="simple-toggle"
              :class="{ active: callTimeRange === opt.value }"
              @click="switchTimeRange(opt.value)"
            >{{ opt.label }}</span>
          </div>
          <div class="divider"></div>
          <div class="simple-toggle-group">
            <!-- <span class="simple-toggle-label">类型</span> -->
            <span
              v-for="opt in dataTypeOptions"
              :key="opt.value"
              class="simple-toggle"
              :class="{ active: callDataType === opt.value }"
              @click="switchDataType(opt.value)"
            >{{ opt.label }}</span>
          </div>
          <!-- <div class="subtitle">总计：{{ callStatsData?.total_count || 0 }}</div> -->
        </div>
      </template>

      <div class="call-stats-container">
        <div class="chart-container">
          <div ref="callStatsChartRef" class="chart"></div>
        </div>
      </div>
    </a-card>
  </div>

</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, defineExpose, watch } from 'vue'
import * as echarts from 'echarts'
import { dashboardApi } from '@/apis/dashboard_api'
import { getColorByIndex, truncateLegend } from '@/utils/chartColors'

const props = defineProps({
  loading: { type: Boolean, default: false },
})

// state
const callStatsData = ref(null)
const callStatsLoading = ref(false)
const callTimeRange = ref('7days')
const callDataType = ref('models')
const timeRangeOptions = [
  { value: '7hours', label: '近7小时' },
  { value: '7days', label: '近7天' },
  { value: '7weeks', label: '近7周' },
]
const dataTypeOptions = [
  { value: 'models', label: '模型调用' },
  { value: 'knowledge_base', label: '知识库调用' },
  { value: 'knowledge_graph', label: '知识图谱调用' },
]

const switchTimeRange = (val) => {
  if (callTimeRange.value === val) return
  callTimeRange.value = val
  loadCallStats()
}

const switchDataType = (val) => {
  if (callDataType.value === val) return
  callDataType.value = val
  loadCallStats()
}
const callStatsChartRef = ref(null)
let callStatsChart = null
let retryTimer = null
const retryCount = ref(0)
const maxRetry = 20

const loadCallStats = async () => {
  callStatsLoading.value = true
  try {
    const response = await dashboardApi.getCallTimeseries(callDataType.value, callTimeRange.value)
    callStatsData.value = response
    await nextTick()
    renderCallStatsChart()
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('加载调用统计数据失败:', error)
  } finally {
    callStatsLoading.value = false
  }
}

const renderCallStatsChart = () => {
  const container = callStatsChartRef.value
  if (!container || !callStatsData.value) return

  // 若父卡片仍在 loading，等待 loading 结束
  if (props.loading) {
    scheduleRetry()
    return
  }

  const { clientWidth, clientHeight } = container
  if (!clientWidth || !clientHeight) {
    scheduleRetry()
    return
  }

  if (retryTimer) {
    clearTimeout(retryTimer)
    retryTimer = null
  }
  retryCount.value = 0

  if (callStatsChart) {
    callStatsChart.dispose()
  }


  callStatsChart = echarts.init(container)

  const data = callStatsData.value.data || []
  const categories = callStatsData.value.categories || []

  const xAxisData = data.map(item => {
    const date = item.date
    if (callTimeRange.value === '7hours') {
      return date.split(' ')[1]
    } else if (callTimeRange.value === '7weeks') {
      return `第${date.split('-')[1]}周`
    } else {
      return date.split('-').slice(1).join('-')
    }
  })

  const series = categories.map((category, index) => ({
    name: category === 'None' ? '未知模型' : category,
    type: 'bar',
    stack: 'total',
    emphasis: { focus: 'series' },
    data: data.map(item => item.data[category] || 0),
    itemStyle: {
      color: getColorByIndex(index),
      borderRadius: 0,
    }
  }))

  const option = {
    backgroundColor: 'transparent',
    grid: {
      left: '3%',
      right: '4%',
      top: '15%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisTick: { show: false },
      axisLabel: { color: 'rgba(255, 255, 255, 0.6)', fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: 'rgba(255, 255, 255, 0.6)', fontSize: 12 },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: 'rgba(6, 182, 212, 0.3)',
      borderWidth: 1,
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: (params) => {
        let total = 0
        let result = `<div style="margin-bottom: 8px; font-weight: 600; color: #fff;">${params[0].name}</div>`
        params.forEach(param => {
          total += param.value
          const truncatedName = truncateLegend(param.seriesName)
          result += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background-color:${param.color};box-shadow: 0 0 5px ${param.color}"></span>
            <span style="color: rgba(255,255,255,0.8)">${truncatedName}:</span>
            <span style="color: #fff; font-weight: 500; margin-left: auto;">${param.value}</span>
          </div>`
        })
        const labelMap = { models: '模型调用', knowledge_base: '知识库调用', knowledge_graph: '知识图谱调用' }
        return `<div style="font-weight:bold;margin-bottom:8px;color:#06b6d4">${labelMap[callDataType.value]}</div>${result}<div style="margin-top:8px;border-top:1px solid rgba(255,255,255,0.1);padding-top:8px;display:flex;justify-content:space-between;color:#fff;font-weight:600"><span>总计</span><span>${total}</span></div>`
      }
    },
    legend: {
      data: categories.map(cat => (cat === 'None' ? '未知模型' : cat)),
      bottom: 0,
      textStyle: { color: 'rgba(255, 255, 255, 0.6)', fontSize: 12 },
      itemWidth: 12,
      itemHeight: 12,
      formatter: (name) => truncateLegend(name),
      pageIconColor: '#06b6d4',
      pageTextStyle: { color: '#fff' }
    },
    series: series.map(s => ({
      ...s,
      itemStyle: {
        ...s.itemStyle,
        shadowBlur: 10,
        shadowColor: s.itemStyle.color
      }
    })),
  }

  callStatsChart.setOption(option)

  window.addEventListener('resize', handleResize, resizeListenerOptions)
}

const scheduleRetry = () => {
  if (retryCount.value >= maxRetry) return
  if (retryTimer) clearTimeout(retryTimer)
  retryTimer = setTimeout(() => {
    retryCount.value += 1
    renderCallStatsChart()
  }, 100)
}

const handleResize = () => {
  if (callStatsChart) callStatsChart.resize()
}

const resizeListenerOptions = { passive: true }

const cleanup = () => {
  window.removeEventListener('resize', handleResize, resizeListenerOptions)
  if (retryTimer) {
    clearTimeout(retryTimer)
    retryTimer = null
  }
  retryCount.value = 0
  if (callStatsChart) {
    callStatsChart.dispose()
    callStatsChart = null
  }
}

defineExpose({ cleanup })

onMounted(() => {
  loadCallStats()
})

watch(() => props.loading, (now) => {
  if (!now) {
    if (callStatsData.value) {
      nextTick().then(() => renderCallStatsChart())
    }
  }
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped lang="less">

/* 复用 dashboard.css 样式：此处仅做最小覆盖以避免重复 */
/* 复用 dashboard.css 样式：此处仅做最小覆盖以避免重复 */
.call-stats-section {
  background-color: transparent;
  height: 100%;
  display: flex;
  flex-direction: column;

  :deep(.ant-card-head-wrapper) {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: nowrap;
  }

  :deep(.ant-card-head-title) {
    flex: 0 0 auto;
    min-width: 72px;
    white-space: nowrap;
    overflow: visible;
    text-overflow: clip;
    padding-right: 0;
  }

  :deep(.ant-card-extra) {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }
}

:deep(.ant-card-body) {
  flex: 1;
  display: flex;
  padding: 16px;
  overflow-x: hidden;
}

.call-stats-container {
  height: 100%;
  display: flex;
  flex: 1;
}

.call-stats .chart-container {
  height: 100%;
  flex: 1;
  padding: 0;
}

.call-stats .chart {
  height: 100% !important;
  width: 100%;
  padding: 0;
  border: none;
  background-color: transparent;
}

.simple-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  width: 100%;
  gap: 8px;
}

.simple-toggle-group {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.05);
  padding: 2px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.simple-toggle {
  padding: 3px 8px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
  user-select: none;
  white-space: nowrap;
}

.simple-toggle:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.simple-toggle.active {
  background-color: rgba(6, 182, 212, 0.2);
  color: #06b6d4;
  font-weight: 500;
  box-shadow: 0 0 10px rgba(6, 182, 212, 0.1);
}

.divider {
  width: 1px;
  height: 16px;
  background-color: rgba(255, 255, 255, 0.1);
}

@media (max-width: 1200px) {
  .simple-controls {
    gap: 6px;
  }

  .simple-toggle {
    padding: 2px 6px;
    font-size: 10px;
  }
}

@media (max-width: 900px) {
  .divider {
    display: none;
  }

  .simple-controls {
    gap: 6px;
  }
}
</style>


