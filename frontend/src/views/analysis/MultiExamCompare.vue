<template>
  <div>
    <div class="page-header"><h3>班级达线人数对比分析</h3><p>多考试各班达线人数对比</p></div>

    <el-form :inline="true">
      <el-form-item label="入学年份"><el-select v-model="filterYear" style="width:120px" @change="onYearChange">
        <el-option v-for="y in yearOptions" :key="y" :label="y+'年'" :value="y" /></el-select></el-form-item>
      <el-form-item label="选择考试"><el-select v-model="selectedExams" multiple placeholder="至少选2次考试" style="width:500px">
        <el-option v-for="e in filteredExams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item><el-button type="primary" @click="loadData" :disabled="selectedExams.length<2">对比分析</el-button></el-form-item>
    </el-form>

    <el-card v-if="selectedExams.length>=2 && compareData.exams" v-loading="loading">
      <template #header><span style="font-weight:600">班级达线人数对比</span></template>

      <div class="scroll-wrap">
      <el-table :data="flatRows" border stripe size="small" :cell-style="{textAlign:'center'}" :span-method="spanMethod">
        <el-table-column prop="examName" label="考试" width="180" fixed />
        <el-table-column prop="typeName" label="指标" width="90" fixed />
        <el-table-column prop="totalCount" label="总人数" width="75" fixed />
        <el-table-column v-for="c in compareData.classes" :key="c.id" :label="c.name" width="85">
          <template #default="{row}"><span v-if="row[c.id] !== 0" :class="numClass(row[c.id], row.typeName)">{{ row[c.id] }}</span></template>
        </el-table-column>
      </el-table>
      </div>

      <el-form :inline="true" style="margin:16px 0">
        <el-form-item label="图表指标"><el-select v-model="chartMetric" @change="drawChart" style="width:180px">
          <el-option label="930分数线人数" value="c930" />
          <el-option label="特控线上线人数" value="special" />
          <el-option label="一段线上线人数" value="first" />
        </el-select></el-form-item>
      </el-form>
      <div id="chart-main" style="width:100%;height:400px"></div>
    </el-card>
    <el-empty v-else description="请至少选择2次考试" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'

const exams = ref([]); const selectedExams = ref<number[]>([])
const filterYear = ref<number | null>(null)
const yearOptions = Array.from({length:7}, (_,i) => new Date().getFullYear() - 6 + i)
const filteredExams = computed(() => filterYear.value ? exams.value.filter((e:any) => e.enrollment_year == filterYear.value) : [])
function onYearChange() { selectedExams.value = []; compareData.value = {} }
const compareData = ref<any>({}); const loading = ref(false)
const chartMetric = ref('c930')

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

const TYPE_NAMES: Record<string,string> = { c930: '930线', special: '特控线', first: '一段线' }

const flatRows = computed(() => {
  const classes = compareData.value.classes || []
  const examsList = compareData.value.exams || []
  const data = compareData.value.data || {}
  const rows: any[] = []
  for (const e of examsList) {
    for (const [key, tname] of Object.entries(TYPE_NAMES)) {
      const row: any = { examName: (e.name||'').substring(0,18), typeName: tname, totalCount: 0 }
      for (const c of classes) {
        const cc = data[String(e.id)]?.class_counts?.find((x: any) => x.class_id === c.id)
        const cnt = cc ? (cc[key] || 0) : 0
        row[c.id] = cnt
        row.totalCount += cnt
      }
      rows.push(row)
    }
  }
  return rows
})

const spanMethod = ({ row, column, rowIndex, columnIndex }: any) => {
  if (columnIndex === 0) {
    if (rowIndex % 3 === 0) return { rowspan: 3, colspan: 1 }
    else return { rowspan: 0, colspan: 0 }
  }
}

async function loadData() {
  if (selectedExams.value.length < 2) return
  loading.value = true; compareData.value = {}
  try {
    const ids = selectedExams.value.join(',')
    const r = await api.get('/analysis/multi-exam-compare', { params: { exam_ids: ids } })
    compareData.value = r.data || {}
    await nextTick(); await new Promise(r2 => setTimeout(r2, 300))
    drawChart()
  } catch {} finally { loading.value = false }
}

function drawChart() {
  const el = document.getElementById('chart-main'); if (!el) return
  const examsList = compareData.value.exams || []
  const classes = compareData.value.classes || []
  const data = compareData.value.data || {}
  const key = chartMetric.value

  const series = examsList.map((e: any) => ({
    name: (e.name||'').substring(0,12),
    type: 'bar',
    data: classes.map((c: any) => {
      const cc = data[String(e.id)]?.class_counts?.find((x: any) => x.class_id === c.id)
      return cc ? (cc[key] || 0) : 0
    }),
  }))

  const inst = echarts.getInstanceByDom(el) || echarts.init(el)
  inst.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, type: 'scroll' },
    grid: { left: 50, right: 20, top: 40, bottom: 25 },
    xAxis: { type: 'category', data: classes.map((c: any) => c.name), axisLabel: { rotate: 45 } },
    yAxis: { type: 'value', name: '人数', minInterval: 1 },
    series,
  }, true)
}

function numClass(v: number, typeName?: string): string {
  if (!v) return ''
  if (typeName === '930线') return 'count-red'
  if (typeName === '特控线') return 'count-orange'
  if (typeName === '一段线') return 'count-green'
  if (v >= 15) return 'count-high'
  if (v >= 5) return 'count-mid'
  return 'count-yellow'
}
</script>

<style scoped>
.scroll-wrap { overflow-x:auto;width:100%; }
:deep(.el-table th.el-table__cell) { background: linear-gradient(180deg,#f0f5fa,#e8f0fe); color:var(--edu-blue); font-weight:600; text-align:center; }
.count-high { color:var(--edu-green); font-weight:700; }
.count-mid { color:var(--edu-gold); font-weight:600; }
.count-low { color:var(--tx-secondary); }
.count-red { color:#e04040; font-weight:700; }
.count-orange { color:#e6a23c; font-weight:700; }
.count-yellow { color:#f99c02; font-weight:700; }
.count-green { color:#0aa344; font-weight:700; }
.count-teal { color:#3de1ad; font-weight:700; }
.count-blue { color:#4B5CC4; font-weight:700; }
.count-gray { color:#999999; }

.subject-name {
  font-weight: 700;
  color: var(--edu-blue);
  font-size: 12px;
}
</style>
