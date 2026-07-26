<template>
  <div>
    <div class="page-header"><h3>分数线设置</h3><p>查看和设置各次考试的参考分数线</p></div>

    <el-table :data="allCutoffs" border stripe v-loading="loading">
      <el-table-column prop="name" label="考试" width="280" fixed />
      <el-table-column label="930分数线" width="120">
        <template #default="{row}">
          <el-input-number v-model="row.score_930" :min="0" :max="750" :precision="1"
            size="small" style="width:100px" controls-position="right" placeholder="-" />
        </template>
      </el-table-column>
      <el-table-column label="特控线" width="120">
        <template #default="{row}">
          <el-input-number v-model="row.special" :min="0" :max="750" :precision="1"
            size="small" style="width:100px" controls-position="right" placeholder="-" />
        </template>
      </el-table-column>
      <el-table-column label="一段线" width="120">
        <template #default="{row}">
          <el-input-number v-model="row.first" :min="0" :max="750" :precision="1"
            size="small" style="width:100px" controls-position="right" placeholder="-" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{row}">
          <el-button size="small" type="primary" @click="saveOne(row)" :loading="row._saving">保存</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const loading = ref(false); const allCutoffs = ref<any[]>([])

onMounted(async () => { await loadAll() })

async function loadAll() {
  loading.value = true
  try {
    const r = await api.get('/exams/all-cutoffs')
    allCutoffs.value = (r.data || []).map((e: any) => ({
      id: e.id, name: e.name,
      score_930: e.score_930 ?? undefined,
      special: e.special ?? undefined,
      first: e.first ?? undefined,
    }))
  } catch {} finally { loading.value = false }
}

async function saveOne(row: any) {
  row._saving = true
  try {
    const cutoffs: Record<string, number> = {}
    if (row.score_930 != null) cutoffs.score_930 = row.score_930
    if (row.special != null) cutoffs.special = row.special
    if (row.first != null) cutoffs.first = row.first
    await api.post(`/exams/${row.id}/cutoffs`, { cutoffs })
    ElMessage.success(`${row.name} 分数线已保存`)
  } catch (e: any) { ElMessage.error(e.message) }
  row._saving = false
}
</script>
