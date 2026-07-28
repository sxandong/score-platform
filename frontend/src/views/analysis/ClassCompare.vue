<template>
  <div>
    <div class="page-header"><h3>班级人数统计</h3><p>各班级达线人数分布</p></div>

    <el-form :inline="true">
      <el-form-item label="入学年份"><el-select v-model="filterYear" style="width:120px" @change="onYearChange">
        <el-option v-for="y in yearOptions" :key="y" :label="y+'年'" :value="y" /></el-select></el-form-item>
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px" @change="loadData">
        <el-option v-for="e in filteredExams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-if="examId && compareData.length" v-loading="loading">
      <div class="scroll-wrap">
      <el-table :data="transposed" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="label" label="指标" width="140" />
        <el-table-column v-for="c in compareData" :key="c.id" :label="c.name" width="90">
          <template #default="{row}">
            <span :class="numClass(row[c.id], row.label)">{{ row[c.id] !== undefined ? row[c.id] : '-' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <h4 style="margin:20px 0 8px">各学科优秀线上线人数
        <span class="cutoff-hint">
          语文≥{{ subjCutoffs.语文?.excellent||'-' }} 数学≥{{ subjCutoffs.数学?.excellent||'-' }}
          外语≥{{ subjCutoffs.外语?.excellent||'-' }} 物理≥{{ subjCutoffs.物理?.excellent||'-' }}
          化学≥{{ subjCutoffs.化学?.excellent||'-' }} 生物≥{{ subjCutoffs.生物?.excellent||'-' }}
          政治≥{{ subjCutoffs.政治?.excellent||'-' }} 历史≥{{ subjCutoffs.历史?.excellent||'-' }}
          地理≥{{ subjCutoffs.地理?.excellent||'-' }} 技术≥{{ subjCutoffs.技术?.excellent||'-' }}
        </span>
      </h4>
      <el-table :data="excellentRows" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="label" label="科目" width="80" />
        <el-table-column prop="total" label="总人数" width="75" />
        <el-table-column v-for="c in compareData" :key="c.id" :label="c.name" width="100">
          <template #default="{row}">
            <span :class="numClass(row[c.id]?.count||0,'')">{{ row[c.id]?.count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total" label="总人数" width="75" />
        <el-table-column prop="label" label="科目" width="80" />
      </el-table>

      <h4 style="margin:16px 0 8px">各学科良好线上线人数
        <span class="cutoff-hint">
          语文≥{{ subjCutoffs.语文?.good||'-' }} 数学≥{{ subjCutoffs.数学?.good||'-' }}
          外语≥{{ subjCutoffs.外语?.good||'-' }} 物理≥{{ subjCutoffs.物理?.good||'-' }}
          化学≥{{ subjCutoffs.化学?.good||'-' }} 生物≥{{ subjCutoffs.生物?.good||'-' }}
          政治≥{{ subjCutoffs.政治?.good||'-' }} 历史≥{{ subjCutoffs.历史?.good||'-' }}
          地理≥{{ subjCutoffs.地理?.good||'-' }} 技术≥{{ subjCutoffs.技术?.good||'-' }}
        </span>
      </h4>
      <el-table :data="goodRows" border stripe size="small" :cell-style="{textAlign:'center'}">
        <el-table-column prop="label" label="科目" width="80" />
        <el-table-column prop="total" label="总人数" width="75" />
        <el-table-column v-for="c in compareData" :key="c.id" :label="c.name" width="100">
          <template #default="{row}">
            <span :class="numClass(row[c.id]?.count||0,'')">{{ row[c.id]?.count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total" label="总人数" width="75" />
        <el-table-column prop="label" label="科目" width="80" />
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
const filterYear = ref<number | null>(null)
const yearOptions = [2023,2024,2025,2026,2027,2028,2029,2030]
const filteredExams = computed(() => filterYear.value ? exams.value.filter((e:any) => e.enrollment_year == filterYear.value) : [])
function onYearChange() { examId.value = null; compareData.value = []; cutoffs.value = {} }
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

const SUBJ_NAMES = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']

const subjCutoffs = computed(() => {
  const map: Record<string, any> = {}
  SUBJ_NAMES.forEach(sn => {
    map[sn] = {
      excellent: cutoffs.value[`subj_excellent_${sn}`] ?? '-',
      good: cutoffs.value[`subj_good_${sn}`] ?? '-',
    }
  })
  return map
})

function _makeSubjRows(type: string) {
  return SUBJ_NAMES.map(sn => {
    const key = `${sn}${type}`
    const items = subjStats.value[key] || []
    const row: any = { label: sn, total: 0 }
    compareData.value.forEach((c: any) => {
      const found = items.find((x: any) => x.class_id === c.id)
      const cnt = found ? found.count : 0
      row.total += cnt
      row[c.id] = { count: cnt, pct: '0' }
    })
    return row
  })
}

const excellentRows = computed(() => _makeSubjRows('优秀'))
const goodRows = computed(() => _makeSubjRows('良好'))

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
.scroll-wrap { overflow-x:auto; width:100%; }
.cutoff-hint { font-size:12px; color:var(--tx-secondary); margin-left:8px; white-space:nowrap; }
:deep(.el-table th.el-table__cell) { background: linear-gradient(180deg,#f0f5fa,#e8f0fe); color:var(--edu-blue); font-weight:600; text-align:center; }
.count-high { color:var(--edu-green); font-weight:700; }
.count-mid { color:var(--edu-gold); font-weight:600; }
.count-low { color:var(--tx-secondary); }
.count-red { color:#e04040; font-weight:700; }
</style>
