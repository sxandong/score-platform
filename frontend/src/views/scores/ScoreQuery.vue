<template>
  <div>
    <h3>成绩查询</h3>
    <el-tabs v-model="mode">
      <el-tab-pane label="按班级查询" name="class" />
      <el-tab-pane label="按学生查询" name="student" />
    </el-tabs>

    <!-- 按班级 -->
    <el-form :inline="true" v-if="mode==='class'">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:250px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item label="班级"><el-select v-model="classId" placeholder="选择班级" style="width:200px">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select>
      </el-form-item>
      <el-form-item><el-button type="primary" @click="loadClassScores">查询</el-button></el-form-item>
    </el-form>

    <!-- 按学生 -->
    <el-form :inline="true" v-if="mode==='student'">
      <el-form-item label="考试"><el-select v-model="examId2" placeholder="必选" style="width:250px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item label="学籍号/姓名"><el-input v-model="studentKeyword" placeholder="搜索" style="width:250px"
        clearable @keyup.enter="searchStudent" /></el-form-item>
      <el-form-item><el-button type="primary" @click="searchStudent" :loading="searching">搜索</el-button></el-form-item>
    </el-form>

    <div v-if="mode==='student' && studentResults.length" style="margin-bottom:16px">
      <el-radio-group v-model="selectedStudentId" @change="loadStudentScores">
        <el-radio v-for="s in studentResults" :key="s.id" :value="s.id" border style="margin:4px 8px 4px 0">
          {{ s.name }} ({{ s.student_no }}) - {{ s.class_name }}
        </el-radio>
      </el-radio-group>
    </div>

    <!-- 班级表格 -->
    <el-table :data="scoreData" border stripe v-if="mode==='class' && scoreData.length" v-loading="loading">
      <el-table-column prop="student_no" label="学籍号" width="120" />
      <el-table-column prop="student_name" label="姓名" width="100" />
      <el-table-column v-for="(v,k) in scoreCols" :key="k" :label="k" width="100">
        <template #default="{ row }">{{ row.subjects[k] }}</template>
      </el-table-column>
      <el-table-column prop="total" label="总分" width="100" />
      <el-table-column prop="class_rank" label="班排" width="80" />
      <el-table-column prop="grade_rank" label="级排" width="80" />
    </el-table>

    <!-- 学生个人成绩卡片 -->
    <div v-if="mode==='student' && studentDetail" v-loading="loading" style="margin-top:16px">
      <el-card>
        <template #header>
          <span style="font-size:18px;font-weight:bold">
            {{ studentDetail.name }} ({{ studentDetail.student_no }}) — {{ studentDetail.class_name }}
            — {{ examName2 }}
          </span>
        </template>

        <el-row :gutter="16" style="margin-bottom:20px">
          <el-col :span="4"><el-statistic title="总分" :value="studentDetail.total" /></el-col>
          <el-col :span="4"><el-statistic title="年级排名">
            <span style="color:#409EFF;font-weight:bold">{{ studentDetail.grade_rank || '-' }}</span>
          </el-statistic></el-col>
          <el-col :span="4"><el-statistic title="语数外" :value="studentDetail.yuwai" /></el-col>
          <el-col :span="4"><el-statistic title="语数外排名">
            <span style="color:#E6A23C;font-weight:bold">{{ studentDetail.yuwai_rank || '-' }}</span>
          </el-statistic></el-col>
          <el-col :span="4"><el-statistic title="7选3" :value="studentDetail.top3" /></el-col>
          <el-col :span="4"><el-statistic title="7选3排名">
            <span style="color:#67C23A;font-weight:bold">{{ studentDetail.top3_rank || '-' }}</span>
          </el-statistic></el-col>
        </el-row>

        <el-table :data="studentDetail.subjects_list" border stripe size="small">
          <el-table-column prop="name" label="科目" width="100" />
          <el-table-column prop="score" label="分数" width="80">
            <template #default="{ row }">
              <span :style="{color: row.score === 0 ? '#ccc' : ''}">{{ row.score || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="full" label="满分" width="80" />
        </el-table>
      </el-card>
    </div>

    <el-empty v-if="!scoreData.length && !studentDetail"
      :description="mode==='class' ? '请选择考试和班级后查询' : '请选择考试并搜索学生'" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/api'

const mode = ref('class')
const exams = ref([]); const classes = ref([])
const examId = ref<number | null>(null); const classId = ref<number | null>(null)
const examId2 = ref<number | null>(null); const examName2 = ref('')
const studentKeyword = ref(''); const searching = ref(false)
const studentResults = ref<any[]>([]); const selectedStudentId = ref<number | null>(null)
const scoreData = ref<any[]>([]); const studentDetail = ref<any>(null)
const loading = ref(false)

const scoreCols = computed(() => scoreData.value[0]?.subjects || {})

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

async function loadClassScores() {
  if (!examId.value || !classId.value) return
  loading.value = true; scoreData.value = []; studentDetail.value = null
  try {
    const r = await api.get(`/scores/class/${classId.value}/exam/${examId.value}`)
    scoreData.value = r.data
  } catch {} finally { loading.value = false }
}

async function searchStudent() {
  if (!studentKeyword.value) return
  searching.value = true; studentResults.value = []; studentDetail.value = null
  try {
    const r = await api.get('/students', { params: { keyword: studentKeyword.value, per_page: 20 } })
    studentResults.value = r.data
    if (r.data.length === 1) {
      selectedStudentId.value = r.data[0].id
      await loadStudentScores()
    }
  } catch {} finally { searching.value = false }
}

async function loadStudentScores() {
  if (!selectedStudentId.value || !examId2.value) return
  loading.value = true; studentDetail.value = null
  const sid = selectedStudentId.value; const eid = examId2.value

  try {
    // 考试名
    const ex = exams.value.find((e: any) => e.id === eid)
    examName2.value = ex?.name || ''

    // 学生基本信息和成绩
    const r1 = await api.get('/analysis/student-trend', { params: { student_id: sid } })
    const exam = r1.data.find((x: any) => x.exam_id === eid)
    if (!exam) { loading.value = false; return }

    // 语数外排名
    let ywRank: any = '-', ywTotal = 0
    try {
      const r3 = await api.get('/analysis/ranks', { params: { exam_id: eid, rank_type: 'yuwai', per_page: 999 } })
      const yw = r3.data.find((x: any) => x.student_id === sid)
      if (yw) { ywRank = yw.rank; ywTotal = yw.total_score }
    } catch {}

    // 7选3排名
    let t3Rank: any = '-', t3Total = 0
    try {
      const r4 = await api.get('/analysis/ranks', { params: { exam_id: eid, rank_type: 'top3', per_page: 999 } })
      const t3 = r4.data.find((x: any) => x.student_id === sid)
      if (t3) { t3Rank = t3.rank; t3Total = t3.total_score }
    } catch {}

    // 科目列表
    const subjList: any[] = []
    for (const [sn, sv] of Object.entries(exam.subjects)) {
      const fullScore = ['语文','数学','外语'].includes(sn as string) ? 150 : 100
      subjList.push({ name: sn, score: sv, full: fullScore })
    }

    studentDetail.value = {
      name: '', student_no: '', class_name: '',
      total: exam.total, grade_rank: exam.grade_rank || '-',
      yuwai: ywTotal, yuwai_rank: ywRank,
      top3: t3Total, top3_rank: t3Rank,
      subjects_list: subjList,
    }
    // 补学生信息
    const st = studentResults.value.find((s: any) => s.id === sid)
    if (st) {
      studentDetail.value.name = st.name
      studentDetail.value.student_no = st.student_no
      studentDetail.value.class_name = st.class_name
    }
  } catch {} finally { loading.value = false }
}
</script>
