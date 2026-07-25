<template>
  <div>
    <div class="page-header"><h3>各学科分数段统计</h3><p>按分数段统计各科目人数分布</p></div>

    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px" @change="loadData">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-if="examId" v-loading="loading">
      <div style="overflow-x:auto">
      <el-table :data="tableData" border stripe size="small">
        <el-table-column prop="threshold" label="分数段" width="90" fixed>
          <template #default="{row}">≥{{ row.threshold }}</template>
        </el-table-column>
        <el-table-column v-for="subj in subjects" :key="subj" :label="subj" width="80">
          <template #default="{row}">{{ row[subj] || 0 }}</template>
        </el-table-column>
      </el-table>
      </div>
    </el-card>
    <el-empty v-else description="请选择考试" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'

const exams = ref([]); const examId = ref<number | null>(null)
const loading = ref(false); const subjects = ref<string[]>([])
const tableData = ref<any[]>([])

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

async function loadData() {
  if (!examId.value) return
  loading.value = true
  try {
    const r = await api.get('/analysis/score-distribution', { params: { exam_id: examId.value } })
    const data = r.data || []

    // 提取科目列表
    const subjSet = new Set<string>()
    data.forEach((d: any) => subjSet.add(d.subject))
    subjects.value = [...subjSet].sort()

    // 按threshold分组
    const thresholds = [...new Set(data.map((d: any) => d.threshold))].sort((a:any,b:any)=>b-a)
    tableData.value = thresholds.map(t => {
      const row: any = { threshold: t }
      data.filter((d: any) => d.threshold === t).forEach((d: any) => { row[d.subject] = d.count })
      return row
    })
  } catch {} finally { loading.value = false }
}
</script>
