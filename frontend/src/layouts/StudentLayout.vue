<template>
  <el-container style="height:100vh">
    <el-header style="background:#409EFF;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 20px">
      <span style="font-size:18px;font-weight:bold">成绩管理平台 - 学生端</span>
      <div style="display:flex;align-items:center;gap:16px">
        <el-dropdown trigger="click">
          <span style="display:flex;align-items:center;gap:6px;cursor:pointer">
            {{ auth.user?.real_name }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="showChangePwdDialog = true">
                <el-icon><Lock /></el-icon>修改密码
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-main><router-view /></el-main>

    <el-dialog v-model="showChangePwdDialog" title="修改密码" width="420px">
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pwdForm.confirm_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChangePwdDialog = false">取消</el-button>
        <el-button type="primary" @click="submitChangePassword">确认修改</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()

const showChangePwdDialog = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

function handleLogout() {
  auth.logout()
  router.push('/login')
}

async function submitChangePassword() {
  if (!pwdForm.old_password || pwdForm.old_password.length < 6) {
    ElMessage.warning('请输入原密码')
    return
  }
  if (!pwdForm.new_password || pwdForm.new_password.length < 6) {
    ElMessage.warning('新密码至少6位')
    return
  }
  if (pwdForm.new_password !== pwdForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (pwdForm.old_password === pwdForm.new_password) {
    ElMessage.warning('新密码不能与原密码相同')
    return
  }
  try {
    await api.post('/auth/change-password', {
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    ElMessage.success('密码修改成功，请重新登录')
    showChangePwdDialog.value = false
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
    auth.logout()
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}
</script>