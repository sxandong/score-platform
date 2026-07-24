<template>
  <div>
    <h3>成绩查询</h3>
    <el-tabs v-model="mode" @tab-change="onTabChange">
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
      <el-form-item label="考试"><el-select v-model="examId2" placeholder="可选，不选显示全部" clearable style="width:250px" @change="onExamChange">
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
      <el-table-column v-for="sn in visibleSubjs" :key="sn" :label="sn" width="72">
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

    <!-- 单个学生结果 (选考试时单行, 未选时多行) -->
    <div v-if="mode==='student' && (studentDetail || scoreData.length)" v-loading="loading" style="margin-top:16px">
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px" v-if="examId2 && studentDetail">
        <template #title>
          {{ studentDetail.name }} ({{ studentDetail.student_no }})
          <span v-if="studentDetail.class_name"> — {{ studentDetail.class_name }}</span>
          — {{ examName2 }}
        </template>
      </el-alert>
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px" v-if="!examId2 && scoreData.length">
        <template #title>
          {{ scoreData[0]?.name }} ({{ scoreData[0]?.student_no }}) — 历次考试成绩
        </template>
      </el-alert>

      <div style="overflow-x:auto;width:100%">
      <el-table :data="examId2 && studentDetail ? [studentDetail] : scoreData" border stripe>
        <el-table-column v-if="!examId2" prop="exam_name" label="考试" width="200" fixed />
        <el-table-column v-if="!examId2" prop="exam_date" label="日期" width="110" />
        <el-table-column prop="student_no" label="学籍号" width="130" v-if="examId2" />
        <el-table-column prop="name" label="姓名" width="90" v-if="examId2" />
        <el-table-column v-for="sn in (examId2 ? studentSubjs : visibleSubjs)" :key="sn" :label="sn" width="72">
          <template #default="{row}">{{ row.subjects[sn] }}</template>
        </el-table-column>
        <el-table-column prop="total" label="总分" width="80" />
        <el-table-column prop="class_rank" label="班排" width="65" />
        <el-table-column prop="grade_rank" label="级排" width="65" />
        <el-table-column prop="yuwai" label="语数外总分" width="100" />
        <el-table-column prop="yuwai_rank" label="语数外排名" width="100" />
        <el-table-column prop="top3" label="7选3总分" width="95" />
        <el-table-column prop="top3_rank" label="7选3排名" width="95" />
      </el-table>
      </div>
    </div>

    <!-- 历次考试趋势图 -->
    <div v-if="mode==='student' && !examId2 && scoreData.length > 1" style="margin-top:16px">
      <el-card><template #header><span style="font-weight:bold">成绩趋势图</span></template>
        <div ref="trendChart" style="width:100%;height:400px"></div>
      </el-card>
    </div>

    <el-empty v-if="!scoreData.length && !studentDetail"
      :description="mode==='class' ? '请选择考试和班级后查询' : '搜索学生即可查看成绩'" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'

const mode = ref('class')
const exams = ref([]); const classes = ref([])
const examId = ref<number | null>(null); const classId = ref<number | null>(null)
const examId2 = ref<number | null>(null); const examName2 = ref('')
const studentKeyword = ref(''); const searching = ref(false)
const studentResults = ref<any[]>([]); const selectedStudentId = ref<number | null>(null)
const scoreData = ref<any[]>([]); const studentDetail = ref<any>(null)
const loading = ref(false)
const rankCache = ref<Record<string, any[]>>({})
const trendChart = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null

