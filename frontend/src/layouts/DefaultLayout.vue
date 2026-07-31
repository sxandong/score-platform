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
        <el-menu-item v-if="auth.hasRole('admin') || auth.hasRole('director')" index="/grades-classes">
          <el-icon><School /></el-icon><span>年级班级</span>
        </el-menu-item>
        <el-menu-item v-if="auth.hasRole('admin') || auth.hasRole('director')" index="/students">
          <el-icon><Avatar /></el-icon><span>学生管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.hasRole('admin') || auth.hasRole('director')" index="/electives">
          <el-icon><Collection /></el-icon><span>选科管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.hasPermission('exam:read')" index="/exams">
          <el-icon><Document /></el-icon><span>考试管理</span>
        </el-menu-item>
        <el-sub-menu v-if="auth.hasPermission('score:create') || auth.hasPermission('score:read')" index="scores">
          <template #title><el-icon><Edit /></el-icon><span>成绩管理</span></template>
          <el-menu-item v-if="auth.hasPermission('score:create')" index="/scores/entry">成绩录入</el-menu-item>
          <el-menu-item v-if="auth.hasPermission('score:create')" index="/scores/import">批量导入</el-menu-item>
          <el-menu-item index="/scores/cutoffs">分数线设置</el-menu-item>
          <el-menu-item v-if="auth.hasPermission('score:read')" index="/scores/query">成绩查询</el-menu-item>
        </el-sub-menu>
        <el-sub-menu v-if="auth.hasPermission('analysis:view')" index="analysis">
          <template #title><el-icon><TrendCharts /></el-icon><span>统计分析</span></template>
          <el-menu-item index="/analysis/class-compare">班级达线统计</el-menu-item>
          <el-menu-item index="/analysis/multi-exam-compare">班级达线对比</el-menu-item>
          <el-menu-item index="/analysis/score-distribution">各学科分数段</el-menu-item>
          <el-menu-item index="/analysis/student-rank-stats">学生排名统计</el-menu-item>
          <el-menu-item index="/analysis/student-trend">学校三线趋势</el-menu-item>
        </el-sub-menu>
        <el-menu-item v-if="auth.hasPermission('report:export')" index="/reports">
          <el-icon><Download /></el-icon><span>报表导出</span>
        </el-menu-item>
        <el-menu-item v-if="auth.hasRole('admin')" index="/data-backup">
          <el-icon><FolderOpened /></el-icon><span>数据备份</span>
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
          <el-dropdown trigger="click">
            <span style="display:flex;align-items:center;gap:6px;cursor:pointer;color:var(--tx-secondary);font-size:13px">
              <el-icon><UserFilled /></el-icon> {{ auth.user?.real_name || '用户' }}
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
      <el-main style="background:var(--bg-page);padding:20px 24px;overflow-y:auto">
        <router-view />
      </el-main>
    </el-container>

    <!-- 修改密码对话框 -->
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
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
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

<style scoped>
.el-menu-item.is-active { background: rgba(255,255,255,.12) !important; border-left: 3px solid #fff; }
.el-sub-menu .el-menu-item { padding-left: 52px !important; }
</style>