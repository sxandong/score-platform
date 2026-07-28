<template>
  <div>
    <div class="page-header"><h3>系统仪表盘</h3><p>数据驱动的教学质量分析平台</p></div>

    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="6" v-for="(c,i) in statCards" :key="i">
        <el-card shadow="hover" :body-style="{padding:'20px'}">
          <div style="display:flex;align-items:center;justify-content:space-between">
            <div>
              <div style="font-size:28px;font-weight:700" :style="{color:c.color}">{{ c.value }}</div>
              <div style="font-size:13px;color:var(--tx-secondary);margin-top:4px">{{ c.label }}</div>
            </div>
            <el-icon :size="36" :color="c.color"><component :is="c.icon" /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="16">
        <el-card>
          <template #header><span style="font-weight:600">快捷入口</span></template>
          <el-row :gutter="12">
            <el-col :span="8" v-for="(link,i) in quickLinks" :key="i">
              <router-link :to="link.path" style="text-decoration:none">
                <div class="quick-card" style="padding:20px;text-align:center;border:1px solid var(--border-color);
                  border-radius:8px;transition:all .2s;cursor:pointer">
                  <el-icon :size="28" :color="link.color"><component :is="link.icon" /></el-icon>
                  <div style="font-weight:600;margin-top:8px;color:var(--tx-primary)">{{ link.label }}</div>
                  <div style="font-size:12px;color:var(--tx-secondary);margin-top:4px">{{ link.desc }}</div>
                </div>
              </router-link>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><span style="font-weight:600">操作指引</span></template>
          <el-steps direction="vertical" :active="4" space="24px">
            <el-step title="数据准备" description="导入学生名单与选科信息" />
            <el-step title="创建考试" description="新建考试并关联科目" />
            <el-step title="录入成绩" description="单条录入或Excel批量导入" />
            <el-step title="查询分析" description="查看成绩与排名趋势" />
          </el-steps>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const statCards = ref([
  { label:'考试场次', value:'-', icon:'Tickets', color:'var(--edu-blue)' },
  { label:'学生人数', value:'-', icon:'User', color:'var(--edu-green)' },
  { label:'班级数量', value:'-', icon:'School', color:'var(--edu-gold)' },
  { label:'用户数量', value:'-', icon:'Avatar', color:'#e04040' },
])
const isTeacher = computed(() => {
  const auth = useAuthStore()
  return auth.hasRole('teacher') && !auth.hasRole('admin') && !auth.hasRole('director')
})
const quickLinks = computed(() => {
  if (isTeacher.value) {
    return [
      { path:'/scores/query', label:'成绩查询', desc:'班级与学生成绩', icon:'Search', color:'var(--edu-gold)' },
      { path:'/analysis/class-compare', label:'班级统计', desc:'各班达线人数', icon:'DataLine', color:'var(--edu-blue)' },
      { path:'/analysis/multi-exam-compare', label:'班级对比', desc:'多考试对比', icon:'TrendCharts', color:'#7b61ff' },
      { path:'/analysis/score-distribution', label:'分数段统计', desc:'各科分数分布', icon:'PieChart', color:'#00897b' },
      { path:'/analysis/student-trend', label:'成绩趋势', desc:'上线人数趋势', icon:'TrendCharts', color:'var(--edu-green)' },
    ]
  }
  return [
    { path:'/exams', label:'考试管理', desc:'创建与管理考试', icon:'Document', color:'var(--edu-blue)' },
    { path:'/scores/entry', label:'成绩录入', desc:'录入各科成绩', icon:'Edit', color:'var(--edu-green)' },
    { path:'/scores/query', label:'成绩查询', desc:'班级与学生成绩', icon:'Search', color:'var(--edu-gold)' },
    { path:'/students', label:'学生管理', desc:'学籍与选科', icon:'Avatar', color:'#e04040' },
    { path:'/analysis/class-compare', label:'班级统计', desc:'各班达线人数', icon:'TrendCharts', color:'#7b61ff' },
    { path:'/reports', label:'报表导出', desc:'成绩单与报表', icon:'Download', color:'#00897b' },
  ]
})

onMounted(async () => {
  try {
    const [r1,r2,r3,r4] = await Promise.all([
      api.get('/exams'), api.get('/students',{params:{per_page:1}}),
      api.get('/classes'), api.get('/users'),
    ])
    statCards.value[0].value = r1.meta?.total || 0
    statCards.value[1].value = r2.meta?.total || 0
    statCards.value[2].value = r3.data?.length || 0
    statCards.value[3].value = r4.meta?.total || 0
  } catch {}
})
</script>

<style scoped>
.quick-card:hover { border-color:var(--edu-blue); box-shadow:0 2px 12px rgba(26,84,144,.12); }
</style>