// 绘制趋势图
watch([scoreData, mode], async () => {
  await nextTick()
  if (mode.value !== 'student' || examId2.value || scoreData.value.length <= 1) {
    chartInstance?.dispose(); chartInstance = null; return
  }
  if (!trendChart.value) return

  if (!chartInstance) chartInstance = echarts.init(trendChart.value)
  const data = [...scoreData.value].reverse() // 时间正序

  const option: any = {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, type: 'scroll' },
    grid: { left: 50, right: 120, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: data.map((r:any) => r.exam_name?.replace('高三','').replace('适应性考试','适应') || '') },
    yAxis: [
      { type: 'value', name: '分数', min: 0 },
      { type: 'value', name: '排名', inverse: true, min: 1 },
    ],
    series: [
      { name: '总分', type: 'line', data: data.map((r:any) => r.total), smooth: true },
      { name: '语数外', type: 'line', data: data.map((r:any) => r.yuwai), smooth: true },
      { name: '7选3', type: 'line', data: data.map((r:any) => r.top3), smooth: true },
      { name: '总分排名', type: 'line', yAxisIndex: 1, data: data.map((r:any) => r.grade_rank), smooth: true,
        lineStyle: { type: 'dashed' } },
      { name: '语数外排名', type: 'line', yAxisIndex: 1, data: data.map((r:any) => r.yuwai_rank), smooth: true,
        lineStyle: { type: 'dashed' } },
      { name: '7选3排名', type: 'line', yAxisIndex: 1, data: data.map((r:any) => r.top3_rank), smooth: true,
        lineStyle: { type: 'dashed' } },
    ],
  }
  chartInstance.setOption(option, true)
})


onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

const ALL_SUBJS = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']

// 表格中只显示有数据的科目列
const visibleSubjs = computed(() => {
  const data = scoreData.value.length ? scoreData.value : (studentDetail.value ? [studentDetail.value] : [])
  return ALL_SUBJS.filter(sn => data.some((row: any) => row.subjects?.[sn] != null))
})
// 学生查询中只显示有数据的科目列
const studentSubjs = computed(() => {
  if (!studentDetail.value?.subjects) return []
  return ALL_SUBJS.filter(sn => studentDetail.value.subjects[sn] != null)
})

function onTabChange() {
  scoreData.value = []; studentDetail.value = null
  studentResults.value = []; selectedStudentId.value = null
  rankCache.value = {}
}
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
  if (!sid) return

  loading.value = true; studentDetail.value = null; scoreData.value = []

  try {
    const numSid = Number(sid)
    const st = studentResults.value.find((s: any) => Number(s.id) === numSid) || {}

    // 获取学生所有考试成绩
    const r1 = await api.get('/analysis/student-trend', { params: { student_id: numSid } })
    let examList = r1.data || []
    if (!examList.length) { loading.value = false; return }

    // 如果选了考试则只显示该考试
    if (eid) {
      const numEid = Number(eid)
      examList = examList.filter((x: any) => Number(x.exam_id) === numEid)
      if (!examList.length) { loading.value = false; return }
      const ex = exams.value.find((e: any) => Number(e.id) === numEid)
      examName2.value = ex?.name || String(eid)
    }

    // 为每场考试加载排名
    const rows: any[] = []
    for (const exam of examList) {
      const numEid = Number(exam.exam_id)
      const cacheKey = String(numEid)

      if (!rankCache.value[`yw_${cacheKey}`]) {
        const [rw, rt] = await Promise.all([
          api.get('/analysis/ranks', { params: { exam_id: numEid, rank_type: 'yuwai', per_page: 2000 } }),
          api.get('/analysis/ranks', { params: { exam_id: numEid, rank_type: 'top3', per_page: 2000 } }),
        ])
        rankCache.value[`yw_${cacheKey}`] = rw.data || []
        rankCache.value[`t3_${cacheKey}`] = rt.data || []
      }

      const ywArr = rankCache.value[`yw_${cacheKey}`] || []
      const t3Arr = rankCache.value[`t3_${cacheKey}`] || []
      const ywMatch = ywArr.find((x: any) => Number(x.student_id) === numSid)
      const t3Match = t3Arr.find((x: any) => Number(x.student_id) === numSid)

      rows.push({
        name: st.name || '', student_no: st.student_no || '',
        exam_name: exam.exam_name, exam_date: exam.exam_date,
        subjects: exam.subjects || {},
        total: Number(exam.total) || 0,
        grade_rank: exam.grade_rank ?? '-',
        class_rank: exam.class_rank ?? '-',
        yuwai: ywMatch ? Number(ywMatch.total_score) : (Number(exam.yws_total) || 0),
        yuwai_rank: ywMatch ? ywMatch.rank : '-',
        top3: t3Match ? Number(t3Match.total_score) : (Number(exam.top3_total) || 0),
        top3_rank: t3Match ? t3Match.rank : '-',
      })
    }

    if (eid && rows.length === 1) {
      studentDetail.value = rows[0]
    } else {
      scoreData.value = rows as any
    }
  } catch (e: any) { console.error(e) }
  finally { loading.value = false }
}
</script>
