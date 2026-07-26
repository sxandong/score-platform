<template>
  <div>
    <div class="page-header"><h3>班级人数统计</h3><p>各班级达线人数分布</p></div>

    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px" @change="loadData">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-if="examId && compareData.length" v-loading="loading">
      <div style="overflow-x:auto">
      <el-table :data="transposed" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="label" label="指标" width="140" fixed />
        <el-table-column v-for="c in compareData" :key="c.id" :label="c.name" width="90">
          <template #default="{row}">
            <span :class="numClass(row[c.id], row.label)">{{ row[c.id] !== undefined ? row[c.id] : '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
      </div>

      <!-- 各科优秀/良好线上线人数 -->
      <h4 style="margin:20px 0 8px">各学科优秀/良好线上线人数</h4>
      <div style="overflow-x:auto">
      <el-table :data="subjRows" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="label" label="科目" width="100" fixed />
        <el-table-column v-for="c in compareData" :key="c.id" :label="c.name" width="100">
          <template #default="{row}">
            {{ row[c.id]?.count }}
            <span style="font-size:11px;color:var(--tx-secondary)">({{ row[c.id]?.pct }}%)</span>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </el-card>
    <el-empty v-else description="请选择考试" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

const exams = ref([]); const examId = ref<number | null>(null)
const compareData = ref([]); const cutoffs = ref<Record<string,number>>({})
const subjStats = ref<Record<string, any[]>>({})
const loading = ref(false)

const transposed = computed(() => {
  const cls = compareData.value
  if (!cls.length) return []
  const rows = []
  const addRow = (label: string, key: string) => {
    const row: any = { label }
    cls.forEach((c: any) => { row[c.id] = c[key] !== undefined ? c[key] : '-' })
    rows.push(row)
  }
  if (cutoffs.value.score_930) addRow(`930线(≥${cutoffs.value.score_930})`, 'count_930')
  if (cutoffs.value.special) addRow(`特控线(≥${cutoffs.value.special})`, 'count_special')
  addRow('前20名', 'top20')
  addRow('前30名', 'top30')
  addRow('前50名', 'top50')
  addRow('前80名', 'top80')
  addRow('前100名', 'top100')
  if (cutoffs.value.first) addRow(`一段线(≥${cutoffs.value.first})`, 'count_first')
  return rows
})

const subjRows = computed(() => {
  const rows: any[] = []
  for (const [key, items] of Object.entries(subjStats.value)) {
    const row: any = { label: key }
    compareData.value.forEach((c: any) => {
      const found = (items as any[]).find((x: any) => x.class_id === c.id)
      const cnt = found ? found.count : 0
      const total = c.top100 ? c.top100 + 1 : 1
      row[c.id] = { count: cnt, pct: total > 0 ? (cnt / Math.max(1, total) * 100).toFixed(1) : '0.0' }
    })
    rows.push(row)
  }
  return rows
})

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

async function loadData() {
  if (!examId.value) return; loading.value = true
  try {
    const r = await api.get('/analysis/class-cutoff-stats', { params: { exam_id: examId.value } })
    compareData.value = r.data?.classes || []
    cutoffs.value = r.data?.cutoffs || {}
    subjStats.value = r.data?.subj_stats || {}
  } catch {} finally { loading.value = false }
}

function numClass(v: number, label: string): string {
  if (!v) return ''
  const isKey = /930|特控/.test(label)
  if (isKey && v > 0) return 'count-red'
  if (v >= 15) return 'count-high'
  if (v >= 5) return 'count-mid'
  return 'count-low'
}
</script>

<style scoped>
:deep(.el-table th.el-table__cell) { background: linear-gradient(180deg,#f0f5fa,#e8f0fe); color:var(--edu-blue); font-weight:600; text-align:center; }
.count-high { color:var(--edu-green); font-weight:700; }
.count-mid { color:var(--edu-gold); font-weight:600; }
.count-low { color:var(--tx-secondary); }
.count-red { color:#e04040; font-weight:700; }
</style>
