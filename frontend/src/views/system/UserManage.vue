<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h3 style="margin:0">用户管理</h3>
      <div>
        <el-button type="primary" @click="openCreateDialog">新增用户</el-button>
        <el-button @click="downloadTemplate">下载模板</el-button>
        <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls" style="display:inline-block">
          <el-button type="success">Excel导入教师</el-button>
        </el-upload>
      </div>
    </div>

    <div style="margin-bottom:16px;display:flex;gap:12px;align-items:center">
      <el-input v-model="searchParams.keyword" placeholder="搜索用户名/姓名/手机/邮箱" clearable style="width:260px" @keyup.enter="handleSearch" />
      <el-select v-model="searchParams.role" placeholder="角色筛选" clearable style="width:140px">
        <el-option v-for="r in allRoles" :key="r.code" :label="r.name" :value="r.code" />
      </el-select>
      <el-select v-model="searchParams.status" placeholder="状态筛选" clearable style="width:120px">
        <el-option label="启用" value="active" />
        <el-option label="禁用" value="disabled" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="handleResetSearch">重置</el-button>
      <el-button v-if="selectedIds.length > 0 && isAdmin" type="warning" @click="openBatchResetDialog">
        批量重置密码 ({{ selectedIds.length }})
      </el-button>
      <el-button v-if="selectedIds.length > 0 && isAdmin" type="danger" @click="handleBatchDelete">
        批量删除 ({{ selectedIds.length }})
      </el-button>
    </div>

    <el-table :data="users" border stripe v-loading="loading" @selection-change="handleSelectionChange" size="small">
      <el-table-column type="selection" width="45" />
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="real_name" label="姓名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column label="角色">
        <template #default="{ row }">
          <el-tag v-for="r in row.roles" :key="r" size="small" style="margin-right:4px">
            {{ getRoleName(r) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
            {{ row.status === 'active' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button size="small" @click="editUser(row)">编辑</el-button>
          <el-button v-if="isAdmin" size="small" type="warning" @click="openResetDialog(row)">重置密码</el-button>
          <el-button v-if="isAdmin" size="small" type="danger" :disabled="row.username === 'admin'" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination :current-page="page" :total="total" :page-size="20" layout="total, prev, pager, next"
      @current-change="loadUsers" style="margin-top:16px;justify-content:flex-end" />

    <!-- 新增/编辑用户 -->
    <el-dialog v-model="showDialog" :title="editing ? '编辑用户' : '新增用户'" width="500px" @close="handleDialogClose">
      <el-form ref="userFormRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item label="用户名" prop="username"><el-input v-model="form.username" /></el-form-item>
        <el-form-item v-if="!editing" label="密码" prop="password"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item label="姓名" prop="real_name"><el-input v-model="form.real_name" /></el-form-item>
        <el-form-item label="手机"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="角色" prop="role_codes">
          <el-select v-model="form.role_codes" multiple>
            <el-option v-for="r in allRoles" :key="r.code" :label="r.name" :value="r.code" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editing" label="状态">
          <el-select v-model="form.status">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置单个用户密码 -->
    <el-dialog v-model="showResetDialog" title="重置用户密码" width="420px">
      <p>将用户 <strong>{{ resetTarget?.real_name || resetTarget?.username }}</strong> 的密码重置为</p>
      <el-alert type="info" :closable="false" show-icon>
        <template #title>
          <span style="font-size:18px;font-weight:700;letter-spacing:2px">123456</span>
        </template>
      </el-alert>
      <p style="margin-top:12px;font-size:13px;color:var(--tx-secondary)">用户下次登录需修改密码</p>
      <template #footer>
        <el-button @click="showResetDialog = false">取消</el-button>
        <el-button type="primary" @click="submitResetPassword">确认重置</el-button>
      </template>
    </el-dialog>

    <!-- 批量重置密码 -->
    <el-dialog v-model="showBatchResetDialog" title="批量重置密码" width="420px">
      <p>将 <strong>{{ selectedIds.length }}</strong> 个用户的密码重置为</p>
      <el-alert type="info" :closable="false" show-icon>
        <template #title>
          <span style="font-size:18px;font-weight:700;letter-spacing:2px">123456</span>
        </template>
      </el-alert>
      <p style="margin-top:12px;font-size:13px;color:var(--tx-secondary)">用户下次登录需修改密码</p>
      <template #footer>
        <el-button @click="showBatchResetDialog = false">取消</el-button>
        <el-button type="primary" @click="submitBatchResetPassword">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const isAdmin = computed(() => auth.hasRole('admin'))

const users = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const selectedIds = ref<number[]>([])
const showDialog = ref(false)
const editing = ref<any>(null)
const showResetDialog = ref(false)
const showBatchResetDialog = ref(false)
const resetTarget = ref<any>(null)

const searchParams = reactive({ keyword: '', role: '', status: '' })
const userFormRef = ref<FormInstance>()
const form = reactive({ username: '', password: '', real_name: '', phone: '', role_codes: [] as string[], status: 'active' })
const formRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role_codes: [{ required: true, type: 'array', message: '请选择角色', trigger: 'change' }],
}

const allRoles = [
  { code: 'admin', name: '管理员' },
  { code: 'director', name: '教学主管' },
  { code: 'teacher', name: '教师' },
  { code: 'student', name: '学生' },
  { code: 'parent', name: '家长' },
]

const roleMap: Record<string, string> = {
  admin: '管理员', director: '教学主管', teacher: '教师', student: '学生', parent: '家长',
}

function getRoleName(code: string) {
  return roleMap[code] || code
}

async function loadUsers(p = 1) {
  loading.value = true; page.value = p
  try {
    const params: any = { page: p }
    if (searchParams.keyword) params.keyword = searchParams.keyword
    if (searchParams.role) params.role = searchParams.role
    if (searchParams.status) params.status = searchParams.status
    const r = await api.get('/users', { params })
    users.value = r.data
    total.value = r.meta.total
  } catch {}
  loading.value = false
}

function handleSearch() {
  loadUsers(1)
}

function handleResetSearch() {
  searchParams.keyword = ''
  searchParams.role = ''
  searchParams.status = ''
  loadUsers(1)
}

function handleSelectionChange(rows: any[]) {
  selectedIds.value = rows.map(r => r.id)
}

function editUser(row: any) {
  editing.value = row
  form.username = row.username
  form.real_name = row.real_name
  form.phone = row.phone || ''
  form.role_codes = [...row.roles]
  form.status = row.status || 'active'
  nextTick(() => userFormRef.value?.clearValidate())
  showDialog.value = true
}

function openCreateDialog() {
  editing.value = null
  form.username = ''
  form.password = ''
  form.real_name = ''
  form.phone = ''
  form.role_codes = []
  form.status = 'active'
  nextTick(() => userFormRef.value?.clearValidate())
  showDialog.value = true
}

function handleDialogClose() {
  editing.value = null
  form.username = ''
  form.password = ''
  form.real_name = ''
  form.phone = ''
  form.role_codes = []
  form.status = 'active'
  userFormRef.value?.resetFields()
}

async function saveUser() {
  if (!userFormRef.value) return
  await userFormRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      if (editing.value) {
        const payload: any = { real_name: form.real_name, phone: form.phone, role_codes: form.role_codes }
        if (form.status) payload.status = form.status
        await api.put(`/users/${editing.value.id}`, payload)
        ElMessage.success('更新成功')
      } else {
        await api.post('/users', { ...form })
        ElMessage.success('创建成功')
      }
      showDialog.value = false
      editing.value = null
      form.username = ''
      form.password = ''
      form.real_name = ''
      form.phone = ''
      form.role_codes = []
      form.status = 'active'
      loadUsers(page.value)
    } catch (e: any) { ElMessage.error(e.message) }
  })
}

