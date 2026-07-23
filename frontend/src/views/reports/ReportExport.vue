<template>
  <div>
    <h3>报表导出</h3>
    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:250px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item label="班级"><el-select v-model="classId" placeholder="选择班级" style="width:200px">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select>
      </el-form-item>
      <el-form-item><el-button type="primary" @click="exportSheet">导出Excel</el-button></el-form-item>
    </el-form>
    <el-empty description="选择考试和班级后导出成绩单" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const exams = ref([]); const classes = ref([])
const examId = ref<number | null>(null); const classId = ref<number | null>(null)

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

async function exportSheet() {
  if (!examId.value || !classId.value) { ElMessage.warning('请选择考试和班级'); return }
  const token = localStorage.getItem('access_token')
  const url = `/api/reports/score-sheet?exam_id=${examId.value}&class_id=${classId.value}`
  const a = document.createElement('a'); a.href = url
  a.download = `成绩单_${examId.value}_${classId.value}.xlsx`
  a.click(); ElMessage.success('开始下载')
}
</script>
