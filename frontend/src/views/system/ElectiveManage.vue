<template>
  <div>
    <div class="page-header"><h3>选科管理</h3><p>管理学生7选3选科信息，查看选科组合统计</p></div>

    <el-form :inline="true" style="margin-bottom:16px">
      <el-form-item label="年级"><el-select v-model="filterGradeId" clearable @change="loadData" style="width:150px">
        <el-option v-for="g in grades" :key="g.id" :label="g.name" :value="g.id" /></el-select>
      </el-form-item>
    </el-form>

    <el-row :gutter="16">
      <!-- 学生列表 -->
      <el-col :span="17">
        <el-card>
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:600">学生选科列表</span>
              <div>
                <el-select v-model="batchElective" placeholder="批量设置选科" style="width:180px" size="small">
                  <el-option v-for="c in hotCombos" :key="c.combo" :label="c.combo+' ('+c.count+'人)'" :value="c.combo" />
                </el-select>
                <el-button size="small" type="primary" :disabled="!selected.length || !batchElective"
                  @click="batchSet" style="margin-left:8px">批量设置 ({{ selected.length }})</el-button>
              </div>
            </div>
          </template>
          <el-table :data="students" border stripe size="small" v-loading="loading"
            @selection-change="(v:any)=>selected=v" max-height="600">
            <el-table-column type="selection" width="40" />
            <el-table-column prop="student_no" label="学籍号" width="130" />
            <el-table-column prop="name" label="姓名" width="80" />
            <el-table-column prop="class_name" label="班级" width="120" />
            <el-table-column label="选科" width="160">
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
                  <el-button size="small" @click="row._editing=false;row._elec=[]">取消</el-button>
                </template>
                <template v-else>
                  <el-button size="small" @click="editOne(row)">编辑</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination :current-page="page" :total="total" :page-size="100" small
            layout="total, prev, pager, next" @current-change="(p:number)=>{page=p;loadData()}"
            style="margin-top:8px;justify-content:flex-end" />
        </el-card>
      </el-col>

      <!-- 选科统计 -->
      <el-col :span="7">
        <el-card>
          <template #header><span style="font-weight:600">选科组合统计</span></template>
          <div v-loading="loading" style="max-height:600px;overflow-y:auto">
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

const grades = ref([]); const filterGradeId = ref<number | null>(null)
const students = ref<any[]>([]); const loading = ref(false)
const page = ref(1); const total = ref(0)
const selected = ref<any[]>([]); const batchElective = ref('')
const combos = ref<any[]>([])
const totalStudents = ref(0); const totalWithElectives = ref(0)
const hotCombos = ref<any[]>([])

onMounted(async () => {
  try { const r = await api.get('/grades'); grades.value = r.data } catch {}
})

async function loadData() {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: 100 }
    if (filterGradeId.value) {
      // 按年级获取所有班级的学生
      const cr = await api.get('/classes', { params: { grade_id: filterGradeId.value } })
      const classIds = cr.data.map((c:any) => c.id)
      if (classIds.length) params.class_id = classIds[0]
      // Actually need to get students by grade_id, not class_id
    }
    const r = await api.get('/students', { params: { per_page: 500, page: page.value } })
    let allStudents = r.data
    if (filterGradeId.value) {
      // Filter by grade via class
      const cr = await api.get('/classes', { params: { grade_id: filterGradeId.value } })
      const classIds = cr.data.map((c:any) => c.id)
      allStudents = allStudents.filter((s:any) => classIds.includes(s.class_id))
    }
    students.value = allStudents.map((s:any) => ({ ...s, _editing: false, _elec: [] }))
    total.value = r.meta?.total || allStudents.length

    // 选科统计
    const sr = await api.get('/elective-stats', { params: { grade_id: filterGradeId.value || undefined } })
    combos.value = sr.data?.combos || []
    totalStudents.value = sr.data?.total || 0
    totalWithElectives.value = sr.data?.with_electives || 0
    hotCombos.value = combos.value.slice(0, 8)
  } catch {} finally { loading.value = false }
}

function editOne(row: any) {
  row._editing = true
  row._elec = (row.electives || '').split(',').filter(Boolean)
}

async function saveOne(row: any) {
  const electives = row._elec.join(',')
  try {
    await api.put('/students/batch-electives', { student_ids: [row.id], electives })
    row.electives = electives; row._editing = false
    ElMessage.success('已保存')
  } catch (e: any) { ElMessage.error(e.message) }
}

async function batchSet() {
  if (!selected.value.length || !batchElective.value) return
  try {
    await ElMessageBox.confirm(
      `将 ${selected.value.length} 名学生的选科设置为 "${batchElective.value}"？`,
      '批量设置选科', { type: 'warning' }
    )
    await api.put('/students/batch-electives', {
      student_ids: selected.value.map((s:any) => s.id),
      electives: batchElective.value,
    })
    ElMessage.success('批量设置完成')
    selected.value = []; batchElective.value = ''
    loadData()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error(e.message) }
}
</script>
