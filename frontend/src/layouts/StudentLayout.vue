<template>
  <el-container style="height:100vh">
    <el-header style="background:#409EFF;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 20px">
      <span style="font-size:18px;font-weight:bold">成绩管理平台 - 学生端</span>
      <div>
        <span style="margin-right:16px">{{ auth.user?.real_name }}</span>
        <el-button text style="color:#fff" @click="handleLogout">退出</el-button>
      </div>
    </el-header>
    <el-main><router-view /></el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
const router = useRouter()
const auth = useAuthStore()
function handleLogout() { auth.logout(); router.push('/login') }
</script>
