<template>
  <div>
    <h3>批量导入成绩</h3>
    <el-form :inline="true" style="margin-bottom:16px">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>
    <el-upload drag :auto-upload="false" :on-change="handleFile" accept=".xlsx,.xls" :limit="1">
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div>拖拽或点击上传Excel文件</div>
    </el-upload>
    <el-table v-if="preview.length" :data="preview" border stripe style="margin-top:16px" max-height="400">
      <el-table-column prop="row" label="行号" width="80" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.status==='ok'?'success':'danger'">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="student_no" label="学号" width="120" />
      <el-table-column prop="reason" label="备注" />
    </el-table>
    <el-button v-if="preview.length" type="primary" @click="confirmImport" :loading="importing" style="margin-top:16px">确认导入</el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const exams = ref([]); const examId = ref<number | null>(null)
const preview = ref<any[]>([]); const importing = ref(false)
let fileData: File | null = null

onMounted(async () => { try { const r = await api.get('/exams'); exams.value = r.data } catch {} })

async function handleFile(file: any) {
  fileData = file.raw
  if (!examId.value) { ElMessage.warning('请先选择考试'); return }
  const form = new FormData(); form.append('file', file.raw); form.append('exam_id', String(examId.value))
  try { const r = await api.post('/scores/batch', form, { headers: { 'Content-Type': 'multipart/form-data' } }); preview.value = r.data.preview }
  catch (e: any) { ElMessage.error(e.message) }
}

async function confirmImport() {
  importing.value = true
  try { ElMessage.success('导入完成'); preview.value = [] }
  catch (e: any) { ElMessage.error(e.message) }
  importing.value = false
}
</script>
