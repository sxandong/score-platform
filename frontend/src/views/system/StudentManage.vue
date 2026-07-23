<template>
  <div>
    <h3>学生管理</h3>
    <el-row :gutter="8" style="margin-bottom:16px">
      <el-col :span="4"><el-select v-model="filterClassId" placeholder="按班级筛选" clearable @change="loadStudents">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
      </el-select></el-col>
      <el-col :span="4"><el-input v-model="keyword" placeholder="搜索学号/姓名" clearable @input="loadStudents" /></el-col>
      <el-col :span="4"><el-button type="primary" @click="openDialog()">新增学生</el-button></el-col>
      <el-col :span="4">
        <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls">
          <el-button type="success">Excel批量导入</el-button>
        </el-upload>
      </el-col>
    </el-row>

    <el-table :data="students" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="student_no" label="学号" width="120" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="class_name" label="班级" width="120" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.status==='enrolled'?'success':'info'">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="openDialog(row)">编辑</el-button>
          <el-popconfirm title="确认删除?" @confirm="deleteStudent(row.id)">
            <template #reference><el-button size="small" type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination :current-page="page" :total="total" :page-size="50" layout="total, prev, pager, next"
      @current-change="(p:number) => { page = p; loadStudents() }" style="margin-top:16px;justify-content:flex-end" />

    <el-dialog v-model="dialog" :title="editing ? '编辑学生' : '新增学生'" width="450px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="学号"><el-input v-model="form.student_no" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="班级">
          <el-select v-model="form.class_id">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog=false">取消</el-button>
        <el-button type="primary" @click="saveStudent">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const students = ref<any[]>([]); const classes = ref<any[]>([])
const loading = ref(false); const page = ref(1); const total = ref(0)
const filterClassId = ref<number | null>(null); const keyword = ref('')

const dialog = ref(false); const editing = ref<any>(null)
const form = reactive({ student_no: '', name: '', class_id: 1 })

async function loadClasses() {
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
}
async function loadStudents() {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: 50 }
    if (filterClassId.value) params.class_id = filterClassId.value
    if (keyword.value) params.keyword = keyword.value
    const r = await api.get('/students', { params })
    students.value = r.data; total.value = r.meta.total
  } catch {}
  loading.value = false
}

function openDialog(row?: any) {
  editing.value = row || null
  form.student_no = row?.student_no || ''; form.name = row?.name || ''
  form.class_id = row?.class_id || 1; dialog.value = true
}
async function saveStudent() {
  try {
    if (editing.value) {
      await api.put(`/students/${editing.value.id}`, { ...form })
    } else {
      await api.post('/students', { ...form })
    }
    ElMessage.success('保存成功'); dialog.value = false; loadStudents()
  } catch (e: any) { ElMessage.error(e.message) }
}
async function deleteStudent(id: number) {
  try { await api.delete(`/students/${id}`); ElMessage.success('已删除'); loadStudents() }
  catch (e: any) { ElMessage.error(e.message) }
}
async function handleImport(file: File) {
  const fd = new FormData(); fd.append('file', file)
  try {
    const r = await api.post('/students/batch', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success(r.message); loadStudents()
  } catch (e: any) { ElMessage.error(e.message) }
  return false // prevent auto upload
}

onMounted(() => { loadClasses(); loadStudents() })
</script>
