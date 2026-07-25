<template>
  <el-container style="height:100vh">
    <el-aside width="220px" style="background:var(--edu-dark);overflow-y:auto">
      <div style="padding:20px 16px;text-align:center;border-bottom:1px solid rgba(255,255,255,.1)">
        <div style="font-size:18px;font-weight:700;color:#fff;letter-spacing:2px">成绩管理平台</div>
        <div style="font-size:11px;color:rgba(255,255,255,.5);margin-top:4px">Score Management System</div>
      </div>
      <el-menu :default-active="route.path" background-color="var(--edu-dark)" text-color="rgba(255,255,255,.75)"
        active-text-color="#fff" router style="margin-top:8px">
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon><span>仪表盘</span>
        </el-menu-item>
        <el-menu-item v-if="auth.hasRole('admin')" index="/users">
          <el-icon><User /></el-icon><span>用户管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.hasRole('admin')" index="/grades-classes">
          <el-icon><School /></el-icon><span>年级班级</span>
        </el-menu-item>
        <el-menu-item v-if="auth.hasRole('admin')" index="/students">
          <el-icon><Avatar /></el-icon><span>学生管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.hasPermission('exam:read')" index="/exams">
          <el-icon><Document /></el-icon><span>考试管理</span>
        </el-menu-item>
        <el-sub-menu v-if="auth.hasPermission('score:create') || auth.hasPermission('score:read')" index="scores">
          <template #title><el-icon><Edit /></el-icon><span>成绩管理</span></template>
          <el-menu-item v-if="auth.hasPermission('score:create')" index="/scores/entry">成绩录入</el-menu-item>
          <el-menu-item v-if="auth.hasPermission('score:create')" index="/scores/import">批量导入</el-menu-item>
          <el-menu-item v-if="auth.hasPermission('score:read')" index="/scores/query">成绩查询</el-menu-item>
        </el-sub-menu>
        <el-sub-menu v-if="auth.hasPermission('analysis:view')" index="analysis">
          <template #title><el-icon><TrendCharts /></el-icon><span>统计分析</span></template>
          <el-menu-item index="/analysis/class-compare">班级对比</el-menu-item>
          <el-menu-item index="/analysis/student-trend">成绩趋势</el-menu-item>
        </el-sub-menu>
        <el-menu-item v-if="auth.hasPermission('report:export')" index="/reports">
          <el-icon><Download /></el-icon><span>报表导出</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header style="background:#fff;border-bottom:1px solid var(--border-color);display:flex;
        align-items:center;justify-content:space-between;padding:0 24px;height:56px">
        <div style="display:flex;align-items:center;gap:12px">
          <el-icon :size="18" color="var(--edu-blue)"><School /></el-icon>
          <span style="font-size:15px;font-weight:600;color:var(--tx-primary)">{{ route.meta.title || '仪表盘' }}</span>
        </div>
        <div style="display:flex;align-items:center;gap:16px">
          <span style="color:var(--tx-secondary);font-size:13px">
            <el-icon><UserFilled /></el-icon> {{ auth.user?.real_name || '管理员' }}
          </span>
          <el-button text type="danger" size="small" @click="handleLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main style="background:var(--bg-page);padding:20px 24px;overflow-y:auto">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
const route = useRoute(); const router = useRouter(); const auth = useAuthStore()
function handleLogout() { auth.logout(); router.push('/login') }
</script>

<style scoped>
.el-menu-item.is-active { background: rgba(255,255,255,.12) !important; border-left: 3px solid #fff; }
.el-sub-menu .el-menu-item { padding-left: 52px !important; }
</style>
