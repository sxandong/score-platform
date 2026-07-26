<template>
  <div>
    <div class="page-header"><h3>成绩趋势</h3><p>历次考试各分数线上线人数变化趋势</p></div>

    <el-card v-loading="loading">
      <div id="chart-cutoff-trend" style="width:100%;height:450px"></div>
    </el-card>
    <el-empty v-if="!loading && !chartReady" description="暂无数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'

const loading = ref(false); const chartReady = ref(false)

onMounted(async () => { await loadData() })

async function loadData() {
  loading.value = true
  try {
    const r = await api.get('/analysis/cutoff-trend')
    const data = r.data || []
    if (!data.length) return

    await nextTick(); await new Promise(r2 => setTimeout(r2, 200))
    const el = document.getElementById('chart-cutoff-trend')
    if (!el) return

    const labels = data.map((d: any) => (d.exam_name||'').substring(0,14))
    const inst = echarts.init(el)
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
    })
    chartReady.value = true
  } catch {} finally { loading.value = false }
}
</script>
