import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' }
      },
      {
        path: 'workbench',
        name: 'Workbench',
        component: () => import('@/views/Workbench.vue'),
        meta: { title: '员工工作台', icon: 'Monitor' }
      },
      {
        path: 'certificates',
        name: 'Certificates',
        component: () => import('@/views/Certificates.vue'),
        meta: { title: '证书管理', icon: 'Document' }
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue'),
        meta: { title: '任务管理', icon: 'List' }
      },
      {
        path: 'employees',
        name: 'Employees',
        component: () => import('@/views/Employees.vue'),
        meta: { title: '员工管理', icon: 'User', roles: ['admin', 'manager'] }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/Reports.vue'),
        meta: { title: '报告中心', icon: 'DataAnalysis' }
      },
      {
        path: 'training',
        name: 'Training',
        component: () => import('@/views/Training.vue'),
        meta: { title: '培训管理', icon: 'Reading' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/Users.vue'),
        meta: { title: '用户管理', icon: 'UserFilled', roles: ['admin'] }
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/Logs.vue'),
        meta: { title: '操作日志', icon: 'Notebook', roles: ['admin'] }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
        meta: { title: '个人中心', icon: 'Setting' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/404.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  NProgress.start()
  
  const userStore = useUserStore()
  const token = userStore.token
  const userRole = userStore.user?.role
  
  if (to.meta.requiresAuth && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && token) {
    next({ path: '/' })
  } else if (to.meta.roles && !to.meta.roles.includes(userRole)) {
    next({ path: '/404' })
  } else {
    next()
  }
})

router.afterEach((to) => {
  NProgress.done()
  if (to.meta.title) {
    document.title = `${to.meta.title} - 企业资质证书管理系统`
  }
})

export default router
