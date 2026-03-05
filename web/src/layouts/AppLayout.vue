<script setup>
import { ref, reactive, onMounted, useTemplateRef, computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import {
  ExclamationCircleOutlined,
} from '@ant-design/icons-vue'
import { Bot, Waypoints, LibraryBig, Settings, BarChart3, BookOpen, ListChecks, Map } from 'lucide-vue-next';
import { onLongPress } from '@vueuse/core'

import { useConfigStore } from '@/stores/config'
import { useDatabaseStore } from '@/stores/database'
import { useInfoStore } from '@/stores/info'
import { useTaskerStore } from '@/stores/tasker'
import { useUserStore } from '@/stores/user'
import { storeToRefs } from 'pinia'
import UserInfoComponent from '@/components/UserInfoComponent.vue'
import DebugComponent from '@/components/DebugComponent.vue'
import TaskCenterDrawer from '@/components/TaskCenterDrawer.vue'

const configStore = useConfigStore()
const databaseStore = useDatabaseStore()
const infoStore = useInfoStore()
const taskerStore = useTaskerStore()
const userStore = useUserStore()
const { activeCount: activeCountRef, isDrawerOpen } = storeToRefs(taskerStore)
const { isAdmin } = storeToRefs(userStore)

const layoutSettings = reactive({
  showDebug: false,
  useTopBar: false, // 是否使用顶栏
})

// Add state for debug modal
const showDebugModal = ref(false)
const htmlRefHook = useTemplateRef('htmlRefHook')

// Setup long press for debug modal
onLongPress(
  htmlRefHook,
  () => {
    showDebugModal.value = true
  },
  {
    delay: 1000, // 1秒长按
    modifiers: {
      prevent: true
    }
  }
)

// Handle debug modal close
const handleDebugModalClose = () => {
  showDebugModal.value = false
}

const getRemoteConfig = () => {
  configStore.refreshConfig()
}

const getRemoteDatabase = () => {
  databaseStore.getDatabaseInfo()
}

onMounted(async () => {
  // 加载信息配置
  await infoStore.loadInfoConfig()
  // 加载其他配置
  getRemoteConfig()
  getRemoteDatabase()
})

// 下面是导航菜单部分
const route = useRoute()

const activeTaskCount = computed(() => activeCountRef.value || 0)

// 下面是导航菜单部分,添加智能体项
const mainList = [
  {
    name: '\u68c0\u7d22',
    path: '/agent',
    icon: Bot,
    activeIcon: Bot,
    requiresAdmin: false,
  },
  {
    name: '\u77e5\u8bc6\u56fe\u8c31',
    path: '/graph',
    icon: Waypoints,
    activeIcon: Waypoints,
    requiresAdmin: false,
  },
  {
    name: '\u77e5\u8bc6\u5e93',
    path: '/database',
    icon: LibraryBig,
    activeIcon: LibraryBig,
    requiresAdmin: true,
  },
  {
    name: '\u6c34\u5e93\u5730\u56fe',
    path: '/map',
    icon: Map,
    activeIcon: Map,
    requiresAdmin: false,
  },
  {
    name: '\u7ba1\u7406\u9762\u677f',
    path: '/dashboard',
    icon: BarChart3,
    activeIcon: BarChart3,
    requiresAdmin: true,
  }
]

const visibleNavItems = computed(() =>
  mainList.filter((item) => !item.requiresAdmin || isAdmin.value)
)
</script>

<template>
  <div class="app-layout" :class="{ 'use-top-bar': layoutSettings.useTopBar }">
    <div class="header" :class="{ 'top-bar': layoutSettings.useTopBar }">
      <div class="logo circle">
        <router-link to="/agent">
          <img :src="infoStore.organization.avatar">
        </router-link>
      </div>
      <div class="nav">
        <!-- 使用mainList渲染导航项 -->
        <RouterLink
          v-for="(item, index) in visibleNavItems"
          :key="index"
          :to="item.path"
          v-show="!item.hidden"
          class="nav-item"
          active-class="active">
          <component class="icon" :is="route.path.startsWith(item.path) ? item.activeIcon : item.icon" size="22"/>
          <span class="nav-text">{{ item.name }}</span>
        </RouterLink>
        <div
          class="nav-item task-center"
          :class="{ active: isDrawerOpen }"
          @click="taskerStore.openDrawer()"
          v-if="activeTaskCount > 0"
        >
          <a-badge
            :count="activeTaskCount"
            :overflow-count="99"
            class="task-center-badge"
            size="small"
          >
            <ListChecks class="icon" size="22" />
          </a-badge>
          <span class="nav-text">任务中心</span>
        </div>
      </div>
      <div
        ref="htmlRefHook"
        class="fill debug-trigger"
      ></div>


        <!-- 已移除文档中心链接 -->
      <!-- <div class="nav-item api-docs">
        <a-tooltip placement="right">
          <template #title>接口文档 {{ apiDocsUrl }}</template>
          <a :href="apiDocsUrl" target="_blank" class="github-link">
            <ApiOutlined class="icon" style="color: #222;"/>
          </a>
        </a-tooltip>
      </div> -->

      <!-- 用户信息组件 -->
      <div class="nav-item user-info">
        <a-tooltip placement="right">
          <template #title>用户信息</template>
          <UserInfoComponent />
        </a-tooltip>
      </div>

      <RouterLink class="nav-item setting" to="/setting" active-class="active" v-if="isAdmin">
        <a-tooltip placement="right">
          <template #title>设置</template>
          <Settings />
        </a-tooltip>
      </RouterLink>
    </div>
    <div class="header-mobile">
      <RouterLink
        v-for="(item, index) in visibleNavItems"
        :key="`mobile-${index}`"
        :to="item.path"
        class="nav-item"
        active-class="active"
      >
        {{ item.name }}
      </RouterLink>
    </div>
    <router-view v-slot="{ Component, route }" id="app-router-view">
      <keep-alive v-if="route.meta.keepAlive !== false">
        <component :is="Component" />
      </keep-alive>
      <component :is="Component" v-else />
    </router-view>

    <!-- Debug Modal -->
    <a-modal
      v-model:open="showDebugModal"
      title="调试面板"
      width="90%"
      :footer="null"
      @cancel="handleDebugModalClose"
      :maskClosable="true"
      :destroyOnClose="true"
      class="debug-modal"
    >
      <DebugComponent />
    </a-modal>
    <TaskCenterDrawer />
  </div>
</template>

<style lang="less" scoped>
// Less 变量定义
@header-width: 86px;

.app-layout {
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100vh;
  min-width: var(--min-width);

  .header-mobile {
    display: none;
  }

  .debug-panel {
    position: absolute;
    z-index: 100;
    right: 0;
    bottom: 50px;
    border-radius: 20px 0 0 20px;
    cursor: pointer;
  }
}

div.header, #app-router-view {
  height: 100%;
  max-width: 100%;
  user-select: none;
}

