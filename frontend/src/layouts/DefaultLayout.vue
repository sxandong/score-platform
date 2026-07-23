<template>
  <el-container style="height:100vh">
    <el-aside width="220px" style="background:#304156">
      <div style="color:#fff;padding:16px;text-align:center;font-size:18px;font-weight:bold">
        成绩管理平台
      </div>
      <el-menu :default-active="route.path" background-color="#304156" text-color="#bfcbd9"
        active-text-color="#409EFF" router>
        <el-menu-item index="/dashboard"><el-icon><DataAnalysis /></el-icon> 仪表盘</el-menu-item>
        <el-menu-item v-if="auth.hasRole('admin')" index="/users"><el-icon><User /></el-icon> 用户管理</el-menu-item>
        <el-menu-item v-if="auth.hasPermission('exam:read')" index="/exams"><el-icon><Document /></el-icon> 考试管理</el-menu-item>
        <el-sub-menu v-if="auth.hasPermission('score:create') || auth.hasPermission('score:read')" index="scores">
          <template #title><el-icon><Edit /></el-icon> 成绩管理</template>
          <el-menu-item v-if="auth.hasPermission('score:create')" index="/scores/entry">成绩录入</el-menu-item>
          <el-menu-item v-if="auth.hasPermission('score:create')" index="/scores/import">批量导入</el-menu-item>
          <el-menu-item v-if="auth.hasPermission('score:read')" index="/scores/query">成绩查询</el-menu-item>
        </el-sub-menu>
        <el-sub-menu v-if="auth.hasPermission('analysis:view')" index="analysis">
          <template #title><el-icon><TrendCharts /></el-icon> 统计分析</template>
          <el-menu-item index="/analysis/class-compare">班级对比</el-menu-item>
          <el-menu-item index="/analysis/student-trend">成绩趋势</el-menu-item>
        </el-sub-menu>
        <el-menu-item v-if="auth.hasPermission('report:export')" index="/reports"><el-icon><Download /></el-icon> 报表导出</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="background:#fff;border-bottom:1px solid #dcdfe6;display:flex;align-items:center;justify-content:flex-end;padding:0 20px">
        <span style="margin-right:16px">{{ auth.user?.real_name }}</span>
        <el-button text @click="handleLogout">退出</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function handleLogout() { auth.logout(); router.push('/login') }
</script>
