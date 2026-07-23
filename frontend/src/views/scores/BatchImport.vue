<template>
  <div>
    <h3>批量导入成绩</h3>
    <el-form :inline="true" style="margin-bottom:16px">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>
    <el-alert v-if="examId && existingCount > 0" type="warning" :closable="false" show-icon style="margin-bottom:12px"
      :title="`该考试已有 ${existingCount} 条成绩，重新导入将更新原有数据。`" />

    <el-upload drag :show-file-list="false" :http-request="doImport" accept=".xlsx,.xls" :disabled="!examId">
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div>点击或拖拽上传Excel文件</div>
      <template #tip><div style="font-size:12px;color:#909399;margin-top:8px">
        列名: 学籍号, 姓名, 班级, 语文, 数学, 外语, 政治, 历史, 地理, 物理, 化学, 生物, 技术
      </div></template>
    </el-upload>

    <el-result v-if="importResult" :icon="importResult.errors?.length ? 'warning' : 'success'"
      :title="importResult.message" style="margin-top:16px">
      <template #sub-title>
        共 {{ importResult.total_rows }} 行，新增 {{ importResult.created_students }} 学生，{{ importResult.created_scores }} 条成绩
        <div v-if="importResult.errors?.length" style="margin-top:8px;text-align:left">
          <el-tag v-for="(e,i) in importResult.errors" :key="i" type="danger" size="small" style="margin:2px">
            行{{ e.row }}: {{ e.reason }}
          </el-tag>
        </div>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const exams = ref([]); const examId = ref<number | null>(null)
const existingCount = ref(0); const importResult = ref<any>(null)

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
})

watch(examId, async (val) => {
  importResult.value = null
  if (!val) { existingCount.value = 0; return }
  try {
    const r = await api.get(`/exams/${val}/stats`)
    existingCount.value = r.data.scores || 0
  } catch { existingCount.value = 0 }
})

async function doImport(options: any) {
  if (!examId.value) { ElMessage.warning('请先选择考试'); return }

  // 已有成绩时确认
  if (existingCount.value > 0) {
    try {
      await ElMessageBox.confirm(
        `该考试已有 ${existingCount.value} 条成绩，重新导入将覆盖更新原有数据。确定导入？`,
        '确认导入', { type: 'warning', confirmButtonText: '确定导入', cancelButtonText: '取消' }
      )
    } catch { return }
  }

  const fd = new FormData(); fd.append('file', options.file); fd.append('exam_id', String(examId.value))
  try {
    const r = await api.post('/scores/batch', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    importResult.value = r.data
    ElMessage.success(r.message)
    // 刷新计数
    existingCount.value = r.data.created_scores
  } catch (e: any) { ElMessage.error(e.message) }
}
</script>
