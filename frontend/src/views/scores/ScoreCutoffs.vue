<template>
  <div>
    <div class="page-header"><h3>分数线设置</h3><p>手动设置各次考试的参考分数线</p></div>

    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px" @change="loadData">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>

    <el-card v-if="examId" v-loading="loading">
      <template #header>
        <span style="font-weight:600;font-size:15px">{{ examName }} — 分数线设置</span>
      </template>

      <el-table :data="cutoffs" border stripe size="small" style="max-width:520px">
        <el-table-column prop="name" label="分数线类型" width="180" />
        <el-table-column label="分数">
          <template #default="{row}">
            <el-input-number v-model="row.score" :min="0" :max="750" :precision="1"
              size="small" style="width:160px" controls-position="right" placeholder="输入分数" />
          </template>
        </el-table-column>
      </el-table>

      <el-button type="primary" @click="saveCutoffs" :loading="saving" style="margin-top:16px">保存设置</el-button>
    </el-card>
    <el-empty v-else description="请选择考试" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const exams = ref([]); const examId = ref<number | null>(null); const examName = ref('')
const loading = ref(false); const saving = ref(false)
const cutoffs = ref<any[]>([])

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
    cutoffs.value = (r.data?.cutoffs || []).map((c: any) => ({ ...c }))
  } catch {} finally { loading.value = false }
}

async function saveCutoffs() {
  saving.value = true
  try {
    const data: Record<string, number> = {}
    cutoffs.value.forEach(c => { if (c.score != null) data[c.type] = c.score })
    await api.post(`/exams/${examId.value}/cutoffs`, { cutoffs: data })
    ElMessage.success('分数线保存成功')
  } catch (e: any) { ElMessage.error(e.message) }
  saving.value = false
}
</script>
