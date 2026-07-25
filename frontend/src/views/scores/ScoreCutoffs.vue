<template>
  <div>
    <div class="page-header"><h3>分数线设置</h3><p>设置各次考试的参考分数线</p></div>

    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px" @change="loadData">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-if="examId" v-loading="loading">
      <template #header>
        <span style="font-weight:600;font-size:15px">{{ examName }} — 分数线设置</span>
      </template>

      <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px">
        参考总人数: <strong>{{ totalStudents }}</strong> 人。手动输入后点击保存即可覆盖自动计算值。
      </el-alert>

      <el-table :data="cutoffs" border stripe size="small" style="max-width:600px">
        <el-table-column prop="name" label="分数线类型" width="180" />
        <el-table-column label="分数" width="160">
          <template #default="{row}">
            <el-input-number v-model="row.score" :min="0" :max="750" :precision="1"
              size="small" style="width:140px" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="来源" width="100">
          <template #default="{row}">
            <el-tag :type="row.manual?'success':'info'" size="small">{{ row.manual ? '手动' : '自动' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top:16px">
        <el-button type="primary" @click="autoCalc" :loading="loading">自动计算</el-button>
        <el-button type="success" @click="saveCutoffs" :loading="saving">保存设置</el-button>
      </div>
    </el-card>
    <el-empty v-else description="请选择考试" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const exams = ref([]); const examId = ref<number | null>(null); const examName = ref('')
const loading = ref(false); const saving = ref(false); const totalStudents = ref(0)
const cutoffs = ref<any[]>([])

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

async function loadData(isAuto = false) {
  if (!examId.value) return
  loading.value = true
  try {
    const ex = exams.value.find((e:any) => e.id === examId.value)
    examName.value = ex?.name || ''
    const r = await api.get(`/exams/${examId.value}/cutoffs`)
    totalStudents.value = r.data?.total || 0
    cutoffs.value = (r.data?.cutoffs || []).map((c: any) => ({
      ...c, score: c.score ?? undefined,
    }))
    if (isAuto) ElMessage.success('已加载自动计算值')
  } catch {} finally { loading.value = false }
}

async function autoCalc() { await loadData(true) }

async function saveCutoffs() {
  saving.value = true
  try {
    const data: Record<string, number> = {}
    cutoffs.value.forEach(c => { if (c.score != null) data[c.type] = c.score })
    await api.post(`/exams/${examId.value}/cutoffs`, { cutoffs: data })
    ElMessage.success('分数线保存成功')
    await loadData()
  } catch (e: any) { ElMessage.error(e.message) }
  saving.value = false
}
</script>