#app-router-view {
  flex: 1 1 auto;
  overflow-y: auto;
}

.header {
  display: flex;
  flex-direction: column;
  flex: 0 0 @header-width;
  justify-content: flex-start;
  align-items: center;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  height: 100%;
  width: @header-width;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 100;

  .nav {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    gap: 16px;
    margin-top: 20px;
  }

  .logo {
    width: 46px;
    height: 46px;
    margin: 24px 0;
    padding: 2px;
    background: radial-gradient(circle, rgba(6, 182, 212, 0.2) 0%, transparent 70%);
    border-radius: 50%;

    img {
      width: 100%;
      height: 100%;
      border-radius: 50%;
      box-shadow: 0 0 15px rgba(6, 182, 212, 0.3);
    }
  }

  .nav-item {
    display: flex;
    flex-direction: column;
    gap: 5px;
    align-items: center;
    justify-content: center;
    width: 64px;
    min-height: 64px;
    padding: 10px 8px;
    border-radius: 12px;
    color: rgba(255, 255, 255, 0.6);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    text-decoration: none;
    cursor: pointer;

    .icon {
      transition: transform 0.3s ease;
    }

    &:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.05);
      .icon {
        transform: scale(1.1);
      }
    }

    &.active {
      color: #06b6d4;
      background: rgba(6, 182, 212, 0.1);
      box-shadow: inset 0 0 10px rgba(6, 182, 212, 0.1);
      
      &::before {
        content: '';
        position: absolute;
        left: 0;
        width: 3px;
        height: 24px;
        background: #06b6d4;
        border-radius: 0 4px 4px 0;
        box-shadow: 0 0 10px #06b6d4;
      }

      .nav-text {
        color: #06b6d4;
        font-weight: 600;
        text-shadow: 0 0 8px rgba(6, 182, 212, 0.4);
      }
    }
  }

  .nav-text {
    font-size: 11px;
    line-height: 1;
    color: inherit;
    text-align: center;
    margin-top: 4px;
  }

  .user-info, .setting {
    margin-top: auto;
    margin-bottom: 20px;
  }

  .setting {
    margin-top: 10px;
    margin-bottom: 24px;
    color: rgba(255, 255, 255, 0.5);
    
    &:hover {
      color: #06b6d4;
    }
  }
}



