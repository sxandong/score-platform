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
      <el-table :data="compareData" border stripe size="small">
        <el-table-column prop="name" label="班级" width="120" fixed />
        <el-table-column v-if="cutoffs.score_930" :label="'≥'+cutoffs.score_930" width="80">
          <template #default="{row}"><span :class="numClass(row.count_930)">{{ row.count_930 || 0 }}</span></template>
        </el-table-column>
        <el-table-column v-if="cutoffs.special" :label="'特控≥'+cutoffs.special" width="100">
          <template #default="{row}"><span :class="numClass(row.count_special)">{{ row.count_special || 0 }}</span></template>
        </el-table-column>
        <el-table-column label="前20" width="65">
          <template #default="{row}"><span :class="numClass(row.top20)">{{ row.top20 || 0 }}</span></template>
        </el-table-column>
        <el-table-column label="前30" width="65">
          <template #default="{row}"><span :class="numClass(row.top30)">{{ row.top30 || 0 }}</span></template>
        </el-table-column>
        <el-table-column label="前50" width="65">
          <template #default="{row}"><span :class="numClass(row.top50)">{{ row.top50 || 0 }}</span></template>
        </el-table-column>
        <el-table-column label="前80" width="65">
          <template #default="{row}"><span :class="numClass(row.top80)">{{ row.top80 || 0 }}</span></template>
        </el-table-column>
        <el-table-column label="前100" width="70">
          <template #default="{row}"><span :class="numClass(row.top100)">{{ row.top100 || 0 }}</span></template>
        </el-table-column>
        <el-table-column v-if="cutoffs.first" :label="'一段≥'+cutoffs.first" width="100">
          <template #default="{row}"><span :class="numClass(row.count_first)">{{ row.count_first || 0 }}</span></template>
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
const compareData = ref([]); const cutoffs = ref<Record<string,number>>({})
const loading = ref(false)

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

async function loadData() {
  if (!examId.value) return; loading.value = true
  try {
    const r = await api.get('/analysis/class-cutoff-stats', { params: { exam_id: examId.value } })
    compareData.value = r.data?.classes || []
    cutoffs.value = r.data?.cutoffs || {}
  } catch {} finally { loading.value = false }
}

function numClass(v: number): string {
  if (!v) return ''
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
</style>
