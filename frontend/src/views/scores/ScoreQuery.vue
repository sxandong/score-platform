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

    <!-- 学生表格 -->
    <div v-if="mode==='student' && scoreData.length" v-loading="loading">
      <el-alert type="info" :closable="false" show-icon style="margin:12px 0">
        <template #title>
          {{ scoreData[0]?.name }} ({{ scoreData[0]?.student_no }}) — {{ examId2 ? '单次考试' : '历次考试' }}
        </template>
      </el-alert>
      <div style="overflow-x:auto;width:100%">
      <el-table :data="scoreData" border stripe>
        <el-table-column prop="exam_name" label="考试" width="200" fixed />
        <el-table-column prop="exam_date" label="日期" width="100" />
        <el-table-column v-for="sn in visibleSubjs" :key="sn" :label="sn" width="72">
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

      <!-- 排名趋势图 -->
      <el-row :gutter="12" v-if="!examId2 && scoreData.length > 1" style="margin-top:16px">
        <el-col :span="12" v-for="sn in chartSubjs" :key="sn" style="margin-bottom:12px">
          <el-card><template #header><span style="font-weight:bold">{{ sn }} 排名趋势</span></template>
            <div :id="'chart-'+sn" style="width:100%;height:300px"></div>
          </el-card>
        </el-col>
      </el-row>
      <div v-if="!examId2 && scoreData.length > 1" style="margin-top:12px">
        <el-card style="margin-bottom:12px"><template #header><span style="font-weight:bold">总分排名趋势</span></template>
          <div id="chart-total" style="width:100%;height:380px"></div>
        </el-card>
        <el-card style="margin-bottom:12px"><template #header><span style="font-weight:bold">语数外排名趋势</span></template>
          <div id="chart-yuwai" style="width:100%;height:380px"></div>
        </el-card>
        <el-card><template #header><span style="font-weight:bold">7选3排名趋势</span></template>
          <div id="chart-top3" style="width:100%;height:380px"></div>
        </el-card>
      </div>
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
const examId2 = ref<number | null>(null)
const studentKeyword = ref(''); const searching = ref(false)
const studentResults = ref<any[]>([]); const selectedStudentId = ref<number | null>(null)
const scoreData = ref<any[]>([]); const studentDetail = ref<any>(null)
const loading = ref(false)
const rankCache = ref<Record<string, any[]>>({})

const ALL_SUBJS = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']
const visibleSubjs = computed(() => {
  const data = scoreData.value
  return ALL_SUBJS.filter(sn => data.some((row: any) => row.subjects?.[sn] != null))
})
const chartSubjs = computed(() => {
  const s = new Set<string>()
  scoreData.value.forEach((r:any) => Object.keys(r.subjects||{}).forEach((k:string) => { if (r.subjects[k] != null) s.add(k) }))
  return [...s].sort((a,b) => ALL_SUBJS.indexOf(a) - ALL_SUBJS.indexOf(b))
})

function onTabChange() { scoreData.value = []; studentDetail.value = null; studentResults.value = []; rankCache.value = {} }
function onExamChange() { studentDetail.value = null; studentResults.value = []; rankCache.value = {} }

