<template>
  <div>
    <div class="page-header"><h3>班级对比分析</h3><p>多考试各班达线人数对比</p></div>

    <el-form :inline="true">
      <el-form-item label="选择考试"><el-select v-model="selectedExams" multiple placeholder="至少选2次考试" style="width:500px" @change="loadData">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-if="selectedExams.length>=2 && compareData.exams" v-loading="loading">
      <template #header><span style="font-weight:600">班级对比表</span></template>

      <div class="scroll-wrap">
      <!-- 930线 -->
      <h4 style="margin:8px 0">930分数线人数</h4>
      <el-table :data="makeRows('c930')" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="label" label="班级" width="110" />
        <el-table-column v-for="e in compareData.exams" :key="e.id" :label="(e.name||'').substring(0,14)" width="90">
          <template #default="{row}"><span :class="numClass(row[e.id])">{{ row[e.id]||0 }}</span></template>
        </el-table-column>
      </el-table>

      <!-- 特控线 -->
      <h4 style="margin:16px 0 8px">特控线上线人数</h4>
      <el-table :data="makeRows('special')" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="label" label="班级" width="110" />
        <el-table-column v-for="e in compareData.exams" :key="e.id" :label="(e.name||'').substring(0,14)" width="90">
          <template #default="{row}"><span :class="numClass(row[e.id])">{{ row[e.id]||0 }}</span></template>
        </el-table-column>
      </el-table>

      <!-- 一段线 -->
      <h4 style="margin:16px 0 8px">一段线上线人数</h4>
      <el-table :data="makeRows('first')" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="label" label="班级" width="110" />
        <el-table-column v-for="e in compareData.exams" :key="e.id" :label="(e.name||'').substring(0,14)" width="90">
          <template #default="{row}"><span :class="numClass(row[e.id])">{{ row[e.id]||0 }}</span></template>
        </el-table-column>
      </el-table>
      </div>

      <!-- 趋势图 -->
      <h4 style="margin:20px 0 8px">930线人数对比趋势</h4>
      <div id="chart-930" style="width:100%;height:350px"></div>
      <h4 style="margin:20px 0 8px">特控线人数对比趋势</h4>
      <div id="chart-special" style="width:100%;height:350px"></div>
      <h4 style="margin:20px 0 8px">一段线人数对比趋势</h4>
      <div id="chart-first" style="width:100%;height:350px"></div>
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

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

async function loadData() {
  if (selectedExams.value.length < 2) return
  loading.value = true
  try {
    const ids = selectedExams.value.join(',')
    const r = await api.get('/analysis/multi-exam-compare', { params: { exam_ids: ids } })
    compareData.value = r.data || {}
    await nextTick(); await new Promise(r2 => setTimeout(r2, 300))
    drawCharts()
  } catch {} finally { loading.value = false }
}

function makeRows(key: string) {
  const classes = compareData.value.classes || []
  const data = compareData.value.data || {}
  return classes.map((c: any) => {
    const row: any = { label: c.name }
    for (const eid of selectedExams.value) {
      const examData = data[String(eid)]
      if (examData) {
        const cc = examData.class_counts?.find((x: any) => x.class_id === c.id)
        row[eid] = cc ? cc[key] : 0
      }
    }
    return row
  })
}

function drawCharts() {
  const examsList = compareData.value.exams || []
  const labels = examsList.map((e: any) => (e.name||'').substring(0,14))
  const classes = compareData.value.classes || []

  function drawChart(domId: string, key: string) {
    const el = document.getElementById(domId); if (!el) return
    const series = classes.map((c: any) => {
      const vals = examsList.map((e: any) => {
        const cc = compareData.value.data[String(e.id)]?.class_counts?.find((x: any) => x.class_id === c.id)
        return cc ? (cc[key] || 0) : 0
      })
      return { name: c.name, type: 'line', data: vals, smooth: true }
    })
    const inst = echarts.getInstanceByDom(el) || echarts.init(el)
    inst.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0, type: 'scroll' },
      grid: { left: 50, right: 20, top: 40, bottom: 25 },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', name: '人数', minInterval: 1 },
      series,
    }, true)
  }

  drawChart('chart-930', 'c930')
  drawChart('chart-special', 'special')
  drawChart('chart-first', 'first')
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
