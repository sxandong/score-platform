<template>
  <div class="login-page">
    <div class="login-bg"></div>
    <el-card class="login-card">
      <div class="login-logo">成绩管理平台</div>
      <div class="login-sub">普通高中教学质量分析系统</div>

      <!-- 账号密码登录 -->
      <div v-if="tab === 'account'">
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
      </div>

      <!-- 钉钉扫码登录 -->
      <div v-else class="dingtalk-section">
        <div v-if="!ddConfig?.enabled" class="dingtalk-disabled">
          <el-icon :size="48" color="#999"><InfoFilled /></el-icon>
          <div>钉钉登录暂未开放</div>
        </div>
        <div v-else>
          <div id="dingtalk-login-container" class="dd-qr-container"></div>
          <div class="dd-tip">请使用钉钉扫一扫登录</div>
        </div>
      </div>

      <div class="login-tabs">
        <el-button :type="tab === 'account' ? 'primary' : 'default'" style="flex:1; margin-left:0; margin-right:0" @click="tab = 'account'">账号登录</el-button>
        <el-button v-if="ddConfig?.enabled" :type="tab === 'dingtalk' ? 'primary' : 'default'" style="flex:1; margin-left:0; margin-right:0" @click="switchToDingtalk">钉钉扫码</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'

const router = useRouter(); const authStore = useAuthStore()
const loading = ref(false); const formRef = ref()
const tab = ref<'account' | 'dingtalk'>('account')
const ddConfig = ref<any>(null)
const ddLoaded = ref(false)  // 钉钉SDK是否已加载
const ddInitializing = ref(false)  // 是否正在初始化二维码
const ddLoginPending = ref(false)  // 防止authCode重复提交

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

onMounted(async () => {
  try {
    const r = await authStore.api_get('/auth/dingtalk/config')
    ddConfig.value = r
  } catch { ddConfig.value = { enabled: false } }
})

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return; loading.value = true
  try {
    const res = await authStore.login(form.username, form.password)
    if (res.user.must_change_password) {
      ElMessage.warning('首次登录请修改密码')
      router.push('/change-password')
    } else {
      ElMessage.success('登录成功')
      router.push('/dashboard')
    }
  }
  catch (e: any) { ElMessage.error(e.message || '登录失败') }
  finally { loading.value = false }
}

// 切换到钉钉登录Tab
async function switchToDingtalk() {
  tab.value = 'dingtalk'
  await nextTick()
  await initDingtalkQr()
}

// 动态加载钉钉JS SDK
async function loadDingtalkScript(): Promise<void> {
  if (ddLoaded.value || (window as any).DTFrameLogin) {
    ddLoaded.value = true
    return
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://g.alicdn.com/dingding/h5-dingtalk-login/0.21.0/ddlogin.js'
    script.onload = () => {
      ddLoaded.value = true
      resolve()
    }
    script.onerror = () => reject(new Error('加载钉钉SDK失败'))
    document.head.appendChild(script)
  })
}

// 初始化钉钉内嵌二维码
async function initDingtalkQr() {
  if (!ddConfig.value?.enabled || ddInitializing.value) return
  ddInitializing.value = true
  try {
    await loadDingtalkScript()
    const DTFrameLogin = (window as any).DTFrameLogin
    if (!DTFrameLogin) {
      ElMessage.error('钉钉SDK加载失败')
      return
    }
    // 清空容器（避免重复初始化）
    const container = document.getElementById('dingtalk-login-container')
    if (container) container.innerHTML = ''
    const redirectUri = window.location.origin + '/dingtalk/callback'
    DTFrameLogin(
      {
        id: 'dingtalk-login-container',
        width: 300,
        height: 300,
      },
      {
        redirect_uri: encodeURIComponent(redirectUri),
        client_id: ddConfig.value.app_key,
        scope: 'openid',
        response_type: 'code',
        state: Math.random().toString(36).substring(2),
        prompt: 'consent',
      },
      (loginResult: any) => {
        // 扫码登录成功，获取 authCode（防止重复回调）
        if (ddLoginPending.value) return
        const authCode = loginResult?.authCode || loginResult?.code
        if (authCode) {
          ddLoginPending.value = true
          handleDingtalkLogin(authCode)
        }
      },
      (errorMsg: string) => {
        ElMessage.error('钉钉登录失败: ' + errorMsg)
      }
    )
  } catch (e: any) {
    ElMessage.error(e.message || '钉钉二维码加载失败')
  } finally {
    ddInitializing.value = false
  }
}

// 用 authCode 调用后端完成登录
async function handleDingtalkLogin(authCode: string) {
  loading.value = true
  try {
    const res = await authStore.dingtalkLogin(authCode)
    if (res.user?.must_change_password) {
      ElMessage.warning('首次登录请修改密码')
      router.push('/change-password')
    } else {
      ElMessage.success('登录成功')
      router.push('/dashboard')
    }
  } catch (e: any) {
    // 非本单位用户等错误，弹窗提示
    ElMessageBox.alert(
      e.message || '钉钉登录失败',
      '登录失败',
      { confirmButtonText: '我知道了', type: 'error' }
    ).catch(() => {})
    // 重新加载二维码，允许重试
    await nextTick()
    initDingtalkQr()
  } finally {
    loading.value = false
    ddLoginPending.value = false
  }
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
.login-tabs {
  display: flex; flex-direction: row; gap: 12px; margin-top: 20px;
  border-top: 1px solid #ebeef5; padding-top: 16px;
}

.dingtalk-section { margin-top: 24px; min-height: 340px; }
.dd-qr-container {
  width: 300px; height: 300px; margin: 16px auto 8px;
  display: flex; justify-content: center; align-items: center;
}
.dd-qr-container :deep(iframe) { border: none; }
.dd-tip { text-align: center; font-size: 12px; color: var(--tx-secondary); margin-bottom: 12px; }
.dingtalk-disabled { text-align: center; padding: 40px 0; color: var(--tx-secondary); }
</style>