onMounted(async () => {
  try { const r = await api.get('/exams'); exams.value = r.data } catch {}
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

async function loadClassScores() {
  if (!examId.value || !classId.value) return
  loading.value = true; scoreData.value = []
  try { const r = await api.get(`/scores/class/${classId.value}/exam/${examId.value}`); scoreData.value = r.data }
  catch {} finally { loading.value = false }
}

async function searchStudent() {
  if (!studentKeyword.value) return
  searching.value = true; studentResults.value = []; scoreData.value = []
  try {
    const r = await api.get('/students', { params: { keyword: studentKeyword.value, per_page: 20 } })
    studentResults.value = r.data
    if (r.data.length === 1) { selectedStudentId.value = r.data[0].id; await loadStudentScores() }
  } catch {} finally { searching.value = false }
}

async function loadStudentScores() {
  const sid = selectedStudentId.value
  if (!sid) return
  loading.value = true; scoreData.value = []
  try {
    const numSid = Number(sid)
    const st = studentResults.value.find((s: any) => Number(s.id) === numSid) || {}
    const r1 = await api.get('/analysis/student-trend', { params: { student_id: numSid } })
    let examList = r1.data || []
    if (!examList.length) { loading.value = false; return }

    if (examId2.value) {
      examList = examList.filter((x: any) => Number(x.exam_id) === Number(examId2.value))
    }

    const rows: any[] = []
    for (const exam of examList) {
      const numEid = Number(exam.exam_id); const cacheKey = String(numEid)
      if (!rankCache.value[`yw_${cacheKey}`]) {
        try {
          const [rw, rt, rs] = await Promise.all([
            api.get('/analysis/ranks', { params: { exam_id: numEid, rank_type: 'yuwai', per_page: 2000 } }),
            api.get('/analysis/ranks', { params: { exam_id: numEid, rank_type: 'top3', per_page: 2000 } }),
            api.get('/analysis/ranks', { params: { exam_id: numEid, rank_type: 'subject', per_page: 5000 } }),
          ])
          rankCache.value[`yw_${cacheKey}`] = rw.data || []
          rankCache.value[`t3_${cacheKey}`] = rt.data || []
          rankCache.value[`subj_${cacheKey}`] = rs.data || []
        } catch {}
      }
      const ywArr = rankCache.value[`yw_${cacheKey}`] || []
      const t3Arr = rankCache.value[`t3_${cacheKey}`] || []
      const ywMatch = ywArr.find((x: any) => Number(x.student_id) === numSid)
      const t3Match = t3Arr.find((x: any) => Number(x.student_id) === numSid)

      rows.push({
        exam_id: exam.exam_id, name: st.name || '', student_no: st.student_no || '',
        exam_name: exam.exam_name, exam_date: exam.exam_date,
        subjects: exam.subjects || {},
        total: Number(exam.total) || 0,
        grade_rank: exam.grade_rank ?? '-', class_rank: exam.class_rank ?? '-',
        yuwai: ywMatch ? Number(ywMatch.total_score) : (Number(exam.yws_total) || 0),
        yuwai_rank: ywMatch ? ywMatch.rank : '-',
        top3: t3Match ? Number(t3Match.total_score) : (Number(exam.top3_total) || 0),
        top3_rank: t3Match ? t3Match.rank : '-',
      })
    }
    scoreData.value = rows

    // 绘制图表
    if (!examId2.value && rows.length > 1) {
      await nextTick(); await new Promise(r => setTimeout(r, 200))
      drawCharts(rows, numSid)
    }
  } catch (e: any) { console.error(e) }
  finally { loading.value = false }
}

function drawCharts(data: any[], numSid: number) {
  // 按日期升序排列
  const sorted = [...data].sort((a:any,b:any) => (a.exam_date||'').localeCompare(b.exam_date||''))
  const labels = sorted.map((r:any) =>
    (r.exam_name||'').replace(/高三|适应性考试/g,'').substring(0,12) || r.exam_date||'')

  function makeRankChart(domId: string, rankKey: string, title: string) {
    const el = document.getElementById(domId); if (!el) return
    echarts.init(el).setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 55, right: 20, top: 20, bottom: 25 },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', name: '排名', inverse: true, min: 1 },
      series: [{ name: title, type: 'line', data: sorted.map((r:any)=>r[rankKey]),
        smooth: true, markLine: { data: [{ type: 'average', name: '平均' }] } }],
    })
  }

  // 各科排名
  chartSubjs.value.forEach(sn => {
    const el = document.getElementById('chart-'+sn); if (!el) return
    const ranks = sorted.map((r:any) => {
      const cache = rankCache.value[`subj_${r.exam_id}`] || []
      const f = cache.find((x:any) => x.subject_name === sn && Number(x.student_id) === numSid)
      return f ? f.rank : null
    })
    echarts.init(el).setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 55, right: 20, top: 20, bottom: 25 },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', name: '排名', inverse: true, min: 1 },
      series: [{ name: sn+'排名', type: 'line', data: ranks, smooth: true,
        markLine: { data: [{ type: 'average', name: '平均排名' }] } }],
    })
  })

  makeRankChart('chart-total', 'grade_rank', '总分排名')
  makeRankChart('chart-yuwai', 'yuwai_rank', '语数外排名')
  makeRankChart('chart-top3', 'top3_rank', '7选3排名')
}
</script>
