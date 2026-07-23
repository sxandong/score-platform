<template>
  <div>
    <h3>学生管理</h3>
    <el-row :gutter="8" style="margin-bottom:16px">
      <el-col :span="3"><el-select v-model="filterClassId" placeholder="按班级" clearable @change="loadStudents">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
      </el-select></el-col>
      <el-col :span="3"><el-input v-model="keyword" placeholder="搜索" clearable @input="loadStudents" /></el-col>
      <el-col :span="3"><el-button type="primary" @click="openDialog()">新增学生</el-button></el-col>
      <el-col :span="3">
        <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls">
          <el-button type="success">Excel导入</el-button>
        </el-upload>
      </el-col>
      <el-col :span="3"><el-button type="danger" :disabled="!selected.length" @click="batchDelete">
        批量删除 ({{ selected.length }})
      </el-button></el-col>
      <el-col :span="3"><el-button type="warning" @click="showPromote=true">升年级</el-button></el-col>
      <el-col :span="3"><el-button type="info" @click="showReassign=true">重新分班</el-button></el-col>
    </el-row>

    <el-table :data="students" border stripe v-loading="loading" @selection-change="(v:any)=>selected=v">
      <el-table-column type="selection" width="40" />
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="student_no" label="学号" width="120" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="class_name" label="班级" width="120" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.status==='enrolled'?'success':'info'">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="openDialog(row)">编辑</el-button>
          <el-popconfirm title="确认删除?" @confirm="deleteStudent(row.id)">
            <template #reference><el-button size="small" type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination :current-page="page" :total="total" :page-size="50"
      layout="total, prev, pager, next" @current-change="(p:number)=>{page=p;loadStudents()}"
      style="margin-top:16px;justify-content:flex-end" />

    <!-- 单个新增/编辑 -->
    <el-dialog v-model="dialog" :title="editing?'编辑学生':'新增学生'" width="450px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="学号"><el-input v-model="form.student_no" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="班级">
          <el-select v-model="form.class_id"><el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog=false">取消</el-button><el-button type="primary" @click="saveStudent">保存</el-button>
      </template>
    </el-dialog>

    <!-- 升年级 -->
    <el-dialog v-model="showPromote" title="升年级" width="450px">
      <el-form :model="promoteForm" label-width="100px">
        <el-form-item label="原年级">
          <el-select v-model="promoteForm.from_grade_id">
            <el-option v-for="g in grades" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标年级">
          <el-select v-model="promoteForm.target_grade_id">
            <el-option v-for="g in grades" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-alert type="info" :closable="false" show-icon style="margin-bottom:8px"
          title="配对同名班级迁移学生。如目标年级缺少同名班级，该班学生不会被迁移。" />
      </el-form>
      <template #footer>
        <el-button @click="showPromote=false">取消</el-button>
        <el-button type="primary" :loading="promoting" @click="doPromote">执行升级</el-button>
      </template>
    </el-dialog>

    <!-- 重新分班 -->
    <el-dialog v-model="showReassign" title="批量重新分班" width="500px">
      <el-form label-width="80px">
        <el-form-item label="目标班级">
          <el-select v-model="reassignClassId" placeholder="选择目标班级">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-alert type="warning" :closable="false" show-icon style="margin-bottom:8px"
          title="将上方已勾选的学生批量移入目标班级。请先在主列表勾选学生。" />
      </el-form>
      <template #footer>
        <el-button @click="showReassign=false">取消</el-button>
        <el-button type="primary" :loading="reassigning" @click="doReassign">确认 ({{ selected.length }}人)</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const students = ref<any[]>([]); const classes = ref<any[]>([]); const grades = ref<any[]>([])
const loading = ref(false); const page = ref(1); const total = ref(0)
const filterClassId = ref<number | null>(null); const keyword = ref('')
const selected = ref<any[]>([])

const dialog = ref(false); const editing = ref<any>(null)
const form = reactive({ student_no: '', name: '', class_id: 1 })

// ---- 数据加载 ----
async function loadClasses() {
  try { const [cr, gr] = await Promise.all([api.get('/classes'), api.get('/grades')])
    classes.value = cr.data; grades.value = gr.data } catch {}
}
async function loadStudents() {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: 50 }
    if (filterClassId.value) params.class_id = filterClassId.value
    if (keyword.value) params.keyword = keyword.value
    const r = await api.get('/students', { params })
    students.value = r.data; total.value = r.meta.total
  } catch {} finally { loading.value = false }
}

// ---- CRUD ----
function openDialog(row?: any) {
  editing.value = row || null
  form.student_no = row?.student_no || ''; form.name = row?.name || ''
  form.class_id = row?.class_id || 1; dialog.value = true
}
async function saveStudent() {
  try {
    editing.value
      ? await api.put(`/students/${editing.value.id}`, { ...form })
      : await api.post('/students', { ...form })
    ElMessage.success('保存成功'); dialog.value = false; loadStudents()
  } catch (e: any) { ElMessage.error(e.message) }
}
async function deleteStudent(id: number) {
  try { await api.delete(`/students/${id}`); ElMessage.success('已删除'); loadStudents() }
  catch (e: any) { ElMessage.error(e.message) }
}
async function handleImport(file: File) {
  const fd = new FormData(); fd.append('file', file)
  try {
    const r = await api.post('/students/batch', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success(r.message); loadStudents()
  } catch (e: any) { ElMessage.error(e.message) }
  return false
}

// ---- 批量操作 ----
async function batchDelete() {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selected.value.length} 个学生?`, '批量删除', { type: 'warning' })
    await api.delete('/students/batch-delete', { data: { ids: selected.value.map((s:any)=>s.id) } })
    ElMessage.success('批量删除完成'); selected.value = []; loadStudents()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error(e.message) }
}

// ---- 升年级 ----
const showPromote = ref(false); const promoting = ref(false)
const promoteForm = reactive({ from_grade_id: 1, target_grade_id: 2 })
async function doPromote() {
  if (promoteForm.from_grade_id === promoteForm.target_grade_id) {
    ElMessage.warning('原年级与目标年级不能相同'); return
  }
  promoting.value = true
  try {
    const r = await api.post('/students/promote', { ...promoteForm })
    ElMessage.success(r.message); showPromote.value = false; loadStudents()
  } catch (e: any) { ElMessage.error(e.message) }
  promoting.value = false
}

// ---- 重新分班 ----
const showReassign = ref(false); const reassignClassId = ref<number | null>(null); const reassigning = ref(false)
async function doReassign() {
  if (!reassignClassId.value) { ElMessage.warning('请选择目标班级'); return }
  if (!selected.value.length) { ElMessage.warning('请至少勾选一个学生'); return }
  reassigning.value = true
  try {
    const assignments = selected.value.map(s => ({ student_id: s.id, new_class_id: reassignClassId.value }))
    const r = await api.post('/students/reassign', { class_assignments: assignments })
    ElMessage.success(r.message); showReassign.value = false; selected.value = []; loadStudents()
  } catch (e: any) { ElMessage.error(e.message) }
  reassigning.value = false
}

onMounted(() => { loadClasses(); loadStudents() })
</script>
