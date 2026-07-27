import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/DefaultLayout.vue'),
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/dashboard/AdminDashboard.vue'),
          meta: { title: '仪表盘' },
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/system/UserManage.vue'),
          meta: { title: '用户管理', roles: ['admin'] },
        },
        {
          path: 'grades-classes',
          name: 'grades-classes',
          component: () => import('@/views/system/GradeClassManage.vue'),
          meta: { title: '年级班级', roles: ['admin'] },
        },
        {
          path: 'students',
          name: 'students',
          component: () => import('@/views/system/StudentManage.vue'),
          meta: { title: '学生管理', roles: ['admin'] },
        },
        {
          path: 'electives',
          name: 'electives',
          component: () => import('@/views/system/ElectiveManage.vue'),
          meta: { title: '选科管理', roles: ['admin'] },
        },
        {
          path: 'data-backup',
          name: 'data-backup',
          component: () => import('@/views/system/DataBackup.vue'),
          meta: { title: '数据备份', roles: ['admin'] },
        },
        {
          path: 'exams',
          name: 'exams',
          component: () => import('@/views/system/ExamManage.vue'),
          meta: { title: '考试管理', roles: ['admin', 'director', 'teacher'] },
        },
        {
          path: 'scores/entry',
          name: 'score-entry',
          component: () => import('@/views/scores/ScoreEntry.vue'),
          meta: { title: '成绩录入', roles: ['admin', 'teacher'] },
        },
        {
          path: 'scores/import',
          name: 'score-import',
          component: () => import('@/views/scores/BatchImport.vue'),
          meta: { title: '批量导入', roles: ['admin', 'teacher'] },
        },
        {
          path: 'scores/query',
          name: 'score-query',
          component: () => import('@/views/scores/ScoreQuery.vue'),
          meta: { title: '成绩查询', roles: ['admin', 'director', 'teacher'] },
        },
        {
          path: 'scores/cutoffs',
          name: 'score-cutoffs',
          component: () => import('@/views/scores/ScoreCutoffs.vue'),
          meta: { title: '分数线设置', roles: ['admin', 'director', 'teacher'] },
        },
        {
          path: 'analysis/class-compare',
          name: 'class-compare',
          component: () => import('@/views/analysis/ClassCompare.vue'),
          meta: { title: '班级统计', roles: ['admin', 'director', 'teacher'] },
        },
        {
          path: 'analysis/multi-exam-compare',
          name: 'multi-exam-compare',
          component: () => import('@/views/analysis/MultiExamCompare.vue'),
          meta: { title: '班级对比', roles: ['admin', 'director', 'teacher'] },
        },
        {
          path: 'analysis/score-distribution',
          name: 'score-distribution',
          component: () => import('@/views/analysis/ScoreDistribution.vue'),
          meta: { title: '分数段统计', roles: ['admin', 'director', 'teacher'] },
        },
        {
          path: 'analysis/student-trend',
          name: 'student-trend',
          component: () => import('@/views/analysis/StudentTrend.vue'),
          meta: { title: '成绩趋势' },
        },
        {
          path: 'reports',
          name: 'reports',
          component: () => import('@/views/reports/ReportExport.vue'),
          meta: { title: '报表导出', roles: ['admin', 'director', 'teacher'] },
        },
      ],
    },
    {
      path: '/student',
      component: () => import('@/layouts/StudentLayout.vue'),
      children: [
        {
          path: '',
          name: 'student-dashboard',
          component: () => import('@/views/dashboard/StudentDashboard.vue'),
          meta: { title: '我的成绩' },
        },
      ],
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  if (to.meta.public) {
    if (authStore.isLoggedIn) return next('/dashboard')
    return next()
  }
  if (!authStore.isLoggedIn) return next('/login')
  if (to.meta.roles) {
    const required = to.meta.roles as string[]
    if (!required.some((r) => authStore.hasRole(r))) {
      return next('/dashboard')
    }
  }
  next()
})

export default router
