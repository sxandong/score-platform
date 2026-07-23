<template>
  <div>
    <h3>年级与班级管理</h3>
    <el-tabs v-model="activeTab">
      <!-- 年级管理 -->
      <el-tab-pane label="年级" name="grades">
        <el-button type="primary" @click="openGradeDialog()" style="margin-bottom:16px">新增年级</el-button>
        <el-table :data="grades" border stripe v-loading="gLoading">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="年级名称" />
          <el-table-column prop="stage" label="学段" width="100" />
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" @click="openGradeDialog(row)">编辑</el-button>
              <el-popconfirm title="删除年级将同时删除关联班级?" @confirm="deleteGrade(row.id)">
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
                <el-option label="高中" value="senior" /><el-option label="初中" value="junior" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="gradeDialog=false">取消</el-button>
            <el-button type="primary" @click="saveGrade">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- 班级管理 -->
      <el-tab-pane label="班级" name="classes">
        <el-button type="primary" @click="openClassDialog()" style="margin-bottom:16px">新增班级</el-button>
        <el-table :data="classes" border stripe v-loading="cLoading">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="班级名称" />
          <el-table-column prop="grade_id" label="年级ID" width="80" />
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" @click="openClassDialog(row)">编辑</el-button>
              <el-popconfirm title="确认删除?" @confirm="deleteClass(row.id)">
                <template #reference><el-button size="small" type="danger">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
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
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const activeTab = ref('grades')
const grades = ref<any[]>([]); const classes = ref<any[]>([])
const gLoading = ref(false); const cLoading = ref(false)

// ---- 年级 ----
const gradeDialog = ref(false); const editingGrade = ref<any>(null)
const gradeForm = reactive({ name: '', stage: 'senior' })

async function loadGrades() {
  gLoading.value = true
  try { const r = await api.get('/grades'); grades.value = r.data } catch {}
  gLoading.value = false
}
function openGradeDialog(row?: any) {
  editingGrade.value = row || null
  gradeForm.name = row?.name || ''; gradeForm.stage = row?.stage || 'senior'
  gradeDialog.value = true
}
async function saveGrade() {
  try {
    if (editingGrade.value) {
      await api.put(`/grades/${editingGrade.value.id}`, { ...gradeForm })
    } else {
      await api.post('/grades', { ...gradeForm })
    }
    ElMessage.success('保存成功'); gradeDialog.value = false; loadGrades()
  } catch (e: any) { ElMessage.error(e.message) }
}
async function deleteGrade(id: number) {
  try { await api.delete(`/grades/${id}`); ElMessage.success('已删除'); loadGrades() }
  catch (e: any) { ElMessage.error(e.message) }
}

// ---- 班级 ----
const classDialog = ref(false); const editingClass = ref<any>(null)
const classForm = reactive({ name: '', grade_id: 1 })

async function loadClasses() {
  cLoading.value = true
  try { const r = await api.get('/classes'); classes.value = r.data } catch {}
  cLoading.value = false
}
function openClassDialog(row?: any) {
  editingClass.value = row || null
  classForm.name = row?.name || ''; classForm.grade_id = row?.grade_id || 1
  classDialog.value = true
}
async function saveClass() {
  try {
    if (editingClass.value) {
      await api.put(`/classes/${editingClass.value.id}`, { ...classForm })
    } else {
      await api.post('/classes', { ...classForm })
    }
    ElMessage.success('保存成功'); classDialog.value = false; loadClasses()
  } catch (e: any) { ElMessage.error(e.message) }
}
async function deleteClass(id: number) {
  try { await api.delete(`/classes/${id}`); ElMessage.success('已删除'); loadClasses() }
  catch (e: any) { ElMessage.error(e.message) }
}

onMounted(() => { loadGrades(); loadClasses() })
</script>
