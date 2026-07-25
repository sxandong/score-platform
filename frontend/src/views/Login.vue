<template>
  <div class="login-page">
    <div class="login-bg"></div>
    <el-card class="login-card">
      <div class="login-logo">成绩管理平台</div>
      <div class="login-sub">普通高中教学质量分析系统</div>
      <el-form :model="form" :rules="rules" ref="formRef" style="margin-top:32px">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock"
            show-password size="large" @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleLogin" size="large" style="width:100%">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter(); const authStore = useAuthStore()
const loading = ref(false); const formRef = ref()
const form = reactive({ username: 'admin', password: 'admin123' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return; loading.value = true
  try { await authStore.login(form.username, form.password); ElMessage.success('登录成功'); router.push('/dashboard') }
  catch (e: any) { ElMessage.error(e.message || '登录失败') }
  finally { loading.value = false }
}
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
  width: 400px; border-radius: 12px; padding: 8px 8px 24px;
  box-shadow: 0 8px 32px rgba(0,0,0,.18);
}
.login-logo {
  text-align: center; font-size: 24px; font-weight: 700; color: var(--edu-blue);
  margin-top: 8px; letter-spacing: 4px;
}
.login-sub {
  text-align: center; font-size: 13px; color: var(--tx-secondary); margin-top: 8px;
}
</style>
