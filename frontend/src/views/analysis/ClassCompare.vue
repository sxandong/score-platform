<template>
  <div>
    <h3>班级对比分析</h3>
    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:250px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item><el-button type="primary" @click="loadData">分析</el-button></el-form-item>
    </el-form>
    <el-table :data="compareData" border stripe v-if="compareData.length" v-loading="loading" style="margin-top:16px">
      <el-table-column prop="class_name" label="班级" width="120" />
      <el-table-column prop="avg_score" label="平均分" width="100" />
      <el-table-column prop="max_score" label="最高分" width="100" />
      <el-table-column prop="min_score" label="最低分" width="100" />
      <el-table-column prop="excellent_rate" label="优秀率(%)" width="120" />
      <el-table-column prop="pass_rate" label="及格率(%)" width="120" />
      <el-table-column prop="student_count" label="人数" width="80" />
    </el-table>
    <el-empty v-else description="请选择考试后查看班级对比分析" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'

const exams = ref([]); const examId = ref<number | null>(null)
const compareData = ref([]); const loading = ref(false)

onMounted(async () => { try { const r = await api.get('/exams'); exams.value = r.data } catch {} })

async function loadData() {
  if (!examId.value) return; loading.value = true
  try { const r = await api.get('/analysis/class-compare', { params: { exam_id: examId.value } }); compareData.value = r.data }
  catch {}
  loading.value = false
}
</script>
