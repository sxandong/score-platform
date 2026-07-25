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
      <el-table :data="tableData" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="subject" label="科目" width="90" fixed />
        <el-table-column v-for="t in thresholds" :key="t" :label="'≥'+t" width="72">
          <template #default="{row}">
            <span :class="countClass(row['t_'+t])">{{ row['t_'+t] || 0 }}</span>
          </template>
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
const loading = ref(false); const thresholds = ref<number[]>([])
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

    const SUBJ_ORDER = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']
    const allThresholds = [...new Set(data.map((d: any) => d.threshold))].sort((a:any,b:any)=>b-a)
    thresholds.value = allThresholds

    // 转置: 行=科目, 列=分数段
    tableData.value = SUBJ_ORDER.filter(sn => data.some((d:any) => d.subject === sn)).map(sn => {
      const row: any = { subject: sn }
      allThresholds.forEach(t => {
        const found = data.find((d: any) => d.threshold === t && d.subject === sn)
        row['t_'+t] = found ? found.count : 0
      })
      return row
    })
  } catch {} finally { loading.value = false }
}

function countClass(v: number): string {
  if (!v) return ''
  if (v >= 100) return 'count-high'
  if (v >= 50) return 'count-mid'
  return 'count-low'
}
</script>

<style scoped>
:deep(.el-table th.el-table__cell) { background: linear-gradient(180deg,#f0f5fa,#e8f0fe); color:var(--edu-blue); font-weight:600; text-align:center; }
.count-high { color:var(--edu-green); font-weight:700; }
.count-mid { color:var(--edu-gold); font-weight:600; }
.count-low { color:var(--tx-secondary); }
</style>

