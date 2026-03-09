import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue';
import { useUserStore } from '@/stores/user';
import { useAgentStore } from '@/stores/agent';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/agent',
      name: 'AgentMain',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'AgentComp',
          component: () => import('../views/AgentView.vue'),
          meta: { keepAlive: true, requiresAuth: true, requiresAdmin: false }
        }
      ]
    },
    {
      path: '/agent/:agent_id',
      name: 'AgentSinglePage',
      component: () => import('../views/AgentSingleView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/exception-qa',
      name: 'ExceptionQaMain',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'ExceptionQaComp',
          component: () => import('../views/ExceptionQaView.vue'),
          meta: { keepAlive: false, requiresAuth: true, requiresAdmin: false }
        }
      ]
    },
    {
      path: '/graph',
      name: 'graph',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'GraphComp',
          component: () => import('../views/GraphView.vue'),
          meta: { keepAlive: false, requiresAuth: true, requiresAdmin: false }
        }
      ]
    },
    {
      path: '/database',
      name: 'database',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'DatabaseComp',
          component: () => import('../views/DataBaseView.vue'),
          meta: { keepAlive: true, requiresAuth: true, requiresAdmin: true }
        },
        {
          path: ':database_id',
          name: 'DatabaseInfoComp',
          component: () => import('../views/DataBaseInfoView.vue'),
          meta: { keepAlive: false, requiresAuth: true, requiresAdmin: true }
        }
      ]
    },
    {
      path: '/setting',
      name: 'setting',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'SettingComp',
          component: () => import('../views/SettingView.vue'),
          meta: { keepAlive: true, requiresAuth: true, requiresAdmin: true }
        }
      ]
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'DashboardComp',
          component: () => import('../views/DashboardView.vue'),
          meta: { keepAlive: false, requiresAuth: true, requiresAdmin: true }
        }
      ]
    },
    {
      path: '/map',
      name: 'reservoirMap',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'ReservoirMapComp',
          component: () => import('../views/ReservoirMapView.vue'),
          meta: { keepAlive: false, requiresAuth: true, requiresAdmin: false }
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('../views/EmptyView.vue'),
      meta: { requiresAuth: false }
    },
  ]
})
router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth === true);
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin);

  const userStore = useUserStore();
  const agentStore = useAgentStore();
  const tokenFromQuery = [to.query.token, to.query.externalToken, to.query.ssoToken]
    .find(value => typeof value === 'string' && value.trim());

  if (!userStore.isLoggedIn && tokenFromQuery) {
    try {
      await userStore.ssoLogin({ token: tokenFromQuery });
      if (!agentStore.isInitialized) {
        await agentStore.initialize().catch(() => {});
      }

      const nextQuery = { ...to.query };
      delete nextQuery.token;
      delete nextQuery.externalToken;
      delete nextQuery.ssoToken;

      next({
        path: to.path === '/login' ? '/agent' : to.path,
        query: nextQuery,
        hash: to.hash,
        replace: true,
      });
      return;
    } catch (error) {
      console.error('SSO自动登录失败:', error);
    }
  }

  const isLoggedIn = userStore.isLoggedIn;
  const isAdmin = userStore.isAdmin;
  if (requiresAuth && !isLoggedIn) {
    sessionStorage.setItem('redirect', to.fullPath);
    next('/login');
    return;
  }
  if (requiresAdmin && !isAdmin) {
    try {
      if (!agentStore.isInitialized) {
        await agentStore.initialize();
      }
      next('/agent');
    } catch (error) {
      console.error('鑾峰彇鏅鸿兘浣撲俊鎭け璐?', error);
      next('/login');
    }
    return;
  }
  if (to.path === '/login' && isLoggedIn) {
    next('/agent');
    return;
  }
  next();
});

export default router
