<template>
  <div>
    <h3>成绩趋势</h3>
    <el-form :inline="true">
      <el-form-item label="学生ID"><el-input-number v-model="studentId" :min="1" /></el-form-item>
      <el-form-item><el-button type="primary" @click="loadData">查询</el-button></el-form-item>
    </el-form>
    <el-table :data="trendData" border stripe v-if="trendData.length" v-loading="loading" style="margin-top:16px">
      <el-table-column prop="exam_name" label="考试" />
      <el-table-column prop="exam_date" label="日期" width="120" />
      <el-table-column prop="total_score" label="总分" width="100" />
      <el-table-column prop="grade_rank" label="年级排名" width="100" />
    </el-table>
    <el-empty v-else description="请输入学生ID查询成绩趋势" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api'

const studentId = ref<number | null>(null)
const trendData = ref([]); const loading = ref(false)

async function loadData() {
  if (!studentId.value) return; loading.value = true
  try { const r = await api.get('/analysis/student-trend', { params: { student_id: studentId.value } }); trendData.value = r.data }
  catch {}
  loading.value = false
}
</script>
