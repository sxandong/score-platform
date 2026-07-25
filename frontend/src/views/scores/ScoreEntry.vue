<template>
  <div>
    <div class="page-header"><h3>成绩录入</h3><p>按班级录入或修改考试成绩</p></div>

    <el-form :inline="true">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" @change="loadStudents" style="width:300px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item label="班级"><el-select v-model="classId" placeholder="选择班级" @change="loadStudents" style="width:200px">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select>
      </el-form-item>
    </el-form>

    <!-- 状态提示 -->
    <el-alert v-if="hasExisting" class="info-bar" :closable="false" show-icon style="margin-bottom:12px"
      title="该考试已有成绩，提交后将更新原有数据。" />
    <el-alert v-if="examId && classId && !hasExisting && scoreRows.length" type="success" :closable="false" show-icon style="margin-bottom:12px"
      title="该考试暂无成绩，将作为新数据录入。" />

    <el-table :data="scoreRows" border stripe v-if="examId && classId" style="margin-top:12px">
      <el-table-column prop="student_no" label="学籍号" width="130" fixed />
      <el-table-column prop="student_name" label="姓名" width="100" fixed />
      <el-table-column v-for="s in examSubjects" :key="s.id" :label="s.subject_name" width="120">
        <template #default="{ row }">
          <el-input-number v-model="row.scores[s.subject_id]" :min="0" :max="s.full_score"
            size="small" controls-position="right" style="width:100px" />
        </template>
      </el-table-column>
    </el-table>

    <div v-if="scoreRows.length" style="margin-top:16px;display:flex;align-items:center;gap:12px">
      <el-button type="primary" @click="submitScores" :loading="submitting" size="large">
        {{ hasExisting ? '更新成绩' : '提交成绩' }}
      </el-button>
      <span style="color:var(--tx-secondary);font-size:13px">
        共 {{ scoreRows.length }} 名学生，{{ examSubjects.length }} 个科目
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const exams = ref([]); const classes = ref([])
const examId = ref<number | null>(null); const classId = ref<number | null>(null)
const examSubjects = ref<any[]>([]); const scoreRows = ref<any[]>([])
const submitting = ref(false); const hasExisting = ref(false)

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

async function loadStudents() {
  if (!examId.value || !classId.value) return
  try {
    const exr = await api.get(`/exams/${examId.value}`)
    examSubjects.value = exr.data.subjects

    // 加载班级学生
    const sr = await api.get('/students', { params: { class_id: classId.value, per_page: 100 } })
    const students = sr.data

    // 检查是否已有成绩
    hasExisting.value = false
    let existingScores: any[] = []
    try {
      const er = await api.get(`/scores/class/${classId.value}/exam/${examId.value}`)
      if (er.data?.length) {
        hasExisting.value = true
        existingScores = er.data
      }
    } catch {}

    // 构建科目名称→ID映射
    const subjNameToId: Record<string, number> = {}
    examSubjects.value.forEach((subj: any) => { subjNameToId[subj.subject_name] = subj.id })

    // 构建行数据(有现有成绩则回填)
    scoreRows.value = students.map((s: any) => {
      const row: any = { student_id: s.id, student_no: s.student_no, student_name: s.name, scores: {} }
      if (hasExisting.value) {
        const es = existingScores.find((x: any) => x.student_id === s.id)
        if (es?.subjects) {
          for (const [subjName, scoreVal] of Object.entries(es.subjects)) {
            const sid = subjNameToId[subjName]
            if (sid !== undefined) row.scores[sid] = scoreVal
          }
        }
      }
      return row
    })
  } catch (e: any) { ElMessage.error(e.message) }
}

async function submitScores() {
  if (hasExisting.value) {
    try {
      await ElMessageBox.confirm('该考试已有成绩数据，提交将覆盖更新原有数据。确定提交？', '确认更新', {
        type: 'warning', confirmButtonText: '确定更新', cancelButtonText: '取消'
      })
    } catch { return }
  }

  submitting.value = true
  try {
    const scores: any[] = []
    scoreRows.value.forEach(row => {
      Object.entries(row.scores).forEach(([subjId, score]) => {
        scores.push({ student_id: row.student_id, subject_id: parseInt(subjId), total_score: score })
      })
    })
    if (!scores.length) { ElMessage.warning('请至少录入一个成绩'); submitting.value = false; return }
    await api.post('/scores', { exam_id: examId.value, scores })
    ElMessage.success(hasExisting.value ? '成绩更新成功' : '成绩提交成功')
  } catch (e: any) { ElMessage.error(e.message) }
  submitting.value = false
}
</script>
