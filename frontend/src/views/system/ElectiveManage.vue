<template>
  <div>
    <div class="page-header"><h3>选科管理</h3><p>管理学生7选3选科，查看选科组合统计</p></div>

    <!-- 筛选 -->
    <el-row :gutter="8" style="margin-bottom:12px">
      <el-col :span="2"><el-select v-model="filterYear" placeholder="入学年份" @change="onYearChange" style="width:110px">
        <el-option v-for="y in yearOptions" :key="y" :label="y+'年'" :value="y" /></el-select></el-col>
      <el-col :span="3"><el-select v-model="filterClassId" placeholder="按班级" clearable :disabled="!filterYear" @change="loadStudents">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-col>
      <el-col :span="4"><el-select v-model="filterCombo" placeholder="选科组合(最多3门)" multiple :multiple-limit="3" clearable :disabled="!filterYear" @change="loadStudents" style="width:320px">
        <el-option v-for="e in ELEC_SUBJS" :key="e" :label="e" :value="e" /></el-select></el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="17">
        <el-card>
          <template #header><span style="font-weight:600">学生选科列表</span></template>
          <el-table :data="students" border stripe  v-loading="loading"
            max-height="550" size="small">
            <el-table-column prop="student_no" label="学籍号" width="140" />
            <el-table-column prop="name" label="姓名" width="140" />  
            <el-table-column prop="enrollment_year" label="入学年份" width="100" />
            <el-table-column prop="class_name" label="班级" width="120" />
            <el-table-column label="选科" min-width="150">
              <template #default="{row}">
                <template v-if="row._editing">
                  <el-checkbox-group v-model="row._elec" size="small" :max="3">
                    <el-checkbox v-for="e in ELEC_SUBJS" :key="e" :label="e" :value="e"
                      :disabled="row._elec.length>=3 && !row._elec.includes(e)" style="margin-right:4px">{{ e }}</el-checkbox>
                  </el-checkbox-group>
                </template>
                <template v-else>
                  <el-tag v-for="(e,i) in (row.electives||'').split(',').filter(Boolean)" :key="e" size="small"
                    :type="['primary','success','warning'][i]||'info'" style="margin:1px">{{ e }}</el-tag>
                  <span v-if="!row.electives" style="color:#ccc">未设置</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{row}">
                <template v-if="row._editing">
                  <el-button size="small" type="primary" @click="saveOne(row)">保存</el-button>
                  <el-button size="small" @click="row._editing=false">取消</el-button>
                </template>
                <template v-else>
                  <el-button size="small" @click="editOne(row)">编辑</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination :current-page="page" :total="total" :page-size="100" small
            layout="total,prev,pager,next" @current-change="(p:number)=>{page=p;loadStudents()}"
            style="margin-top:8px;justify-content:flex-end" />
        </el-card>
      </el-col>

      <el-col :span="7">
        <el-card>
          <template #header><span style="font-weight:600">选科组合统计</span></template>
          <div v-loading="loading" style="max-height:550px;overflow-y:auto">
            <div v-for="c in combos" :key="c.combo" style="padding:6px 0;border-bottom:1px solid #f0f0f0;
              display:flex;justify-content:space-between">
              <span>{{ c.combo }}</span>
              <el-tag size="small" type="primary">{{ c.count }}人</el-tag>
            </div>
            <el-empty v-if="!combos.length" description="暂无数据" :image-size="60" />
            <div v-if="combos.length" style="margin-top:8px;font-size:13px;color:var(--tx-secondary)">
              已选科: {{ totalWithElectives }} / {{ totalStudents }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const ELEC_SUBJS = ['政治','历史','地理','物理','化学','生物','技术']
const yearOptions = Array.from({length:7}, (_,i) => new Date().getFullYear() - 6 + i)

const classes = ref([])
const filterYear = ref<number | null>(null)
const filterClassId = ref<number | null>(null)
const filterCombo = ref<string[]>([])
const students = ref<any[]>([]); const loading = ref(false)
const page = ref(1); const total = ref(0)
const combos = ref<any[]>([]); const totalStudents = ref(0); const totalWithElectives = ref(0)
const allStudents = ref<any[]>([])

onMounted(async () => {
  // 初始化时不加载数据，等待用户选择入学年份
})

async function onYearChange() {
  filterClassId.value = null
  filterCombo.value = []
  classes.value = []
  if (!filterYear.value) return
  // 加载该年份有学生的班级
  try {
    const r = await api.get('/students', { params: { enrollment_year: filterYear.value, per_page: 5000 } })
    const studentData = r.data || []
    const classIds = new Set(studentData.map((s: any) => s.class_id))
    // 获取所有班级，然后过滤出该年份有学生的班级
    const allClasses = await api.get('/classes')
    classes.value = (allClasses.data || []).filter((c: any) => classIds.has(c.id))
  } catch {}
  loadStudents()
}

async function loadStudents() {
  if (!filterYear.value) {
    students.value = []
    total.value = 0
    combos.value = []
    allStudents.value = []
    return
  }
  loading.value = true
  try {
    const params: any = { page: 1, per_page: 5000, enrollment_year: filterYear.value }
    if (filterClassId.value) params.class_id = filterClassId.value
    const r = await api.get('/students', { params })
    let allData = (r.data || []).map((s:any) => ({ ...s, _editing: false, _elec: [] }))
    // 选科组合筛选
    if (filterCombo.value.length) {
      allData = allData.filter((s:any) => {
        const elecs = (s.electives||'').split(',').filter(Boolean)
        return filterCombo.value.every((c:string) => elecs.includes(c))
      })
    }
    allStudents.value = allData
    const start = (page.value - 1) * 100
    students.value = allData.slice(start, start + 100)
    total.value = allData.length
    await loadStats()
  } catch {} finally { loading.value = false }
}

async function loadStats() {
  const SUBJ_ORDER = ['物理','化学','生物','政治','历史','地理','技术']
  const filtered = allStudents.value.filter((s:any) => s.electives)
  const comboMap: Record<string, number> = {}
  filtered.forEach((s:any) => {
    const parts = (s.electives||'').split(',').filter(Boolean)
    parts.sort((a:any,b:any) => SUBJ_ORDER.indexOf(a) - SUBJ_ORDER.indexOf(b))
    const key = parts.join(',')
    if (key) comboMap[key] = (comboMap[key]||0) + 1
  })
  combos.value = Object.entries(comboMap).map(([k,v]) => ({combo:k,count:v})).sort((a,b)=>b.count-a.count)
  totalStudents.value = allStudents.value.length
  totalWithElectives.value = filtered.length
}

function editOne(row: any) {
  row._editing = true
  row._elec = (row.electives || '').split(',').filter(Boolean)
}

async function saveOne(row: any) {
  if (row._elec.length !== 3) { ElMessage.warning('选科必须恰好3门'); return }
  const el = row._elec.join(',')
  try {
    await api.put('/students/batch-electives', { student_ids: [row.id], electives: el })
    row.electives = el; row._editing = false
    ElMessage.success('已保存')
    loadStats()  // 自动更新统计
  } catch (e: any) { ElMessage.error(e.message) }
}

</script>

<style scoped>
:deep(.el-table th.el-table__cell) { background: linear-gradient(180deg,#f0f5fa,#e8f0fe); color:var(--edu-blue); font-weight:600; text-align:center; }
:deep(.el-table td) { text-align:center; }
</style>