<template>
  <div>
    <div class="page-header"><h3>分数线设置</h3><p>查看各次考试的特控线、一段线等分数参考</p></div>

    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px" @change="loadData">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-if="examId && cutoffs.length" v-loading="loading">
      <template #header>
        <span style="font-weight:600;font-size:15px">{{ examName }} — 分数线</span>
      </template>

      <el-row :gutter="16" style="margin-bottom:20px">
        <el-col :span="8"><el-statistic title="参考总人数" :value="totalStudents" /></el-col>
        <el-col :span="8" v-for="c in cutoffs" :key="c.name">
          <el-statistic :title="c.name">
            <span style="font-size:28px;font-weight:700;color:var(--edu-blue)">{{ c.score.toFixed(1) }}</span>
          </el-statistic>
          <div style="font-size:12px;color:var(--tx-secondary);margin-top:4px">
            排名第 {{ c.rank }} 名 / {{ c.percentile }}
          </div>
        </el-col>
      </el-row>
    </el-card>
    <el-empty v-else :description="examId ? '加载中...' : '请选择考试'" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'

const exams = ref([]); const examId = ref<number | null>(null); const examName = ref('')
const loading = ref(false); const totalStudents = ref(0); const cutoffs = ref<any[]>([])

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

async function loadData() {
  if (!examId.value) return
  loading.value = true
  try {
    const ex = exams.value.find((e:any) => e.id === examId.value)
    examName.value = ex?.name || ''
    const r = await api.get(`/exams/${examId.value}/cutoffs`)
    totalStudents.value = r.data?.total || 0
    cutoffs.value = r.data?.cutoffs || []
  } catch {} finally { loading.value = false }
}
</script>
