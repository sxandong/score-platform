<template>
  <div>
    <div class="page-header"><h3>分数线设置</h3><p>手动设置各次考试的参考分数线</p></div>

    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px" @change="loadData">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item v-if="examId && !isReadOnly">
        <el-button type="success" @click="downloadTemplate">
          <el-icon><Download /></el-icon> 下载导入模板
        </el-button>
        <el-upload
          :show-file-list="false"
          :before-upload="beforeImport"
          :http-request="doImport"
          accept=".xlsx,.xls"
          style="margin-left:8px"
        >
          <el-button type="warning">
            <el-icon><Upload /></el-icon> 导入Excel
          </el-button>
        </el-upload>
      </el-form-item>
    </el-form>

    <el-card v-if="examId" v-loading="loading">
      <template #header>
        <span style="font-weight:600;font-size:15px">{{ examName }} — 分数线设置</span>
      </template>

      <h4 style="margin:16px 0 8px">考试分数线</h4>
      <el-table :data="examCutoffs" border stripe size="small" style="max-width:520px">
        <el-table-column prop="name" label="类型" width="200" />
        <el-table-column label="分数">
          <template #default="{row}">
            <el-input-number v-model="row.score" :min="0" :max="750" :precision="1"
              size="small" style="width:160px" controls-position="right" placeholder="输入分数" :disabled="isReadOnly" />
          </template>
        </el-table-column>
      </el-table>

      <h4 style="margin:20px 0 8px">各科优秀/良好线</h4>
      <div style="overflow-x:auto">
      <el-table :data="subjCutoffs" border stripe size="small" style="max-width:520px">
        <el-table-column prop="subject" label="科目" width="80"  />
        <el-table-column label="优秀线">
          <template #default="{row}">
            <el-input-number v-model="row.excellent" :min="0" :max="150" :precision="1"
              size="small" style="width:120px" controls-position="right" placeholder="-" :disabled="isReadOnly" />
          </template>
        </el-table-column>
        <el-table-column label="良好线">
          <template #default="{row}">
            <el-input-number v-model="row.good" :min="0" :max="150" :precision="1"
              size="small" style="width:120px" controls-position="right" placeholder="-" :disabled="isReadOnly" />
          </template>
        </el-table-column>
      </el-table>
      </div>

      <el-button v-if="!isReadOnly" type="primary" @click="saveCutoffs" :loading="saving" style="margin-top:20px">保存设置</el-button>
    </el-card>
    <el-empty v-else description="请选择考试" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import axios from 'axios'

const auth = useAuthStore()
const isReadOnly = computed(() => auth.hasRole('teacher') && !auth.hasRole('admin') && !auth.hasRole('director'))
const exams = ref<any[]>([]); const examId = ref<number | null>(null); const examName = ref('')
const loading = ref(false); const saving = ref(false)
const examCutoffs = ref<any[]>([])
const subjCutoffs = ref<any[]>([])

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
    const all = (r.data?.cutoffs || []).map((c: any) => ({ ...c }))
    examCutoffs.value = all.filter((c: any) => !c.type.startsWith('subj_'))
    const SUBJ_NAMES = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']
    subjCutoffs.value = SUBJ_NAMES.map(sn => ({
      subject: sn,
      excellent: all.find((c: any) => c.type === `subj_excellent_${sn}`)?.score ?? undefined,
      good: all.find((c: any) => c.type === `subj_good_${sn}`)?.score ?? undefined,
    }))
  } catch {} finally { loading.value = false }
}

async function saveCutoffs() {
  saving.value = true
  try {
    const data: Record<string, number> = {}
    examCutoffs.value.forEach(c => { if (c.score != null) data[c.type] = c.score })
    subjCutoffs.value.forEach(s => {
      if (s.excellent != null) data[`subj_excellent_${s.subject}`] = s.excellent
      if (s.good != null) data[`subj_good_${s.subject}`] = s.good
    })
    await api.post(`/exams/${examId.value}/cutoffs`, { cutoffs: data })
    ElMessage.success('分数线保存成功')
  } catch (e: any) { ElMessage.error(e.message) }
  saving.value = false
}

async function downloadTemplate() {
  if (!examId.value) { ElMessage.warning('请先选择考试'); return }
  try {
    const token = localStorage.getItem('access_token')
    const resp = await axios.get('/api/exams/cutoffs/template', {
      params: { exam_id: examId.value },
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([resp.data]))
    const a = document.createElement('a')
    a.href = url
    const contentDisposition = resp.headers['content-disposition']
    let fileName = '分数线模板.xlsx'
    if (contentDisposition) {
      // 优先使用 filename*=UTF-8''... 格式（支持中文）
      const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
      if (utf8Match) {
        fileName = decodeURIComponent(utf8Match[1])
      } else {
        const asciiMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
        if (asciiMatch) fileName = asciiMatch[1]
      }
    }
    a.download = fileName
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    ElMessage.error('下载模板失败')
  }
}

function beforeImport(file: File): boolean {
  if (!examId.value) { ElMessage.warning('请先选择考试'); return false }
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
    ElMessage.error('请上传Excel文件(.xlsx或.xls)')
    return false
  }
  return true
}

async function doImport(options: any) {
  if (!examId.value) return
  const formData = new FormData()
  formData.append('exam_id', String(examId.value))
  formData.append('file', options.file)

  try {
    // 检查是否已有分数线
    const r = await api.get(`/exams/${examId.value}/cutoffs`)
    const existing = (r.data?.cutoffs || []).filter((c: any) => c.score != null && c.score !== undefined)
    const hasExisting = existing.length > 0

    if (hasExisting) {
      await ElMessageBox.confirm(
        `该考试已设置 ${existing.length} 项分数线数据，导入将覆盖原有数据，是否继续？`,
        '确认覆盖',
        { confirmButtonText: '确定导入', cancelButtonText: '取消', type: 'warning' }
      )
    }

    const token = localStorage.getItem('access_token')
    const resp = await axios.post('/api/exams/cutoffs/import', formData, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'multipart/form-data' },
    })
    if (resp.data?.code === 200) {
      ElMessage.success(resp.data.message || '导入成功')
      loadData()
    } else {
      ElMessage.error(resp.data?.message || '导入失败')
    }
  } catch (e: any) {
    if (e !== 'cancel' && e?.name !== 'Cancel') {
      ElMessage.error(e?.response?.data?.message || e.message || '导入失败')
    }
  }
}
</script>
