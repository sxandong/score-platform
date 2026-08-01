<template>
  <div>
    <div class="page-header"><h3>成绩趋势</h3><p>历次考试各分数线上线人数变化趋势</p></div>

    <el-form :inline="true">
      <el-form-item label="入学年份"><el-select v-model="filterYear" style="width:120px" @change="loadData">
        <el-option v-for="y in yearOptions" :key="y" :label="y+'年'" :value="y" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-show="filterYear && !noData" v-loading="loading">
      <div id="chart-cutoff-trend" style="width:100%;height:450px"></div>
    </el-card>
    <el-empty v-if="!filterYear" description="请先选择入学年份" />
    <el-empty v-if="filterYear && noData" description="该入学年份暂无考试数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'

const filterYear = ref<number | null>(null)
const yearOptions = Array.from({length:7}, (_,i) => new Date().getFullYear() - 6 + i)
const loading = ref(false); const noData = ref(false)

async function loadData() {
  if (!filterYear.value) return
  loading.value = true; noData.value = false
  try {
    const r = await api.get('/analysis/cutoff-trend', { params: { enrollment_year: filterYear.value } })
    const data = r.data || []
    if (!data.length) { noData.value = true; return }

    await nextTick()
    const el = document.getElementById('chart-cutoff-trend')
    if (!el) return

    const labels = data.map((d: any) => (d.exam_name||'').substring(0,14))
    const specialMax = Math.max(...data.map((d: any) => d.special||0))
    const inst = echarts.getInstanceByDom(el) || echarts.init(el)
    inst.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 65, right: 65, top: 40, bottom: 25 },
      xAxis: { type: 'category', data: labels },
      yAxis: [
        { type: 'value', name: '930线/一段线', minInterval: 1, position: 'left',
          axisLine: { show: true, lineStyle: { color: '#5470c6' } },
          axisLabel: { color: '#5470c6' } },
        { type: 'value', name: '特控线', minInterval: 1, position: 'right',
          max: specialMax + 20,
          axisLine: { show: true, lineStyle: { color: '#ee6666' } },
          axisLabel: { color: '#ee6666' },
          splitLine: { show: false } },
      ],
      series: [
        { name: '930线人数', type: 'line', yAxisIndex: 0, data: data.map((d: any) => d.c930||0), smooth: true,
          symbol: 'circle', symbolSize: 7, lineStyle: { width: 2.5 },
          itemStyle: { color: '#5470c6' },
          label: { show: true, position: 'top', fontSize: 11, color: '#5470c6' } },
        { name: '特控线人数', type: 'line', yAxisIndex: 1, data: data.map((d: any) => d.special||0), smooth: true,
          symbol: 'diamond', symbolSize: 8, lineStyle: { width: 2.5, type: 'dashed' },
          itemStyle: { color: '#ee6666' },
          label: { show: true, position: 'top', fontSize: 11, color: '#ee6666' } },
        { name: '一段线人数', type: 'line', yAxisIndex: 0, data: data.map((d: any) => d.first||0), smooth: true,
          symbol: 'triangle', symbolSize: 7, lineStyle: { width: 2.5 },
          itemStyle: { color: '#91cc75' },
          label: { show: true, position: 'top', fontSize: 11, color: '#91cc75' } },
      ],
    }, true)
  } catch {} finally { loading.value = false }
}
</script>
