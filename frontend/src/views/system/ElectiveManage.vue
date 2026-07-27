<template>
  <div>
    <div class="page-header"><h3>选科管理</h3><p>管理学生7选3选科，查看选科组合统计</p></div>

    <!-- 筛选 -->
    <el-row :gutter="8" style="margin-bottom:12px">
      <el-col :span="2"><el-select v-model="filterYear" placeholder="入学年份" clearable @change="onYearChange" style="width:110px">
        <el-option v-for="y in yearOptions" :key="y" :label="y+'年'" :value="y" /></el-select></el-col>
      <el-col :span="3"><el-select v-model="filterClassId" placeholder="按班级" clearable @change="loadStudents" style="width:180px">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="17">
        <el-card>
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:600">学生选科列表</span>
              <div>
                <el-select v-model="batchElective" placeholder="批量设置" style="width:180px" size="small">
                  <el-option v-for="c in hotCombos" :key="c.combo" :label="c.combo+' ('+c.count+'人)'" :value="c.combo" />
                </el-select>
                <el-button size="small" type="primary" :disabled="!selected.length||!batchElective"
                  @click="batchSet" style="margin-left:8px">批量设置 ({{ selected.length }})</el-button>
              </div>
            </div>
          </template>
          <el-table :data="students" border stripe size="small" v-loading="loading"
            @selection-change="(v:any)=>selected=v" max-height="550">
            <el-table-column type="selection" width="40" />
            <el-table-column prop="student_no" label="学籍号" width="130" />
            <el-table-column prop="name" label="姓名" width="80" />
            <el-table-column prop="enrollment_year" label="入学年份" width="90" />
            <el-table-column prop="class_name" label="班级" width="120" />
            <el-table-column label="选科" min-width="150">
              <template #default="{row}">
                <template v-if="row._editing">
                  <el-checkbox-group v-model="row._elec" size="small">
                    <el-checkbox v-for="e in ELEC_SUBJS" :key="e" :label="e" :value="e" style="margin-right:4px">{{ e }}</el-checkbox>
                  </el-checkbox-group>
                </template>
                <template v-else>
                  <el-tag v-for="(e,i) in (row.electives||'').split(',').filter(Boolean)" :key="e" size="small"
                    :type="['primary','success','warning'][i]||'info'" style="margin:1px">{{ e }}</el-tag>
                  <span v-if="!row.electives" style="color:#ccc">未设置</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
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
import { ElMessage, ElMessageBox } from 'element-plus'

const ELEC_SUBJS = ['政治','历史','地理','物理','化学','生物','技术']
const yearOptions = [2023,2024,2025,2026,2027,2028,2029,2030]

const classes = ref([])
const filterYear = ref<number | null>(null)
const filterClassId = ref<number | null>(null)
const students = ref<any[]>([]); const loading = ref(false)
const page = ref(1); const total = ref(0)
const selected = ref<any[]>([]); const batchElective = ref('')
const combos = ref<any[]>([]); const totalStudents = ref(0); const totalWithElectives = ref(0)
const hotCombos = ref<any[]>([])

onMounted(async () => {
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
})

function onYearChange() { filterClassId.value = null; loadStudents() }

async function loadStudents() {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: 500 }
    if (filterClassId.value) params.class_id = filterClassId.value
    if (filterYear.value) params.enrollment_year = filterYear.value
    const r = await api.get('/students', { params })
    students.value = (r.data || []).map((s:any) => ({ ...s, _editing: false, _elec: [] }))
    total.value = r.meta?.total || students.value.length
    await loadStats()
  } catch {} finally { loading.value = false }
}

async function loadStats() {
  // 按筛选条件获取统计
  const params: any = {}
  if (filterClassId.value) params.class_id = filterClassId.value
  // backend doesn't support class_id for elective stats, use enrollment_year or grade
  if (filterYear.value) {
    // Get grade from class
  }
  try {
    const sr = await api.get('/elective-stats', { params: {} })
    // Client-side filter by displayed students
    const filtered = students.value.filter((s:any) => s.electives)
    const comboMap: Record<string, number> = {}
    filtered.forEach((s:any) => {
      const parts = (s.electives||'').split(',').filter(Boolean).sort()
      const key = parts.join(',')
      if (key) comboMap[key] = (comboMap[key]||0) + 1
    })
    combos.value = Object.entries(comboMap).map(([k,v]) => ({combo:k,count:v})).sort((a,b)=>b.count-a.count)
    totalStudents.value = students.value.length
    totalWithElectives.value = filtered.length
    hotCombos.value = combos.value.slice(0, 8)
  } catch {}
}

function editOne(row: any) {
  row._editing = true
  row._elec = (row.electives || '').split(',').filter(Boolean)
}

async function saveOne(row: any) {
  const el = row._elec.join(',')
  try {
    await api.put('/students/batch-electives', { student_ids: [row.id], electives: el })
    row.electives = el; row._editing = false
    ElMessage.success('已保存')
    loadStats()  // 自动更新统计
  } catch (e: any) { ElMessage.error(e.message) }
}

async function batchSet() {
  if (!selected.value.length || !batchElective.value) return
  try {
    await ElMessageBox.confirm(
      `将 ${selected.value.length} 名学生的选科设为 "${batchElective.value}"？`, '批量设置', { type: 'warning' })
    await api.put('/students/batch-electives', {
      student_ids: selected.value.map((s:any)=>s.id), electives: batchElective.value,
    })
    ElMessage.success('批量设置完成')
    selected.value = []; batchElective.value = ''
    loadStudents()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error(e.message) }
}
</script>
