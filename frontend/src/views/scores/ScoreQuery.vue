<template>
  <div>
    <h3>成绩查询</h3>
    <el-tabs v-model="mode">
      <el-tab-pane label="按班级查询" name="class" />
      <el-tab-pane label="按学生查询" name="student" />
    </el-tabs>

    <!-- 按班级 -->
    <el-form :inline="true" v-if="mode==='class'">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:250px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item label="班级"><el-select v-model="classId" placeholder="选择班级" style="width:200px">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select>
      </el-form-item>
      <el-form-item><el-button type="primary" @click="loadClassScores">查询</el-button></el-form-item>
    </el-form>

    <!-- 按学生 -->
    <el-form :inline="true" v-if="mode==='student'">
      <el-form-item label="考试"><el-select v-model="examId2" placeholder="选择考试" style="width:250px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item label="学籍号/姓名"><el-input v-model="studentKeyword" placeholder="输入学籍号或姓名搜索" style="width:250px"
        clearable @keyup.enter="searchStudent" /></el-form-item>
      <el-form-item><el-button type="primary" @click="searchStudent" :loading="searching">搜索</el-button></el-form-item>
    </el-form>

    <!-- 学生搜索结果 -->
    <div v-if="mode==='student' && studentResults.length" style="margin-bottom:16px">
      <el-radio-group v-model="selectedStudentId" @change="loadStudentScores">
        <el-radio v-for="s in studentResults" :key="s.id" :value="s.id" border style="margin:4px 8px 4px 0">
          {{ s.name }} ({{ s.student_no }}) - {{ s.class_name }}
        </el-radio>
      </el-radio-group>
    </div>

    <!-- 成绩表格 -->
    <el-table :data="scoreData" border stripe v-if="scoreData.length" v-loading="loading">
      <el-table-column v-if="mode==='class'" prop="student_no" label="学籍号" width="120" />
      <el-table-column v-if="mode==='class'" prop="student_name" label="姓名" width="100" />
      <el-table-column v-for="(v,k) in scoreCols" :key="k" :label="k" width="100">
        <template #default="{ row }">
          <template v-if="mode==='class'">{{ row.subjects[k] }}</template>
          <template v-else>{{ row.subjects[k] }}</template>
        </template>
      </el-table-column>
      <el-table-column v-if="mode==='class'" prop="total" label="总分" width="100" />
      <el-table-column v-if="mode==='class'" prop="class_rank" label="班级排名" width="100" />
      <el-table-column prop="grade_rank" :label="mode==='class'?'年级排名':'年级排名'" width="100" />
      <el-table-column v-if="mode==='student'" prop="exam_name" label="考试" width="180" />
      <el-table-column v-if="mode==='student'">
        <template #default="{ row }">
          <el-tag v-for="(sv, sk) in row.subjects" :key="sk" size="small" style="margin:2px">
            {{ sk }}: {{ sv }}
          </el-tag>
          <el-tag type="primary" size="small" style="margin:2px">总分: {{ row.total }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else :description="mode==='class' ? '请选择考试和班级后查询' : '请输入学籍号或姓名搜索'" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/api'

const mode = ref('class')
const exams = ref([]); const classes = ref([])
const examId = ref<number | null>(null); const classId = ref<number | null>(null)
const examId2 = ref<number | null>(null)
const studentKeyword = ref(''); const searching = ref(false)
const studentResults = ref<any[]>([]); const selectedStudentId = ref<number | null>(null)
const scoreData = ref<any[]>([]); const loading = ref(false)

const scoreCols = computed(() => {
  if (!scoreData.value.length) return {}
  return scoreData.value[0]?.subjects || {}
})

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

async function loadClassScores() {
  if (!examId.value || !classId.value) return
  loading.value = true
  try {
    const r = await api.get(`/scores/class/${classId.value}/exam/${examId.value}`)
    scoreData.value = r.data
  } catch {} finally { loading.value = false }
}

async function searchStudent() {
  if (!studentKeyword.value) return
  searching.value = true; studentResults.value = []
  try {
    const r = await api.get('/students', { params: { keyword: studentKeyword.value, per_page: 20 } })
    studentResults.value = r.data
    if (r.data.length === 1) {
      selectedStudentId.value = r.data[0].id
      await loadStudentScores()
    }
  } catch {} finally { searching.value = false }
}

async function loadStudentScores() {
  if (!selectedStudentId.value) return
  loading.value = true
  try {
    const params: any = { student_id: selectedStudentId.value }
    const r = await api.get('/analysis/student-trend', { params })
    // 如果选了考试就只显示该考试
    if (examId2.value) {
      scoreData.value = r.data.filter((x: any) => x.exam_id === examId2.value)
    } else {
      scoreData.value = r.data
    }
  } catch {} finally { loading.value = false }
}
</script>
