import {
  createRouter,
  createWebHashHistory,
  createWebHistory,
} from 'vue-router';

import { resetStaticRoutes } from '@vben/utils';

import { createRouterGuard } from './guard';
import { routes } from './routes';

/**
 *  @zh_CN 创建vue-router实例
 */
const router = createRouter({
  history:
    import.meta.env.VITE_ROUTER_HISTORY === 'hash'
      ? createWebHashHistory(import.meta.env.VITE_BASE)
      : createWebHistory(import.meta.env.VITE_BASE),
  // 应该添加到路由的初始路由列表。
  routes,
  scrollBehavior: (to, _from, savedPosition) => {
    if (savedPosition) {
      return savedPosition;
    }
    return to.hash ? { behavior: 'smooth', el: to.hash } : { left: 0, top: 0 };
  },
  // 是否应该禁止尾部斜杠。
  // strict: true,
});

const resetRoutes = () => resetStaticRoutes(router, routes);

// 创建路由守卫
createRouterGuard(router);

// 全局导航错误兜底，防止未捕获的异常输出 [VUE_ROUTER_R0010] / [VUE_ROUTER_R0011]
router.onError((error) => {
  // 导航被取消（如 token 过期后 guard 返回 false）不需要额外处理
  if (
    error.name === 'NavigationDuplicated' ||
    error.message?.includes('Navigation cancelled')
  ) {
    return;
  }
  console.warn('[Router] Navigation error:', error.message);
});

export { resetRoutes, router };
