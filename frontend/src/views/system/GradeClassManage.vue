<template>
  <div>
    <h3>年级与班级管理</h3>
    <el-tabs v-model="activeTab">
      <!-- ========== 年级 ========== -->
      <el-tab-pane label="年级" name="grades">
        <div style="margin-bottom:16px">
          <el-button type="primary" @click="openGradeDialog()">新增年级</el-button>
          <el-button type="danger" :disabled="!gSelected.length" @click="batchDeleteGrades">
            批量删除 ({{ gSelected.length }})
          </el-button>
        </div>
        <el-table :data="grades" border size="small" stripe v-loading="gLoading" @selection-change="(v:any)=>gSelected=v">
          <el-table-column type="selection" width="40" />
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="年级名称" />
          <el-table-column label="学段" width="100">
            <template #default="{ row }">{{ stageMap[row.stage] || row.stage }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" @click="openGradeDialog(row)">编辑</el-button>
              <el-popconfirm title="删除年级将同时删除关联班级和学生?" @confirm="deleteGrade(row.id)">
                <template #reference><el-button size="small" type="danger">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="gradeDialog" :title="editingGrade ? '编辑年级' : '新增年级'" width="400px">
          <el-form :model="gradeForm" label-width="80px">
            <el-form-item label="名称"><el-input v-model="gradeForm.name" /></el-form-item>
            <el-form-item label="学段">
              <el-select v-model="gradeForm.stage">
                <el-option label="高中" value="高中" /><el-option label="初中" value="初中" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="gradeDialog=false">取消</el-button>
            <el-button type="primary" @click="saveGrade">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- ========== 班级 ========== -->
      <el-tab-pane label="班级" name="classes">
        <div style="margin-bottom:16px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          <el-select v-model="classGradeFilter" placeholder="按年级筛选" clearable @change="loadClasses" style="width:150px">
            <el-option v-for="g in grades" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
          <el-button type="primary" @click="openClassDialog()">单个新增</el-button>
          <el-button type="success" @click="showAutoGen=true">按数量生成</el-button>
          <el-button type="warning" @click="showBatchDialog=true">批量输入</el-button>
          <el-upload :show-file-list="false" :before-upload="handleClassExcel" accept=".xlsx,.xls" style="display:inline-block">
            <el-button type="info">Excel导入</el-button>
          </el-upload>
          <el-button type="danger" :disabled="!cSelected.length" @click="batchDeleteClasses">
            批量删除 ({{ cSelected.length }})
          </el-button>
          <el-button text @click="selectAllClasses">{{ cSelected.length === filteredClasses.length && filteredClasses.length > 0 ? '取消全选' : '全选当前' }}</el-button>
        </div>

        <el-table ref="classTableRef" :data="classes" border size="small" stripe v-loading="cLoading" @selection-change="(v:any)=>cSelected=v">
          <el-table-column type="selection" width="40" />
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="班级名称" />
          <el-table-column label="年级" width="100">
            <template #default="{ row }">{{ gradeMap[row.grade_id] || row.grade_id }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" @click="openClassDialog(row)">编辑</el-button>
              <el-popconfirm title="确认删除?" @confirm="deleteClass(row.id)">
                <template #reference><el-button size="small" type="danger">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <!-- 单个/编辑弹窗 -->
        <el-dialog v-model="classDialog" :title="editingClass ? '编辑班级' : '新增班级'" width="400px">
          <el-form :model="classForm" label-width="80px">
            <el-form-item label="名称"><el-input v-model="classForm.name" /></el-form-item>
            <el-form-item label="年级">
              <el-select v-model="classForm.grade_id">
                <el-option v-for="g in grades" :key="g.id" :label="g.name" :value="g.id" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="classDialog=false">取消</el-button>
            <el-button type="primary" @click="saveClass">保存</el-button>
          </template>
        </el-dialog>

        <!-- 批量输入 -->
        <el-dialog v-model="showBatchDialog" title="批量新增班级" width="500px">
          <el-form label-width="80px">
            <el-form-item label="年级">
              <el-select v-model="batchForm.grade_id">
                <el-option v-for="g in grades" :key="g.id" :label="g.name" :value="g.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="班级名称">
              <el-input v-model="batchForm.names" type="textarea" :rows="8"
                placeholder="每行一个班级名称&#10;如:&#10;高一(1)班&#10;高一(2)班" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showBatchDialog=false">取消</el-button>
            <el-button type="primary" :loading="batchSaving" @click="saveBatchClasses">批量创建</el-button>
          </template>
        </el-dialog>

        <!-- 按数量自动生成 -->
        <el-dialog v-model="showAutoGen" title="按数量自动生成班级" width="400px">
          <el-form :model="autoForm" label-width="80px">
            <el-form-item label="年级">
              <el-select v-model="autoForm.grade_id">
                <el-option v-for="g in grades" :key="g.id" :label="g.name" :value="g.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="班级数量">
              <el-input-number v-model="autoForm.count" :min="1" :max="30" />
            </el-form-item>
            <el-form-item>
              <span style="color:#909399;font-size:12px">
                例: 高三已有3个班, 输入15 → 自动生成高三(4)班~高三(15)班
              </span>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showAutoGen=false">取消</el-button>
            <el-button type="primary" @click="saveAutoGen">生成</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('grades')
