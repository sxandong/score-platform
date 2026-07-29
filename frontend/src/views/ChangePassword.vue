<template>
  <div class="change-password-page">
    <div class="login-bg"></div>
    <el-card class="change-password-card">
      <div class="logo">成绩管理平台</div>
      <div class="sub">首次登录需修改初始密码</div>
      <el-alert type="warning" :closable="false" show-icon style="margin:16px 0">
        <p>您的账号使用的是初始密码 <b>123456</b>，为了账号安全，请立即修改密码。</p>
      </el-alert>
      <el-form :model="form" :rules="rules" ref="formRef" style="margin-top:16px">
        <el-form-item prop="old_password">
          <el-input v-model="form.old_password" type="password" placeholder="原密码（当前密码）" show-password size="large" />
        </el-form-item>
        <el-form-item prop="new_password">
          <el-input v-model="form.new_password" type="password" placeholder="新密码（至少6位）" show-password size="large" />
        </el-form-item>
        <el-form-item prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" placeholder="确认新密码" show-password size="large" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit" size="large" style="width:100%">
            确认修改
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
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ old_password: '123456', new_password: '', confirm_password: '' })

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 6, message: '新密码至少6位', trigger: 'blur' }],
  confirm_password: [{ required: true, validator: validateConfirm, trigger: 'blur' }],
}

async function handleSubmit() {
  const valid = await formRef.value!.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.changePassword(form.old_password, form.new_password)
    ElMessage.success('密码修改成功，请重新登录')
    authStore.logout()
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e.message || '修改失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-password-page {
  display: flex; justify-content: center; align-items: center; height: 100vh;
  background: linear-gradient(135deg, #1a5490 0%, #1e3a5f 60%, #0d2137 100%);
  position: relative; overflow: hidden;
}
.login-bg {
  position: absolute; top: -50%; right: -30%; width: 800px; height: 800px;
  background: rgba(255,255,255,.03); border-radius: 50%; pointer-events: none;
}
.change-password-card {
  width: 440px; border-radius: 12px; padding: 24px;
  box-shadow: 0 8px 32px rgba(0,0,0,.18);
}
.logo {
  text-align: center; font-size: 24px; font-weight: 700; color: var(--edu-blue);
  margin-top: 8px; letter-spacing: 4px;
}
.sub {
  text-align: center; font-size: 13px; color: var(--tx-secondary); margin-top: 4px;
}
</style>