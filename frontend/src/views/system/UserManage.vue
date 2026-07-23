<template>
  <div>
    <h3>用户管理</h3>
    <el-button type="primary" @click="showDialog = true" style="margin-bottom:16px">新增用户</el-button>
    <el-table :data="users" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="real_name" label="姓名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column label="角色">
        <template #default="{ row }"><el-tag v-for="r in row.roles" :key="r" size="small" style="margin-right:4px">{{ r }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="editUser(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination :current-page="page" :total="total" :page-size="20" layout="total, prev, pager, next"
      @current-change="loadUsers" style="margin-top:16px;justify-content:flex-end" />

    <el-dialog v-model="showDialog" :title="editing ? '编辑用户' : '新增用户'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item v-if="!editing" label="密码"><el-input v-model="form.password" type="password" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.real_name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_codes" multiple>
            <el-option v-for="r in allRoles" :key="r.code" :label="r.name" :value="r.code" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const users = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const showDialog = ref(false)
const editing = ref<any>(null)
const form = reactive({ username: '', password: '', real_name: '', role_codes: [] as string[] })
const allRoles = [
  { code: 'admin', name: '管理员' }, { code: 'director', name: '教学主管' },
  { code: 'teacher', name: '教师' }, { code: 'student', name: '学生' }, { code: 'parent', name: '家长' },
]

async function loadUsers(p = 1) {
  loading.value = true; page.value = p
  try { const r = await api.get('/users', { params: { page: p } }); users.value = r.data; total.value = r.meta.total } catch {}
  loading.value = false
}

function editUser(row: any) {
  editing.value = row; form.username = row.username; form.real_name = row.real_name
  form.role_codes = [...row.roles]; showDialog.value = true
}

async function saveUser() {
  try {
    if (editing.value) {
      await api.put(`/users/${editing.value.id}`, { real_name: form.real_name, role_codes: form.role_codes })
      ElMessage.success('更新成功')
    } else {
      await api.post('/users', { ...form })
      ElMessage.success('创建成功')
    }
    showDialog.value = false; editing.value = null
    form.username = ''; form.password = ''; form.real_name = ''; form.role_codes = []
    loadUsers(page.value)
  } catch (e: any) { ElMessage.error(e.message) }
}

onMounted(() => loadUsers())
</script>
