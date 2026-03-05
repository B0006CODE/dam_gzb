<template>
  <!-- 登录页面根容器，根据服务器状态动态添加样式类 -->
  <div class="login-view" :class="{ 'has-alert': serverStatus === 'error' }">
    <!-- 服务器状态异常时的顶部提示条 -->
    <div v-if="serverStatus === 'error'" class="server-status-alert">
      <div class="alert-content">
        <exclamation-circle-outlined class="alert-icon" />
        <div class="alert-text">
          <div class="alert-title">服务端连接失败</div>
          <div class="alert-message">{{ serverError }}</div>
        </div>
        <a-button type="link" size="small" @click="checkServerHealth" :loading="healthChecking">
          重试
        </a-button>
      </div>
    </div>

    <!-- 登录页面主要布局 -->
    <div class="login-layout">
      <!-- 左侧品牌形象图片区域 -->
      <div class="login-image-section">
        <img :src="loginBgImage" alt="中国水库地图" class="login-bg-image" />
        <div class="image-overlay">
          <div class="brand-info">
            <h1 class="brand-title">{{ brandName }}</h1>
          </div>
          <div class="brand-copyright">
            <p>{{ infoStore.footer?.copyright || 'Smart Water' }}. {{ infoStore.branding?.copyright || '版权所有' }}</p>
          </div>
        </div>
      </div>

      <!-- 右侧登录表单区域 -->
      <div class="login-form-section">
        <div class="login-container">
          <header class="login-header">
            <p class="login-title">欢迎登录</p>
            <h1 class="login-brand">{{ brandName }}</h1>
          </header>

          <div class="login-content" :class="{ 'is-initializing': isFirstRun }">
            <!-- 初始化管理员表单 -->
            <div v-if="isFirstRun" class="login-form login-form--init">
              <h2>系统初始化，请创建超级管理员</h2>
              <a-form :model="adminForm" @finish="handleInitialize" layout="vertical">
                <a-form-item
                  label="用户ID"
                  name="user_id"
                  :rules="[
                    { required: true, message: '请输入用户ID' },
                    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户ID只能包含字母、数字和下划线' },
                    { min: 3, max: 20, message: '用户ID长度必须在3-20个字符之间' }
                  ]"
                >
                  <a-input
                    v-model:value="adminForm.user_id"
                    placeholder="请输入用户ID（3-20个字符）"
                    :maxlength="20"
                  />
                </a-form-item>

                <a-form-item label="密码" name="password" :rules="[{ required: true, message: '请输入密码' }]">
                  <a-input-password v-model:value="adminForm.password" />
                </a-form-item>

                <a-form-item
                  label="确认密码"
                  name="confirmPassword"
                  :rules="[
                    { required: true, message: '请确认密码' },
                    { validator: validateConfirmPassword }
                  ]"
                >
                  <a-input-password v-model:value="adminForm.confirmPassword" />
                </a-form-item>

                <a-form-item>
                  <a-button type="primary" html-type="submit" :loading="loading" block>
                    创建管理员账户
                  </a-button>
                </a-form-item>
              </a-form>
            </div>

            <!-- 普通登录表单 -->
            <div v-else class="login-form">
              <a-form :model="loginForm" @finish="handleLogin" layout="vertical">
                <a-form-item label="登录账号" name="loginId" :rules="[{ required: true, message: '请输入用户ID' }]">
                  <a-input v-model:value="loginForm.loginId" placeholder="请输入用户ID">
                    <template #prefix><user-outlined /></template>
                  </a-input>
                </a-form-item>

                <a-form-item label="密码" name="password" :rules="[{ required: true, message: '请输入密码' }]">
                  <a-input-password v-model:value="loginForm.password">
                    <template #prefix><lock-outlined /></template>
                  </a-input-password>
                </a-form-item>

                <a-form-item>
                  <a-button type="primary" html-type="submit" :loading="loading" :disabled="isLocked" block>
                    <span v-if="isLocked">账户已锁定 {{ formatTime(lockRemainingTime) }}</span>
                    <span v-else>登录</span>
                  </a-button>
                </a-form-item>
              </a-form>
            </div>

            <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useInfoStore } from '@/stores/info'