const grades = ref<any[]>([]); const classes = ref<any[]>([])
const gLoading = ref(false); const cLoading = ref(false)
const gSelected = ref<any[]>([]); const cSelected = ref<any[]>([])

const stageMap: Record<string, string> = {
  senior: '高中',
  junior: '初中',
  高中: '高中',
  初中: '初中',
}

// ---- 年级 ----
const gradeDialog = ref(false); const editingGrade = ref<any>(null)
const gradeForm = reactive({ name: '', stage: '高中' })

async function loadGrades() {
  gLoading.value = true
  try {
    const r = await api.get('/grades'); grades.value = r.data
    r.data.forEach((g: any) => { gradeMap.value[g.id] = g.name })
  } catch {} finally { gLoading.value = false }
}
function openGradeDialog(row?: any) {
  editingGrade.value = row || null
  gradeForm.name = row?.name || ''; gradeForm.stage = row?.stage || '高中'
  gradeDialog.value = true
}
async function saveGrade() {
  try {
    if (editingGrade.value)
      await api.put(`/grades/${editingGrade.value.id}`, { ...gradeForm })
    else
      await api.post('/grades', { ...gradeForm })
    ElMessage.success('保存成功'); gradeDialog.value = false; loadGrades()
  } catch (e: any) { ElMessage.error(e.message) }
}
async function deleteGrade(id: number) {
  try { await api.delete(`/grades/${id}`); ElMessage.success('已删除'); loadGrades() }
  catch (e: any) { ElMessage.error(e.message) }
}
async function batchDeleteGrades() {
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${gSelected.value.length} 个年级及其所有班级和学生?`, '批量删除', { type: 'warning' })
    const ids = gSelected.value.map((g: any) => g.id)
    await api.delete('/grades/batch-delete', { data: { ids } })
    ElMessage.success('批量删除完成'); gSelected.value = []; loadGrades(); loadClasses()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error(e.message) }
}

// ---- 班级 ----
const classDialog = ref(false); const editingClass = ref<any>(null)
const classForm = reactive({ name: '', grade_id: 1 })
const classGradeFilter = ref<number | null>(null)
const gradeMap = ref<Record<number, string>>({})
const classTableRef = ref<any>(null)
const filteredClasses = ref<any[]>([])

const showBatchDialog = ref(false); const batchSaving = ref(false)
const batchForm = reactive({ grade_id: 1, names: '' })
const showAutoGen = ref(false)
const autoForm = reactive({ grade_id: 1, count: 10 })

async function loadClasses() {
  cLoading.value = true
  try {
    const params: any = {}
    if (classGradeFilter.value) params.grade_id = classGradeFilter.value
    const r = await api.get('/classes', { params })
    classes.value = r.data
    filteredClasses.value = r.data
  } catch {} finally { cLoading.value = false }
}
function selectAllClasses() {
  if (cSelected.value.length === filteredClasses.value.length) {
    classTableRef.value?.clearSelection()
  } else {
    filteredClasses.value.forEach((c: any) => classTableRef.value?.toggleRowSelection(c, true))
  }
}
function openClassDialog(row?: any) {
  editingClass.value = row || null
  classForm.name = row?.name || ''; classForm.grade_id = row?.grade_id || 1
  classDialog.value = true
}
async function saveClass() {
  try {
    if (editingClass.value)
      await api.put(`/classes/${editingClass.value.id}`, { ...classForm })
    else
      await api.post('/classes', { ...classForm })
    ElMessage.success('保存成功'); classDialog.value = false; loadClasses()
  } catch (e: any) { ElMessage.error(e.message) }
}
async function deleteClass(id: number) {
  try { await api.delete(`/classes/${id}`); ElMessage.success('已删除'); loadClasses() }
  catch (e: any) { ElMessage.error(e.message) }
}

async function saveBatchClasses() {
  const names = batchForm.names.split('\n').map(s => s.trim()).filter(Boolean)
  if (!names.length) { ElMessage.warning('请输入至少一个班级名称'); return }
  batchSaving.value = true
  try {
    const r = await api.post('/classes/batch', { grade_id: batchForm.grade_id, names })
    ElMessage.success(r.message); showBatchDialog.value = false
    batchForm.names = ''; loadClasses()
  } catch (e: any) { ElMessage.error(e.message) }
  batchSaving.value = false
}

async function saveAutoGen() {
  try {
    const r = await api.post('/classes/auto-generate', { ...autoForm })
    ElMessage.success(r.message); showAutoGen.value = false; loadClasses()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function handleClassExcel(file: File) {
  const fd = new FormData(); fd.append('file', file)
  try {
    const r = await api.post('/classes/batch-excel', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success(r.message); loadClasses()
  } catch (e: any) { ElMessage.error(e.message) }
  return false
}

async function batchDeleteClasses() {
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${cSelected.value.length} 个班级及其学生?`, '批量删除', { type: 'warning' })
    const ids = cSelected.value.map((c: any) => c.id)
    await api.delete('/classes/batch-delete', { data: { ids } })
    ElMessage.success('批量删除完成'); cSelected.value = []; loadClasses()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error(e.message) }
}

onMounted(async () => { await loadGrades(); loadClasses() })
</script>

