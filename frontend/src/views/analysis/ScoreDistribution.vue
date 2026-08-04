<template>
  <div>
    <div class="page-header"><h3>各学科分数段统计</h3><p>按分数段统计各科目人数分布</p></div>

    <el-form :inline="true">
      <el-form-item label="入学年份"><el-select v-model="filterYear" style="width:120px" @change="onYearChange">
        <el-option v-for="y in yearOptions" :key="y" :label="y+'年'" :value="y" /></el-select></el-form-item>
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px" @change="loadData">
        <el-option v-for="e in filteredExams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-if="examId && examName" v-loading="loading" style="margin-bottom:16px">
      <template #header><span style="font-weight:600;font-size:15px">{{ examName }} — 各学科分数段情况统计</span></template>

      <h4 style="margin:0 0 8px;font-size:14px;color:var(--tx-secondary)">累计人数</h4>
      <div style="overflow-x:auto;margin-bottom:20px">
      <el-table :data="tableData" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="subject" label="科目" width="90" fixed>
          <template #default="{row}">
            <span style="font-weight:700;color:var(--edu-blue)">{{ row.subject }}</span>
          </template>
        </el-table-column>
        <el-table-column v-for="t in thresholds" :key="'n'+t" :label="'≥'+t" width="80">
          <template #default="{row}">
            <span v-if="row['t_'+t] !== 0" :class="countClass(row['t_'+t])">{{ row['t_'+t] }}</span>
          </template>
        </el-table-column>
      </el-table>
      </div>

      <h4 style="margin:0 0 8px;font-size:14px;color:var(--tx-secondary)">比例 (%)</h4>
      <div style="overflow-x:auto">
      <el-table :data="tableData" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="subject" label="科目" width="90" fixed>
          <template #default="{row}">
            <span style="font-weight:700;color:var(--edu-blue)">{{ row.subject }}</span>
          </template>
        </el-table-column>
        <el-table-column v-for="t in thresholds" :key="'p'+t" :label="'≥'+t" width="80">
          <template #default="{row}">
            <span v-if="row['p_'+t] !== 0" :class="pctClass(row['p_'+t])">{{ row['p_'+t]?.toFixed(1) }}</span>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </el-card>
    <el-empty v-else :description="examId ? '加载中...' : '请选择考试'" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

const exams = ref([]); const examId = ref<number | null>(null); const examName = ref('')
const filterYear = ref<number | null>(null)
const yearOptions = Array.from({length:7}, (_,i) => new Date().getFullYear() - 6 + i)
const filteredExams = computed(() => filterYear.value ? exams.value.filter((e:any) => e.enrollment_year == filterYear.value) : [])
function onYearChange() { examId.value = null }
const loading = ref(false); const thresholds = ref<number[]>([])
const tableData = ref<any[]>([])

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

async function loadData() {
  if (!examId.value) return
  loading.value = true
  try {
    // 考试名称
    const ex = exams.value.find((e:any) => e.id === examId.value)
    examName.value = ex?.name || ''

    const r = await api.get('/analysis/score-distribution', { params: { exam_id: examId.value } })
    const data = r.data || []

    const SUBJ_ORDER = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']
    const allThresholds = [...new Set(data.map((d: any) => d.threshold))].sort((a:any,b:any)=>b-a)
    thresholds.value = allThresholds

    tableData.value = SUBJ_ORDER.filter(sn => data.some((d:any) => d.subject === sn)).map(sn => {
      const row: any = { subject: sn }
      // 总人数取最低阈值(≥40)的累计数
      const totalRow = data.find((d: any) => d.threshold === allThresholds[allThresholds.length-1] && d.subject === sn)
      const total = totalRow ? totalRow.count : 1
      allThresholds.forEach(t => {
        const found = data.find((d: any) => d.threshold === t && d.subject === sn)
        const cnt = found ? found.count : 0
        row['t_'+t] = cnt
        row['p_'+t] = total > 0 ? (cnt / total * 100) : 0
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
function pctClass(v: number): string {
  if (!v) return ''
  if (v >= 80) return 'count-high'
  if (v >= 50) return 'count-mid'
  return 'count-low'
}
</script>

<style scoped>
:deep(.el-table) { border-radius:8px; overflow:hidden; }
:deep(.el-table th.el-table__cell) { background: linear-gradient(180deg,#f0f5fa,#e8f0fe); color:var(--edu-blue); font-weight:600; text-align:center; font-size:12px; }
:deep(.el-table td) { text-align:center; color:#000; }
:deep(.el-table .el-table__row:hover > td) { background:#ecf5ff !important; }
:deep(.el-table .el-table__row:nth-child(even) > td) { background:#fafcfd; }
:deep(.el-table .el-table__row:nth-child(odd) > td) { background:#ffffff; }
.count-high { color:#666; }
.count-mid { color:#666; }
.count-low { color:#666; }
</style>
