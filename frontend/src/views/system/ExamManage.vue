<template>
  <div>
    <h3>考试管理</h3>
    <el-button type="primary" @click="showDialog = true" style="margin-bottom:16px">创建考试</el-button>
    <el-table :data="exams" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="考试名称" />
      <el-table-column prop="exam_type" label="类型" width="100" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.status==='locked'?'danger':'success'">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="exam_date" label="日期" width="120" />
      <el-table-column label="科目" min-width="200">
        <template #default="{ row }"><el-tag v-for="s in row.subjects" :key="s.id" size="small" style="margin-right:4px">{{ s.subject_name }}({{ s.full_score }})</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button size="small" v-if="row.status!=='locked'" @click="lockExam(row.id)">锁定</el-button>
          <el-button size="small" type="primary" @click="$router.push(`/scores/entry?exam_id=${row.id}`)">录成绩</el-button>
          <el-popconfirm :title="deleteMsg(row)" @confirm="deleteExam(row.id)">
            <template #reference>
              <el-button size="small" type="danger" :disabled="row.status==='locked'">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showDialog" title="创建考试" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.exam_type"><el-option v-for="t in types" :key="t" :label="t" :value="t" /></el-select>
        </el-form-item>
        <el-form-item label="考试日期"><el-date-picker v-model="form.exam_date" type="date" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="createExam">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const exams = ref([]); const loading = ref(false); const showDialog = ref(false)
const types = ['monthly', 'midterm', 'final', 'mock', 'other']
const form = reactive({ name: '', exam_type: 'midterm', exam_date: '', semester_id: 1, grade_id: 1, subjects: [] })

async function loadExams() {
  loading.value = true
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  loading.value = false
}

async function createExam() {
  try {
    await api.post('/exams', { ...form })
    ElMessage.success('创建成功'); showDialog.value = false
    form.name = ''; loadExams()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function lockExam(id: number) {
  try { await api.put(`/exams/${id}/lock`); ElMessage.success('已锁定'); loadExams() }
  catch (e: any) { ElMessage.error(e.message) }
}

const examStats = ref<Record<number, number>>({})

async function deleteMsg(row: any): Promise<string> {
  try {
    const r = await api.get(`/exams/${row.id}/stats`)
    const cnt = r.data.scores || 0
    examStats.value[row.id] = cnt
    return cnt > 0
      ? `此考试已导入 ${cnt} 条成绩，删除考试将同时删除全部成绩数据，确定删除？`
      : '确定删除此考试？'
  } catch { return '确定删除此考试？' }
}

async function deleteExam(id: number) {
  try { await api.delete(`/exams/${id}`); ElMessage.success('已删除'); loadExams() }
  catch (e: any) { ElMessage.error(e.message) }
}

onMounted(() => loadExams())
</script>
