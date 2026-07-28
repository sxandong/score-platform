<template>
  <div>
    <div class="page-header"><h3>考试管理</h3><p>创建和管理考试</p></div>

    <el-button type="primary" @click="openDialog()" style="margin-bottom:16px">创建考试</el-button>

    <el-table :data="exams" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="50" />
      <el-table-column prop="name" label="考试名称" min-width="180" />
      <el-table-column label="类型" width="70">
        <template #default="{ row }">{{ typeLabel(row.exam_type) }}</template>
      </el-table-column>
      <el-table-column prop="enrollment_year" label="入学年份" width="85" />
      <el-table-column prop="grade_name" label="年级" width="70" />
      <el-table-column prop="exam_date" label="日期" width="110" />
      <el-table-column label="科目" min-width="180">
        <template #default="{ row }"><el-tag v-for="s in row.subjects" :key="s.id" size="small" style="margin:2px">{{ s.subject_name }}({{ s.full_score }})</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openDialog(row)">编辑</el-button>
          <el-button size="small" v-if="row.status!=='locked'" @click="lockExam(row.id)">锁定</el-button>
          <el-popconfirm :title="examStats[row.id] > 0 ? '已导入'+examStats[row.id]+'条成绩，确定删除？' : '确定删除？'" @confirm="deleteExam(row.id)">
            <template #reference><el-button size="small" type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showDialog" :title="editing ? '编辑考试' : '创建考试'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.exam_type"><el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" /></el-select>
        </el-form-item>
        <el-form-item label="入学年份">
          <el-select v-model="form.enrollment_year" style="width:100%">
            <el-option v-for="y in yearOptions" :key="y" :label="y+'年'" :value="y" /></el-select>
        </el-form-item>
        <el-form-item label="年级">
          <el-select v-model="form.grade_id" style="width:100%">
            <el-option v-for="g in grades" :key="g.id" :label="g.name" :value="g.id" /></el-select>
        </el-form-item>
        <el-form-item label="考试日期"><el-date-picker v-model="form.exam_date" type="date" style="width:100%" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" @click="saveExam">{{ editing ? '更新' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const exams = ref([]); const loading = ref(false); const showDialog = ref(false)
const editing = ref<any>(null); const grades = ref([])
const yearOptions = Array.from({length:7}, (_,i) => new Date().getFullYear() - 6 + i)
const typeOptions = [
  { value:'monthly',label:'月考'},{ value:'midterm',label:'期中'},{ value:'final',label:'期末'},
  { value:'mock',label:'模拟'},{ value:'other',label:'其他'},
]
const typeLabel = (v:string) => typeOptions.find(t=>t.value===v)?.label||v
const form = reactive({ name:'', exam_type:'midterm', enrollment_year:2026, grade_id:1, exam_date:'', subjects:[] })

onMounted(async () => {
  try { const r = await api.get('/grades'); grades.value = r.data } catch {}
  loadExams()
})

async function loadExams() {
  loading.value = true
  try {
    const r = await api.get('/exams'); exams.value = r.data
    // 加载每个考试的成绩数
    for (const e of exams.value) {
      try {
        const sr = await api.get(`/exams/${e.id}/stats`)
        examStats.value[e.id] = sr.data?.scores || 0
      } catch {}
    }
  } catch {} finally { loading.value = false }
}

function openDialog(row?: any) {
  editing.value = row || null
  if (row) {
    form.name = row.name; form.exam_type = row.exam_type
    form.enrollment_year = row.enrollment_year || 2026
    form.grade_id = row.grade_id || 1
    form.exam_date = row.exam_date || ''
  } else {
    form.name = ''; form.exam_type = 'midterm'
    form.enrollment_year = 2026; form.grade_id = 1; form.exam_date = ''
  }
  showDialog.value = true
}

async function saveExam() {
  try {
    const data: any = {
      name: form.name, exam_type: form.exam_type,
      semester_id: 1, grade_id: Number(form.grade_id),
      enrollment_year: Number(form.enrollment_year),
      exam_date: form.exam_date || undefined,
      subjects: [],
    }
    if (editing.value) {
      await api.put(`/exams/${editing.value.id}`, data)
      ElMessage.success('更新成功')
    } else {
      await api.post('/exams', data)
      ElMessage.success('创建成功')
    }
    showDialog.value = false; editing.value = null; loadExams()
  } catch (e: any) { ElMessage.error(e.message) }
}

const examStats = ref<Record<number, number>>({})
async function deleteExam(id: number) {
  try { await api.delete(`/exams/${id}`); ElMessage.success('已删除'); loadExams() }
  catch (e: any) { ElMessage.error(e.message) }
}
async function lockExam(id: number) {
  try { await api.put(`/exams/${id}/lock`); ElMessage.success('已锁定'); loadExams() }
  catch (e: any) { ElMessage.error(e.message) }
}
</script>

<style scoped>
:deep(.el-table th.el-table__cell) { background: linear-gradient(180deg,#f0f5fa,#e8f0fe); color:var(--edu-blue); font-weight:600; text-align:center; }
:deep(.el-table td) { text-align:center; }
</style>