import { useAgentStore } from '@/stores/agent'
import { message } from 'ant-design-vue'
import { healthApi } from '@/apis/system_api'
import { UserOutlined, LockOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const infoStore = useInfoStore()
const agentStore = useAgentStore()

/* 品牌展示 */
const loginBgImage = '/china-reservoir-map.png'
const brandName = computed(() => infoStore.branding?.name?.trim() || '大坝工程领域知识图谱大模型')

/* 状态 */
const isFirstRun = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const serverStatus = ref('loading')
const serverError = ref('')
const healthChecking = ref(false)

/* 锁定逻辑 */
const isLocked = ref(false)
const lockRemainingTime = ref(0)
let lockCountdown = null

/* 表单 */
const loginForm = reactive({ loginId: '', password: '' })
const adminForm = reactive({ user_id: '', password: '', confirmPassword: '' })

function clearLockCountdown () {
  if (lockCountdown) { clearInterval(lockCountdown); lockCountdown = null }
}
function startLockCountdown (seconds) {
  clearLockCountdown()
  isLocked.value = true
  lockRemainingTime.value = seconds
  lockCountdown = setInterval(() => {
    lockRemainingTime.value--
    if (lockRemainingTime.value <= 0) {
      clearLockCountdown()
      isLocked.value = false
      errorMessage.value = ''
    }
  }, 1000)
}
function formatTime (s) {
  if (s < 60) return `${s}秒`
  if (s < 3600) return `${Math.floor(s / 60)}分${s % 60}秒`
  if (s < 86400) return `${Math.floor(s / 3600)}小时${Math.floor((s % 3600) / 60)}分钟`
  return `${Math.floor(s / 86400)}天${Math.floor((s % 86400) / 3600)}小时`
}
async function validateConfirmPassword (rule, value) {
  if (!value) throw new Error('请确认密码')
  if (value !== adminForm.password) throw new Error('两次输入的密码不一致')
}

async function handleLogin () {
  if (isLocked.value) {
    message.warning(`账户已锁定，请等待 ${formatTime(lockRemainingTime.value)}`)
    return
  }
  try {
    loading.value = true
    errorMessage.value = ''
    clearLockCountdown()
    await userStore.login({ loginId: loginForm.loginId, password: loginForm.password })
    message.success('登录成功')
    const redirect = sessionStorage.getItem('redirect') || '/'
    sessionStorage.removeItem('redirect')
    if (redirect === '/') {
      if (userStore.isAdmin) { router.push('/agent'); return }
      await agentStore.initialize().catch(() => {})
      router.push('/agent')
    } else {
      router.push(redirect)
    }
  } catch (e) {
    if (e.status === 423) {
      let t = 0
      if (e.headers?.get) t = parseInt(e.headers.get('X-Lock-Remaining') || 0)
      if (!t) {
        const m = e.message.match(/(\d+)\s*秒/)
        if (m) t = parseInt(m[1])
      }
      if (t > 0) startLockCountdown(t)
      errorMessage.value = t ? `由于多次登录失败，账户已锁定 ${formatTime(t)}` : '账户已锁定，请稍后再试'
    } else {
      errorMessage.value = e.message || '登录失败，请检查用户名和密码'
    }
  } finally {
    loading.value = false
  }
}

async function handleInitialize () {
  try {
    loading.value = true
    errorMessage.value = ''
    if (adminForm.password !== adminForm.confirmPassword) {
      errorMessage.value = '两次输入的密码不一致'
      return
    }
    await userStore.initialize({ user_id: adminForm.user_id, password: adminForm.password })
    message.success('管理员账户创建成功')
    router.push('/agent')
  } catch (e) {
    errorMessage.value = e.message || '初始化失败，请重试'
  } finally {
    loading.value = false
  }
}

async function checkFirstRunStatus () {
  try {
    loading.value = true
    isFirstRun.value = await userStore.checkFirstRun()
  } catch (e) {
    errorMessage.value = '系统出错，请稍后再试'
  } finally {
    loading.value = false
  }
}

async function checkServerHealth () {
  try {
    healthChecking.value = true
    const res = await healthApi.checkHealth()
    serverStatus.value = res.status === 'ok' ? 'ok' : 'error'
    serverError.value = res.message || '服务端状态异常'
  } catch (e) {
    serverStatus.value = 'error'
    serverError.value = e.message || '无法连接到服务端，请检查网络连接'
  } finally {
    healthChecking.value = false
  }
}

onMounted(async () => {
  if (userStore.isLoggedIn) { router.push('/agent'); return }
  await checkServerHealth()
  await checkFirstRunStatus()
})

onUnmounted(() => clearLockCountdown())
</script>

<style lang="less" scoped>
/* 样式与原来一致，仅把乱码中文恢复 */
.login-view{height:100vh;width:100%;position:relative;padding-top:0;background:transparent;&.has-alert{padding-top:60px}}
.server-status-alert{position:absolute;top:0;left:0;right:0;padding:12px 20px;background:linear-gradient(135deg,#ff4d4f,#ff7875);color:#fff;z-index:1000;box-shadow:0 2px 8px rgba(255,77,79,.3);
  .alert-content{display:flex;align-items:center;max-width:1200px;margin:0 auto;
    .alert-icon{font-size:20px;margin-right:12px;color:#fff}
    .alert-text{flex:1;
      .alert-title{font-weight:600;font-size:16px;margin-bottom:2px}
      .alert-message{font-size:14px;opacity:.9}
    }
  }
}
.login-layout{display:flex;min-height:100%;width:100%;background:transparent}
.login-image-section{flex:0 0 52%;position:relative;overflow:hidden;max-height:100vh;border-right:var(--glass-border);
  .login-bg-image{width:100%;height:100%;object-fit:cover;object-position:center;filter:brightness(.96) contrast(1.1) saturate(1.15)}
  .image-overlay{position:absolute;top:0;left:0;right:0;bottom:0;background:linear-gradient(to right,rgba(4,30,64,.52),rgba(4,30,64,.24));display:flex;flex-direction:column;justify-content:space-between;padding:72px 64px 36px;backdrop-filter:blur(1px);
    .brand-info{text-align:left;color:var(--text-primary);max-width:none;
      .brand-title{font-size:52px;font-weight:700;margin-bottom:20px;text-shadow:0 4px 12px rgba(0,0,0,.5);letter-spacing:-.5px;background:linear-gradient(135deg,#fff 0%,#94a3b8 100%);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;white-space:nowrap}
      .brand-subtitle{font-size:24px;font-weight:500;margin-bottom:24px;opacity:.92;text-shadow:0 2px 4px rgba(0,0,0,.5);line-height:1.4;color:var(--text-primary)}
      .brand-description{font-size:18px;line-height:1.6;margin:0;opacity:.82;text-shadow:0 1px 3px rgba(0,0,0,.5);color:var(--text-secondary)}
    }
    .brand-copyright{align-self:flex-start;p{margin:0;font-size:14px;color:var(--text-disabled);text-shadow:0 1px 2px rgba(0,0,0,.5);font-weight:400}}
  }
}
.login-form-section{flex:1;min-width:420px;display:flex;justify-content:center;align-items:center;padding:64px 72px;background:transparent}
.login-container{width:100%;max-width:560px;padding:50px;background:var(--glass-bg);backdrop-filter:blur(12px);border-radius:24px;border:1px solid var(--glass-border);box-shadow:0 8px 32px 0 rgba(0,0,0,.37);display:flex;flex-direction:column;gap:32px;transition:transform .3s ease,box-shadow .3s ease,border-color .3s ease;&:hover{box-shadow:0 20px 40px -10px rgba(6,182,212,.2),0 0 0 1px rgba(6,182,212,.2),inset 0 1px 0 rgba(255,255,255,.08);border-color:rgba(6,182,212,.3)}}
.login-header{display:flex;flex-direction:column;gap:8px;text-align:left}
.login-title{margin:0;font-size:14px;font-weight:600;letter-spacing:.08em;color:var(--main-color);text-transform:uppercase}
.login-brand{margin:0;font-size:30px;font-weight:600;color:var(--text-primary);line-height:1.25;white-space:nowrap}
.login-subtitle{margin:0;font-size:16px;color:var(--text-secondary);line-height:1.6}
.login-content{display:flex;flex-direction:column;gap:24px;&.is-initializing{gap:28px}}
.login-form{display:flex;flex-direction:column;gap:12px;width:100%;
  :deep(.ant-form){width:100%}
  :deep(.ant-form-item){margin-bottom:18px}
  :deep(.ant-form-item-label>label){color:var(--text-secondary)}
  :deep(.ant-input){padding:10px 11px;height:auto;background-color:rgba(6,42,92,.3);color:var(--text-primary);border-radius:8px;transition:all .3s ease;&:hover{border-color:rgba(6,182,212,.5);background-color:rgba(15,23,42,.9)}&:focus-within,&.ant-input-affix-wrapper-focused{border-color:var(--main-color);background-color:rgba(15,23,42,.9);box-shadow:0 0 0 3px rgba(6,182,212,.15)}input{background-color:transparent;color:var(--text-primary);&::placeholder{color:var(--text-disabled)}}.anticon{color:var(--text-tertiary);transition:color .2s ease}&:hover .anticon,&:focus-within .anticon{color:var(--text-secondary)}}
  :deep(.ant-input-password){.ant-input-suffix{.anticon{cursor:pointer;&:hover{color:var(--main-color)}}}}
  :deep(.ant-btn){font-size:16px;font-weight:500;padding:12px 16px;height:auto;background:linear-gradient(135deg,var(--main-color) 0%,var(--main-active) 100%);border:none;border-radius:8px;box-shadow:0 4px 14px 0 rgba(6,182,212,.35);transition:all .3s ease;&:hover:not(:disabled){background:linear-gradient(135deg,var(--main-hover) 0%,var(--main-color) 100%);box-shadow:0 6px 20px rgba(6,182,212,.4);transform:translateY(-2px)}&:active:not(:disabled){transform:translateY(0);box-shadow:0 2px 8px rgba(6,182,212,.3)}&:disabled{background:rgba(107,114,128,.5);box-shadow:none;cursor:not-allowed}}
}
.login-form--init{padding:24px;border-radius:18px;background:rgba(6,182,212,.05);border:1px solid rgba(6,182,212,.2);h2{margin-bottom:16px;font-size:22px;font-weight:600;color:var(--main-color);text-align:left}}
.error-message{margin-top:16px;padding:10px 12px;background-color:var(--stats-error-bg);border:1px solid rgba(220,38,38,.25);border-radius:8px;color:var(--stats-error-color);font-size:14px}
</style>
