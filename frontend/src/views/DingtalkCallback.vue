<template>
  <div class="login-page">
    <div class="login-bg"></div>
    <el-card class="login-card">
      <div class="callback-center">
        <el-icon class="loading-icon" :size="48" color="#1a5490"><Loading /></el-icon>
        <div class="callback-title">正在登录...</div>
        <div class="callback-desc">{{ statusText }}</div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const statusText = ref('正在获取钉钉授权...')

onMounted(async () => {
  try {
    const authCode = (route.query.authCode as string) || (route.query.code as string) || ''
    if (!authCode) {
      ElMessage.error('未获取到钉钉授权码')
      setTimeout(() => router.push('/login'), 1500)
      return
    }

    statusText.value = '正在登录系统...'
    const res = await authStore.dingtalkLogin(authCode)
    if (res.user.must_change_password) {
      ElMessage.warning('首次登录请修改密码')
      router.push('/change-password')
    } else {
      ElMessage.success('登录成功')
      router.push('/dashboard')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '钉钉登录失败')
    setTimeout(() => router.push('/login'), 1500)
  }
})
</script>

<style scoped>
.login-page {
  display: flex; justify-content: center; align-items: center; height: 100vh;
  background: linear-gradient(135deg, #1a5490 0%, #1e3a5f 60%, #0d2137 100%);
  position: relative; overflow: hidden;
}
.login-bg {
  position: absolute; top: -50%; right: -30%; width: 800px; height: 800px;
  background: rgba(255,255,255,.03); border-radius: 50%; pointer-events: none;
}
.login-card {
  width: 400px; border-radius: 12px; padding: 40px 24px;
  box-shadow: 0 8px 32px rgba(0,0,0,.18);
}
.callback-center { text-align: center; padding: 24px 0; }
.loading-icon { animation: spin 1.5s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.callback-title { font-size: 18px; font-weight: 600; color: var(--edu-blue); margin-top: 16px; }
.callback-desc { font-size: 13px; color: var(--tx-secondary); margin-top: 8px; }
</style>