function openResetDialog(row: any) {
  resetTarget.value = row
  showResetDialog.value = true
}

async function submitResetPassword() {
  try {
    await api.post(`/users/${resetTarget.value.id}/reset-password`)
    ElMessage.success('密码已重置为123456')
    showResetDialog.value = false
  } catch (e: any) { ElMessage.error(e.message) }
}

function openBatchResetDialog() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择用户')
    return
  }
  showBatchResetDialog.value = true
}

async function submitBatchResetPassword() {
  try {
    await api.post('/users/batch-reset-password', {
      user_ids: selectedIds.value,
    })
    ElMessage.success('批量重置成功，密码已设为123456')
    showBatchResetDialog.value = false
    selectedIds.value = []
    loadUsers(page.value)
  } catch (e: any) { ElMessage.error(e.message) }
}

function downloadTemplate() {
  window.open('/api/users/download-template', '_blank')
}

async function handleImport(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  try {
    const r = await api.post('/users/batch', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success(r.message)
    loadUsers(page.value)
  } catch (e: any) { ElMessage.error(e.message) }
  return false
}

function handleDelete(row: any) {
  ElMessageBox.confirm(
    `确定要删除用户「${row.real_name || row.username}」吗？此操作不可恢复。`,
    '删除确认',
    { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await api.delete(`/users/${row.id}`)
      ElMessage.success('删除成功')
      loadUsers(page.value)
    } catch (e: any) { ElMessage.error(e.message) }
  }).catch(() => {})
}

function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的用户')
    return
  }
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedIds.value.length} 个用户吗？此操作不可恢复。`,
    '批量删除确认',
    { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await api.post('/users/batch-delete', { user_ids: selectedIds.value })
      ElMessage.success('批量删除成功')
      selectedIds.value = []
      loadUsers(page.value)
    } catch (e: any) { ElMessage.error(e.message) }
  }).catch(() => {})
}

onMounted(() => loadUsers())
</script>