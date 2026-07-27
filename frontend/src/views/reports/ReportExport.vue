<template>
  <div>
    <div class="page-header"><h3>报表导出</h3><p>导出班级或单个学生成绩报告</p></div>

    <el-card style="margin-bottom:16px">
      <template #header><span style="font-weight:600">导出全班学生成绩报告 (PDF)</span></template>
      <el-form :inline="true">
        <el-form-item label="班级"><el-select v-model="classId" placeholder="选择班级" style="width:250px">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="exportClassReport">导出全班报告</el-button></el-form-item>
      </el-form>
      <div style="font-size:12px;color:var(--tx-secondary);margin-top:4px">
        生成每个学生一页的HTML报告，请用浏览器 Ctrl+P 打印为PDF，并在更多设置中缩放为55%以适应A4纸张。<br />
      </div>
    </el-card>

    <el-card>
      <template #header><span style="font-weight:600">导出学生成绩报告 (PDF)</span></template>
      <el-form :inline="true">
        <el-form-item label="学籍号/姓名"><el-input v-model="keyword" placeholder="搜索学生" style="width:250px" clearable /></el-form-item>
        <el-form-item><el-button type="primary" @click="searchStudent">搜索</el-button></el-form-item>
      </el-form>
      <div v-if="studentResults.length" style="margin-bottom:12px">
        <el-radio-group v-model="selectedId">
          <el-radio v-for="s in studentResults" :key="s.id" :value="s.id" border style="margin:4px 8px 4px 0">
            {{ s.name }} ({{ s.student_no }}) - {{ s.class_name }}
          </el-radio>
        </el-radio-group>
      </div>
      <el-button type="success" :disabled="!selectedId" @click="exportPDF">导出单个学生报告</el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const exams = ref([]); const classes = ref([])
const classId = ref<number | null>(null)
const keyword = ref(''); const studentResults = ref<any[]>([])
const selectedId = ref<number | null>(null)

onMounted(async () => {
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

function exportClassReport() {
  if (!classId.value) { ElMessage.warning('请选择班级'); return }
  window.open(`/api/reports/class-report?class_id=${classId.value}`)
  ElMessage.success('报告已在新标签页打开，请按 Ctrl+P 打印为PDF')
}

async function searchStudent() {
  if (!keyword.value) return
  try {
    const r = await api.get('/students', { params: { keyword: keyword.value, per_page: 20 } })
    studentResults.value = r.data
  } catch {}
}

function exportPDF() {
  if (!selectedId.value) return
  const token = localStorage.getItem('access_token')
  const url = `/api/reports/student-report?student_id=${selectedId.value}&token=${token}`
  window.open(url, '_blank')
  ElMessage.success('报告已在新标签页打开，可按 Ctrl+P 打印为PDF')
}
</script>
