<script setup>
import { themeConfig } from '@/assets/theme'
import { useAgentStore } from '@/stores/agent'
import { useUserStore } from '@/stores/user'
import { onMounted } from 'vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'

const agentStore = useAgentStore();
const userStore = useUserStore();

onMounted(async () => {
  if (userStore.isLoggedIn) {
    await agentStore.initialize();
  }
})
</script>
<template>
  <a-config-provider :theme="themeConfig" :locale="zhCN">
    <router-view />
  </a-config-provider>
</template>
