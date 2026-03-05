<template>
  <div class="stats-overview-container">
    <div class="stats-grid">
      <div class="stat-card primary">
        <div class="stat-icon">
          <MessageCircle class="icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ basicStats?.total_conversations || 0 }}</div>
          <div class="stat-label">总对话数</div>
          <div class="stat-trend" v-if="basicStats?.conversation_trend">
            <TrendingUp v-if="basicStats.conversation_trend > 0" class="trend-icon up" />
            <TrendingDown v-else-if="basicStats.conversation_trend < 0" class="trend-icon down" />
            <span class="trend-text">{{ Math.abs(basicStats.conversation_trend) }}%</span>
          </div>
        </div>
      </div>

      <div class="stat-card success">
        <div class="stat-icon">
          <Activity class="icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ basicStats?.active_conversations || 0 }}</div>
          <div class="stat-label">活跃对话</div>
        </div>
      </div>

      <div class="stat-card info">
        <div class="stat-icon">
          <Mail class="icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ basicStats?.total_messages || 0 }}</div>
          <div class="stat-label">总消息数</div>
        </div>
      </div>

      <div class="stat-card warning">
        <div class="stat-icon">
          <Users class="icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ basicStats?.total_users || 0 }}</div>
          <div class="stat-label">用户数</div>
        </div>
      </div>


    </div>
  </div>
</template>

<script setup>
import { MessageCircle, Activity, Mail, Users, BarChart3, Heart, TrendingUp, TrendingDown } from 'lucide-vue-next'

// Props
const props = defineProps({
  basicStats: {
    type: Object,
    default: () => ({})
  }
})


</script>

<style lang="less" scoped>
.stats-overview-container {
  margin-bottom: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}

.stat-card {
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0) 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    transform: translateY(-2px);
    border-color: rgba(6, 182, 212, 0.5);
    box-shadow: 0 0 20px rgba(6, 182, 212, 0.15);

    &::before {
      opacity: 1;
    }

    .stat-icon {
      background: rgba(6, 182, 212, 0.2);
      color: #06b6d4;
      box-shadow: 0 0 15px rgba(6, 182, 212, 0.3);
    }
  }

  .stat-icon {
    width: 42px;
    height: 42px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    color: rgba(255, 255, 255, 0.7);

    .icon {
      width: 20px;
      height: 20px;
    }
  }

  .stat-content {
    flex: 1;
    z-index: 1;

    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: #fff;
      line-height: 1.2;
      margin-bottom: 4px;
      font-family: 'Inter', sans-serif;
      text-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
    }

    .stat-label {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.5);
      font-weight: 500;
    }

    .stat-trend {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 4px;
      font-size: 12px;
      font-weight: 600;

      .trend-icon {
        width: 14px;
        height: 14px;
      }

      &.up {
        color: #10b981;
      }

      &.down {
        color: #ef4444;
      }
    }
  }

  // 特定卡片样式
  &.primary {
    .stat-icon {
      color: #06b6d4;
      background: rgba(6, 182, 212, 0.1);
    }
  }

  &.success {
    .stat-icon {
      color: #10b981;
      background: rgba(16, 185, 129, 0.1);
    }
  }

  &.warning {
    .stat-icon {
      color: #f59e0b;
      background: rgba(245, 158, 11, 0.1);
    }
  }

  &.info {
    .stat-icon {
      color: #3b82f6;
      background: rgba(59, 130, 246, 0.1);
    }
  }

  &.secondary {
    .stat-icon {
      color: #8b5cf6;
      background: rgba(139, 92, 246, 0.1);
    }
  }

  &.satisfaction-high {
    .stat-icon {
      color: #ec4899;
      background: rgba(236, 72, 153, 0.1);
    }
  }
}
</style>
