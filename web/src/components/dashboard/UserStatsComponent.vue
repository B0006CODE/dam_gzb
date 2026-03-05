<template>
  <a-card title="用户活跃度分析" :loading="loading" class="dashboard-card">
    <!-- 紧凑型用户统计概览 -->
    <div class="compact-stats-grid">
      <div class="mini-stat-card">
        <div class="mini-stat-value">{{ userStats?.total_users || 0 }}</div>
        <div class="mini-stat-label">总用户</div>
      </div>
      <div class="mini-stat-card">
        <div class="mini-stat-value">{{ userStats?.active_users_24h || 0 }}</div>
        <div class="mini-stat-label">24h活跃</div>
      </div>
      <div class="mini-stat-card">
        <div class="mini-stat-value">{{ userStats?.active_users_30d || 0 }}</div>
        <div class="mini-stat-label">30天活跃</div>
      </div>
    </div>

    <!-- 图表区域 - 更紧凑 -->
    <div class="compact-chart-container">
      <div class="chart-header">
        <span class="chart-title">活跃度趋势</span>
        <span class="chart-subtitle">最近7天</span>
      </div>
      <div ref="activityChartRef" class="compact-chart"></div>
    </div>
  </a-card>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getChartColor } from '@/utils/chartColors'
import { dashboardApi } from '@/apis/dashboard_api'

// Props
const props = defineProps({
  userStats: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

// Chart refs
const activityChartRef = ref(null)
let activityChart = null

// 初始化活跃度趋势图
const initActivityChart = () => {
  if (!activityChartRef.value || !props.userStats?.daily_active_users) return

  activityChart = echarts.init(activityChartRef.value)

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: 'rgba(6, 182, 212, 0.3)',
      borderWidth: 1,
      textStyle: {
        color: '#fff'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: props.userStats.daily_active_users.map(item => item.date),
      axisLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.1)'
        }
      },
      axisLabel: {
        color: 'rgba(255, 255, 255, 0.6)'
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.1)'
        }
      },
      axisLabel: {
        color: 'rgba(255, 255, 255, 0.6)'
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.05)'
        }
      }
    },
    series: [{
      name: '活跃用户数',
      type: 'line',
      data: props.userStats.daily_active_users.map(item => item.active_users),
      smooth: true,
      lineStyle: {
        color: '#06b6d4',
        width: 3,
        shadowColor: 'rgba(6, 182, 212, 0.5)',
        shadowBlur: 10
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [{
            offset: 0, color: 'rgba(6, 182, 212, 0.3)'
          }, {
            offset: 1, color: 'rgba(6, 182, 212, 0.05)'
          }]
        }
      },
      itemStyle: {
        color: '#06b6d4',
        borderWidth: 2,
        borderColor: '#fff',
        shadowColor: 'rgba(6, 182, 212, 0.5)',
        shadowBlur: 10
      },
      emphasis: {
        itemStyle: {
          color: '#06b6d4',
          borderWidth: 3,
          borderColor: '#fff',
          shadowBlur: 15,
          shadowColor: 'rgba(6, 182, 212, 0.8)'
        }
      }
    }]
  }

  activityChart.setOption(option)
}


// 更新图表
const updateCharts = () => {
  nextTick(() => {
    initActivityChart()
  })
}

// 监听数据变化
watch(() => props.userStats, () => {
  updateCharts()
}, { deep: true })

// 窗口大小变化时重新调整图表
const handleResize = () => {
  if (activityChart) activityChart.resize()
}

onMounted(() => {
  updateCharts()
  window.addEventListener('resize', handleResize)
})

// 组件卸载时清理
const cleanup = () => {
  window.removeEventListener('resize', handleResize)
  if (activityChart) {
    activityChart.dispose()
    activityChart = null
  }
}

// 导出清理函数供父组件调用
defineExpose({
  cleanup
})
</script>

<style scoped lang="less">

// UserStatsComponent 特有的样式
.compact-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;

  .mini-stat-card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 12px;
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.05);
    transition: all 0.3s ease;

    &:hover {
      background: rgba(6, 182, 212, 0.1);
      border-color: rgba(6, 182, 212, 0.3);
      transform: translateY(-2px);
    }

    .mini-stat-value {
      font-size: 20px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 4px;
      text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
    }

    .mini-stat-label {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
    }
  }
}

.compact-chart-container {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .chart-title {
      font-size: 14px;
      font-weight: 600;
      color: #fff;
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

    .chart-subtitle {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.4);
      background: rgba(255, 255, 255, 0.05);
      padding: 2px 8px;
      border-radius: 4px;
    }
  }

  .compact-chart {
    height: 200px;
    width: 100%;
  }
}
</style>