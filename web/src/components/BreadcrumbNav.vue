<template>
  <div class="breadcrumb-nav">
    <a-breadcrumb>
      <template #separator>
        <ChevronRight :size="14" class="separator-icon" />
      </template>
      <a-breadcrumb-item 
        v-for="(item, index) in breadcrumbItems" 
        :key="index"
      >
        <router-link 
          v-if="item.path && index < breadcrumbItems.length - 1" 
          :to="item.path"
          class="breadcrumb-link"
        >
          <component v-if="item.icon" :is="item.icon" :size="14" class="breadcrumb-icon" />
          <span>{{ item.name }}</span>
        </router-link>
        <span v-else class="breadcrumb-current">
          <component v-if="item.icon" :is="item.icon" :size="14" class="breadcrumb-icon" />
          <span>{{ item.name }}</span>
        </span>
      </a-breadcrumb-item>
    </a-breadcrumb>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronRight, Home, Bot, LibraryBig, Waypoints, Settings, BarChart3, Map } from 'lucide-vue-next'
import { useDatabaseStore } from '@/stores/database'

const route = useRoute()
const databaseStore = useDatabaseStore()

// 路由映射配置
const routeMap = {
  '/agent': { name: '检索', icon: Bot },
  '/graph': { name: '知识图谱', icon: Waypoints },
  '/database': { name: '知识库', icon: LibraryBig },
  '/map': { name: '水库地图', icon: Map },
  '/dashboard': { name: '管理面板', icon: BarChart3 },
  '/setting': { name: '设置', icon: Settings },
}

// 生成面包屑项
const breadcrumbItems = computed(() => {
  const items = [
    { name: '首页', path: '/agent', icon: Home }
  ]

  const path = route.path
  const pathSegments = path.split('/').filter(Boolean)

  // 如果是根路径，只返回首页
  if (pathSegments.length === 0) {
    return items
  }

  // 构建面包屑路径
  let currentPath = ''
  pathSegments.forEach((segment, index) => {
    currentPath += `/${segment}`
    
    // 检查是否是已知路由
    if (routeMap[currentPath]) {
      items.push({
        name: routeMap[currentPath].name,
        path: currentPath,
        icon: routeMap[currentPath].icon
      })
    } else if (index === pathSegments.length - 1) {
      // 如果是最后一段且不在映射中，尝试从路由元数据获取
      const routeName = route.meta?.breadcrumbName || route.name || segment
      
      // 特殊处理：知识库详情页
      if (path.includes('/database/')) {
        // 获取知识库名称，如果没有则显示ID
        const dbName = databaseStore.database?.name || route.params.database_id
        items.push({
          name: dbName,
          path: currentPath,
          icon: null
        })
      } else {
        items.push({
          name: routeName,
          path: null, // 当前页面不可点击
          icon: null
        })
      }
    }
  })

  return items
})
</script>

<style lang="less" scoped>
.breadcrumb-nav {
  padding: 16px 0;
  margin-bottom: 8px;
  
  :deep(.ant-breadcrumb) {
    font-size: 14px;
    
    .ant-breadcrumb-separator {
      margin: 0 8px;
      color: rgba(255, 255, 255, 0.3);
      
      .separator-icon {
        color: rgba(255, 255, 255, 0.3);
      }
    }
  }
  
  .breadcrumb-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: rgba(255, 255, 255, 0.6);
    text-decoration: none;
    transition: all 0.2s ease;
    padding: 4px 8px;
    border-radius: 6px;
    
    &:hover {
      color: #06b6d4;
      background: rgba(6, 182, 212, 0.1);
      
      .breadcrumb-icon {
        color: #06b6d4;
      }
    }
    
    .breadcrumb-icon {
      color: rgba(255, 255, 255, 0.5);
      transition: color 0.2s ease;
    }
  }
  
  .breadcrumb-current {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #06b6d4;
    font-weight: 500;
    padding: 4px 8px;
    
    .breadcrumb-icon {
      color: #06b6d4;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .breadcrumb-nav {
    padding: 12px 0;
    
    :deep(.ant-breadcrumb) {
      font-size: 13px;
    }
  }
}
</style>
