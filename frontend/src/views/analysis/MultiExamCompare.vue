<template>
  <div>
    <div class="page-header"><h3>班级对比分析</h3><p>多考试各班达线人数对比</p></div>

    <el-form :inline="true">
      <el-form-item label="选择考试"><el-select v-model="selectedExams" multiple placeholder="至少选2次考试" style="width:500px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item><el-button type="primary" @click="loadData" :disabled="selectedExams.length<2">对比分析</el-button></el-form-item>
    </el-form>

    <el-card v-if="selectedExams.length>=2 && compareData.exams" v-loading="loading">
      <template #header><span style="font-weight:600">班级达线人数对比</span></template>

      <div class="scroll-wrap">
      <el-table :data="mergedRows" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="className" label="班级" width="110" fixed />
        <el-table-column prop="typeName" label="指标" width="90" fixed />
        <el-table-column v-for="e in compareData.exams" :key="e.id" :label="(e.name||'').substring(0,14)" width="85">
          <template #default="{row}"><span :class="numClass(row[e.id])">{{ row[e.id]||0 }}</span></template>
        </el-table-column>
      </el-table>
      </div>

      <el-form :inline="true" style="margin:16px 0">
        <el-form-item label="图表指标"><el-select v-model="chartMetric" @change="drawChart">
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
const compareData = ref<any>({}); const loading = ref(false)
const chartMetric = ref('c930')

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

const TYPE_NAMES: Record<string,string> = { c930: '930线', special: '特控线', first: '一段线' }

const mergedRows = computed(() => {
  const classes = compareData.value.classes || []
  const data = compareData.value.data || {}
  const rows: any[] = []
  for (const c of classes) {
    for (const [key, name] of Object.entries(TYPE_NAMES)) {
      const row: any = { className: c.name, typeName: name }
      for (const eid of selectedExams.value) {
        const examData = data[String(eid)]
        if (examData) {
          const cc = examData.class_counts?.find((x: any) => x.class_id === c.id)
          row[eid] = cc ? (cc[key] || 0) : 0
        }
      }
      rows.push(row)
    }
  }
  return rows
})

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

function numClass(v: number): string {
  if (!v) return ''
  if (v >= 15) return 'count-high'
  if (v >= 5) return 'count-mid'
  return 'count-low'
}
</script>

<style scoped>
.scroll-wrap { overflow-x:auto;width:100%; }
:deep(.el-table th.el-table__cell) { background: linear-gradient(180deg,#f0f5fa,#e8f0fe); color:var(--edu-blue); font-weight:600; text-align:center; }
.count-high { color:var(--edu-green); font-weight:700; }
.count-mid { color:var(--edu-gold); font-weight:600; }
.count-low { color:var(--tx-secondary); }
</style>
