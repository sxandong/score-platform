<template>
  <div>
    <h3>成绩查询</h3>
    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:250px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item label="班级"><el-select v-model="classId" placeholder="选择班级" style="width:200px">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select>
      </el-form-item>
      <el-form-item><el-button type="primary" @click="loadScores">查询</el-button></el-form-item>
    </el-form>
    <el-table :data="scoreData" border stripe v-if="scoreData.length" v-loading="loading">
      <el-table-column prop="student_no" label="学号" width="120" />
      <el-table-column prop="student_name" label="姓名" width="100" />
      <el-table-column v-for="(v,k) in scoreData[0]?.subjects" :key="k" :label="k" width="100">
        <template #default="{ row }">{{ row.subjects[k] }}</template>
      </el-table-column>
      <el-table-column prop="total" label="总分" width="100" />
      <el-table-column prop="class_rank" label="班级排名" width="100" />
      <el-table-column prop="grade_rank" label="年级排名" width="100" />
    </el-table>
    <el-empty v-else description="请选择考试和班级后查询" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'

const exams = ref([]); const classes = ref([])
const examId = ref<number | null>(null); const classId = ref<number | null>(null)
const scoreData = ref([]); const loading = ref(false)

onMounted(async () => { try { const r = await api.get('/exams'); exams.value = r.data } catch {} })

async function loadScores() {
  if (!examId.value || !classId.value) return
  loading.value = true
  try { const r = await api.get(`/scores/class/${classId.value}/exam/${examId.value}`); scoreData.value = r.data }
  catch (e: any) {}
  loading.value = false
}
</script>
