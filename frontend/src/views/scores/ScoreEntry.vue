<template>
  <div>
    <h3>成绩录入</h3>
    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" @change="loadStudents" style="width:300px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item label="班级"><el-select v-model="classId" placeholder="选择班级" @change="loadStudents" style="width:200px">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select>
      </el-form-item>
    </el-form>
    <el-table :data="scoreRows" border stripe v-if="examId && classId" style="margin-top:16px">
      <el-table-column prop="student_no" label="学籍号" width="120" />
      <el-table-column prop="student_name" label="姓名" width="100" fixed />
      <el-table-column v-for="s in examSubjects" :key="s.id" :label="s.subject_name" width="120">
        <template #default="{ row }">
          <el-input-number v-model="row.scores[s.subject_id]" :min="0" :max="s.full_score" size="small" controls-position="right" />
        </template>
      </el-table-column>
    </el-table>
    <el-button v-if="scoreRows.length" type="primary" @click="submitScores" :loading="submitting" style="margin-top:16px">提交成绩</el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const exams = ref([]); const classes = ref([])
const examId = ref<number | null>(null); const classId = ref<number | null>(null)
const examSubjects = ref<any[]>([]); const scoreRows = ref<any[]>([])
const submitting = ref(false)

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

async function loadStudents() {
  if (!examId.value || !classId.value) return
  try {
    const exr = await api.get(`/exams/${examId.value}`)
    examSubjects.value = exr.data.subjects
    // 从学生API加载班级学生
    const sr = await api.get('/students', { params: { class_id: classId.value, per_page: 100 } })
    scoreRows.value = sr.data.map((s: any) => ({
      student_id: s.id,
      student_no: s.student_no,
      student_name: s.name,
      scores: {},
    }))
  } catch (e: any) { ElMessage.error(e.message) }
}

async function submitScores() {
  submitting.value = true
  try {
    const scores: any[] = []
    scoreRows.value.forEach(row => {
      Object.entries(row.scores).forEach(([subjId, score]) => {
        scores.push({ student_id: row.student_id, subject_id: parseInt(subjId), total_score: score })
      })
    })
    await api.post('/scores', { exam_id: examId.value, scores })
    ElMessage.success('成绩提交成功')
  } catch (e: any) { ElMessage.error(e.message) }
  submitting.value = false
}
</script>
