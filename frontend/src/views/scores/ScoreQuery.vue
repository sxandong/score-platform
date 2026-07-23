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
      <el-form-item label="考试"><el-select v-model="examId2" placeholder="必选" style="width:250px" @change="onExamChange">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
      <el-form-item label="学籍号/姓名"><el-input v-model="studentKeyword" placeholder="搜索" style="width:220px"
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
    <div style="overflow-x:auto;width:100%">
    <el-table :data="scoreData" border stripe v-if="mode==='class' && scoreData.length" v-loading="loading">
      <el-table-column prop="student_no" label="学籍号" width="130" fixed />
      <el-table-column prop="student_name" label="姓名" width="90" fixed />
      <el-table-column v-for="sn in ALL_SUBJS" :key="sn" :label="sn" width="72">
        <template #default="{row}">{{ row.subjects[sn] }}</template>
      </el-table-column>
      <el-table-column prop="total" label="总分" width="80" />
      <el-table-column prop="class_rank" label="班排" width="65" />
      <el-table-column prop="grade_rank" label="级排" width="65" />
      <el-table-column prop="yws_total" label="语数外总分" width="100" />
      <el-table-column prop="yws_rank" label="语数外排名" width="100" />
      <el-table-column prop="top3_total" label="7选3总分" width="95" />
      <el-table-column prop="top3_rank" label="7选3排名" width="95" />
    </el-table>
    </div>

    <!-- 学生成绩卡片 -->
    <div v-if="mode==='student' && studentDetail" v-loading="loading">
      <el-card style="margin-top:16px">
        <template #header>
          <span style="font-size:18px;font-weight:bold">
            {{ studentDetail.name }} ({{ studentDetail.student_no }})
            — {{ studentDetail.class_name }} — {{ examName2 }}
          </span>
        </template>

        <el-row :gutter="12" style="margin-bottom:16px">
          <el-col :span="4"><el-statistic title="总分" :value="studentDetail.total" /></el-col>
          <el-col :span="4"><el-statistic title="班级排名"><span style="color:#409EFF;font-size:20px;font-weight:bold">{{ studentDetail.class_rank }}</span></el-statistic></el-col>
          <el-col :span="4"><el-statistic title="年级排名"><span style="color:#409EFF;font-size:20px;font-weight:bold">{{ studentDetail.grade_rank }}</span></el-statistic></el-col>
          <el-col :span="4"><el-statistic title="语数外"><span style="font-size:20px">{{ studentDetail.yuwai }}</span></el-statistic></el-col>
          <el-col :span="4"><el-statistic title="语数外排名"><span style="color:#E6A23C;font-size:20px;font-weight:bold">{{ studentDetail.yuwai_rank }}</span></el-statistic></el-col>
          <el-col :span="4"><el-statistic title="7选3"><span style="font-size:20px">{{ studentDetail.top3 }}</span></el-statistic></el-col>
          <el-col :span="4"><el-statistic title="7选3排名"><span style="color:#67C23A;font-size:20px;font-weight:bold">{{ studentDetail.top3_rank }}</span></el-statistic></el-col>
        </el-row>

        <h4 style="margin:12px 0 8px">语数外</h4>
        <el-table :data="ywsList" border stripe size="small">
          <el-table-column prop="name" label="科目" width="100" />
          <el-table-column prop="score" label="分数" width="80" />
          <el-table-column prop="full" label="满分" width="80" />
        </el-table>

        <h4 style="margin:12px 0 8px">7选3 (最优3科)</h4>
        <el-table :data="top3List" border stripe size="small">
          <el-table-column prop="name" label="科目" width="100" />
          <el-table-column prop="score" label="分数" width="80" />
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
const rankCache = ref<Record<string, any[]>>({})  // 缓存同一考试的排名数据

const ywsList = computed(() => {
  if (!studentDetail.value?.yws) return []
  return Object.entries(studentDetail.value.yws).map(([k,v]) => ({name:k, score:v, full:150}))
})
const top3List = computed(() => {
  if (!studentDetail.value?.top3) return []
  return Object.entries(studentDetail.value.top3).map(([k,v]) => ({name:k, score:v, full:100}))
})

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

const ALL_SUBJS = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']

function onExamChange() { studentDetail.value = null; studentResults.value = []; rankCache.value = {} }
function fmt(v: any): string { return (v === null || v === undefined || v === '') ? '-' : String(v) }

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
      loadStudentScores()
    }
  } catch {} finally { searching.value = false }
}

async function loadStudentScores() {
  const sid = selectedStudentId.value
  const eid = examId2.value
  if (!sid || !eid) return

  loading.value = true; studentDetail.value = null

  try {
    const ex = exams.value.find((e: any) => Number(e.id) === Number(eid))
    examName2.value = ex?.name || String(eid)

    // 1. 获取学生该次考试成绩
    const r1 = await api.get('/analysis/student-trend', { params: { student_id: Number(sid) } })
    const exam = r1.data.find((x: any) => Number(x.exam_id) === Number(eid))
    if (!exam) { loading.value = false; return }

    // 2. 加载排名
    const numEid = Number(eid); const numSid = Number(sid)
    const cacheKey = String(numEid)
    if (!rankCache.value[`yw_${cacheKey}`]) {
      const [rw, rt] = await Promise.all([
        api.get('/analysis/ranks', { params: { exam_id: numEid, rank_type: 'yuwai', per_page: 2000 } }),
        api.get('/analysis/ranks', { params: { exam_id: numEid, rank_type: 'top3', per_page: 2000 } }),
      ])
      rankCache.value[`yw_${cacheKey}`] = rw.data || []
      rankCache.value[`t3_${cacheKey}`] = rt.data || []
    }

    // 3. 查找排名
    const ywArr = rankCache.value[`yw_${cacheKey}`] || []
    const t3Arr = rankCache.value[`t3_${cacheKey}`] || []
    const ywMatch = ywArr.find((x: any) => Number(x.student_id) === numSid)
    const t3Match = t3Arr.find((x: any) => Number(x.student_id) === numSid)

    // 4. 学生信息
    const st = studentResults.value.find((s: any) => Number(s.id) === numSid) || {}

    studentDetail.value = {
      name: st.name || '', student_no: st.student_no || '', class_name: st.class_name || '',
      total: Number(exam.total) || 0,
      grade_rank: exam.grade_rank ?? '-',
      class_rank: exam.class_rank ?? '-',
      yuwai: ywMatch ? Number(ywMatch.total_score) : (Number(exam.yws_total) || 0),
      yuwai_rank: ywMatch ? ywMatch.rank : '-',
      top3: t3Match ? Number(t3Match.total_score) : (Number(exam.top3_total) || 0),
      top3_rank: t3Match ? t3Match.rank : '-',
      yws: exam.yws || {},
      top3: exam.top3 || {},
    }
  } catch (e: any) {
    console.error('loadStudentScores:', e)
  } finally {
    loading.value = false
  }
}
</script>