@media (max-width: 1024px) {
  .app-layout {
    .header {
      .nav-item {
        width: 58px;
        min-height: 58px;
        padding: 8px 6px;
        gap: 4px;
      }

      .nav-text {
        font-size: 10px;
      }

      .logo {
        width: 40px;
        height: 40px;
        margin: 20px 0;
      }
    }
  }
}

@media (max-width: 768px) {
  .layout-container {
    padding: 20px 24px !important;
  }
  
  .app-layout {
    .header {
      width: 68px;
      
      .nav-item {
        width: 52px;
        min-height: 52px;
        padding: 6px;
        gap: 3px;
      }

      .nav-text {
        font-size: 9px;
      }

      .logo {
        width: 36px;
        height: 36px;
        margin: 16px 0;
      }
    }
  }
}

@media (max-width: 520px) {
  .layout-container {
    padding: 16px 20px !important;
  }
  
  .app-layout {
    flex-direction: column-reverse;

    div.header {
      display: none;
    }

    .debug-panel {
      bottom: 10rem;
    }

  }
  .app-layout div.header-mobile {
    display: flex;
    flex-direction: row;
    width: 100%;
    padding: 0 20px;
    justify-content: space-around;
    align-items: center;
    flex: 0 0 60px;
    border-right: none;
    height: 40px;

    .nav-item {
      text-decoration: none;
      width: 40px;
      color: rgba(255, 255, 255, 0.8);
      font-size: 1rem;
      font-weight: bold;
      transition: color 0.1s ease-in-out, font-size 0.1s ease-in-out;

      &.active {
        color: #06b6d4;
        font-size: 1.1rem;
      }
    }
  }
  .app-layout .chat-box::webkit-scrollbar {
    width: 0;
  }
}

.app-layout.use-top-bar {
  flex-direction: column;
}

.header.top-bar {
  flex-direction: row;
  flex: 0 0 50px;
  width: 100%;
  height: 50px;
  border-right: none;
  border-bottom: 1px solid var(--main-40);
  background-color: var(--main-20);
  padding: 0 20px;
  gap: 24px;

  .logo {
    width: fit-content;
    height: 28px;
    margin-right: 16px;
    display: flex;
    align-items: center;

    a {
      display: flex;
      align-items: center;
      text-decoration: none;
      color: inherit;
    }

    img {
      width: 28px;
      height: 28px;
      margin-right: 8px;
    }

  }

  .nav {
    flex-direction: row;
    height: auto;
    gap: 20px;
  }

  .nav-item {
    flex-direction: row;
    width: auto;
    padding: 4px 16px;
    margin: 0;

    .icon {
      margin-right: 8px;
      font-size: 15px; // 减小图标大小
      border: none;
      outline: none;

      &:focus, &:active {
        border: none;
        outline: none;
      }
    }

    .nav-text {
      margin-top: 0;
      font-size: 15px;
      color: inherit;
    }

    &.github, &.setting {
      padding: 8px 12px;

      .icon {
        margin-right: 0;
        font-size: 18px;
      }

      &.active {
        color: var(--main-color);
      }
    }

    &.github {
      a {
        display: flex;
        align-items: center;
      }

      .github-stars {
        display: flex;
        align-items: center;
        margin-left: 6px;

        .star-icon {
          color: #f0a742;
          font-size: 14px;
          margin-right: 2px;
        }
      }
    }
  }
}
</style>
