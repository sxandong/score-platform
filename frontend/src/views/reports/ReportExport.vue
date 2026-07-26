<template>
  <div>
    <div class="page-header"><h3>报表导出</h3><p>成绩单Excel导出与PDF学生报告</p></div>

    <el-card style="margin-bottom:16px">
      <template #header><span style="font-weight:600">导出班级成绩单 (Excel)</span></template>
      <el-form :inline="true">
        <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:250px">
          <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
        </el-form-item>
        <el-form-item label="班级"><el-select v-model="classId" placeholder="选择班级" style="width:200px">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="exportSheet">导出Excel</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <template #header><span style="font-weight:600">导出学生成绩报告 (PDF)</span></template>
      <el-form :inline="true">
        <el-form-item label="学籍号/姓名"><el-input v-model="keyword" placeholder="搜索学生" style="width:250px" clearable /></el-form-item>
        <el-form-item><el-button type="primary" @click="searchStudent">搜索</el-button></el-form-item>
      </el-form>
      <div v-if="studentResults.length" style="margin-bottom:12px">
        <el-radio-group v-model="selectedId">
          <el-radio v-for="s in studentResults" :key="s.id" :value="s.id" border style="margin:4px 8px 4px 0">
            {{ s.name }} ({{ s.student_no }}) - {{ s.class_name }}
          </el-radio>
        </el-radio-group>
      </div>
      <el-button type="success" :disabled="!selectedId" @click="exportPDF">导出PDF报告</el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const exams = ref([]); const classes = ref([])
const examId = ref<number | null>(null); const classId = ref<number | null>(null)
const keyword = ref(''); const studentResults = ref<any[]>([])
const selectedId = ref<number | null>(null)

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

function exportSheet() {
  if (!examId.value || !classId.value) { ElMessage.warning('请选择考试和班级'); return }
  window.open(`/api/reports/score-sheet?exam_id=${examId.value}&class_id=${classId.value}`)
  ElMessage.success('开始下载')
}

async function searchStudent() {
  if (!keyword.value) return
  try {
    const r = await api.get('/students', { params: { keyword: keyword.value, per_page: 20 } })
    studentResults.value = r.data
  } catch {}
}

function exportPDF() {
  if (!selectedId.value) return
  window.open(`/api/reports/student-report?student_id=${selectedId.value}`)
  ElMessage.success('PDF报告生成中，请稍候...')
}
</script>
