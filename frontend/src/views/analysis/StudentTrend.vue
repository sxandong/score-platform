<template>
  <div>
    <div class="page-header"><h3>成绩趋势</h3><p>历次考试各分数线上线人数变化趋势</p></div>

    <el-form :inline="true">
      <el-form-item label="入学年份"><el-select v-model="filterYear" style="width:120px" @change="loadData">
        <el-option v-for="y in yearOptions" :key="y" :label="y+'年'" :value="y" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-if="filterYear && chartReady" v-loading="loading">
      <div id="chart-cutoff-trend" style="width:100%;height:450px"></div>
    </el-card>
    <el-empty v-else :description="filterYear ? '加载中...' : '请先选择入学年份'" />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'

const filterYear = ref<number | null>(null)
const yearOptions = [2023,2024,2025,2026,2027,2028,2029,2030]
const loading = ref(false); const chartReady = ref(false)

async function loadData() {
  if (!filterYear.value) return
  loading.value = true; chartReady.value = false
  try {
    const r = await api.get('/analysis/cutoff-trend', { params: { enrollment_year: filterYear.value } })
    const data = r.data || []
    if (!data.length) return

    await nextTick(); await new Promise(r2 => setTimeout(r2, 200))
    const el = document.getElementById('chart-cutoff-trend')
    if (!el) return

    const labels = data.map((d: any) => (d.exam_name||'').substring(0,14))
    const inst = echarts.getInstanceByDom(el) || echarts.init(el)
    inst.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 55, right: 20, top: 40, bottom: 25 },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', name: '人数', minInterval: 1 },
      series: [
        { name: '930线人数', type: 'line', data: data.map((d: any) => d.c930||0), smooth: true,
          label: { show: true, position: 'top', fontSize: 11 } },
        { name: '特控线人数', type: 'line', data: data.map((d: any) => d.special||0), smooth: true,
          label: { show: true, position: 'top', fontSize: 11 } },
        { name: '一段线人数', type: 'line', data: data.map((d: any) => d.first||0), smooth: true,
          label: { show: true, position: 'top', fontSize: 11 } },
      ],
    }, true)
    chartReady.value = true
  } catch {} finally { loading.value = false }
}
</script>
