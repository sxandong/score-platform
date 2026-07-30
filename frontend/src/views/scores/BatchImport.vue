<template>
  <div>
    <h3>批量导入成绩</h3>
    <el-form :inline="true" style="margin-bottom:16px">
      <el-form-item label="考试"><el-select v-model="examId" placeholder="选择考试" style="width:300px">
        <el-option v-for="e in exams" :key="e.id" :label="e.name" :value="e.id" /></el-select>
      </el-form-item>
    </el-form>
    <el-alert v-if="examId && existingCount > 0" type="warning" :closable="false" show-icon style="margin-bottom:12px">
      <template #title>
        该考试已有 {{ existingCount }} 条成绩，重新导入将更新原有数据。
      </template>
    </el-alert>

    <el-upload drag :show-file-list="false" :http-request="doImport" accept=".xlsx,.xls" :disabled="!examId">
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div>点击或拖拽上传Excel文件</div>
      <template #tip><div style="font-size:12px;color:#909399;margin-top:8px">
        列名: 学籍号, 姓名, 班级, 语文, 数学, 外语, 政治, 历史, 地理, 物理, 化学, 生物, 技术
      </div></template>
    </el-upload>

    <!-- 导入结果显示 -->
    <el-card v-if="importResult" style="margin-top:16px" :class="importCardClass">
      <template #header>
        <div class="result-header">
          <el-icon :size="24" :color="resultIconColor">
            <CircleCheckFilled v-if="!hasError" />
            <WarningFilled v-else />
          </el-icon>
          <span :style="{color: resultIconColor, fontWeight: 'bold', fontSize: '16px', marginLeft: '8px'}">
            {{ resultTitle }}
          </span>
        </div>
      </template>
      
      <div class="result-stats">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="处理行数">{{ importResult.total_rows || 0 }}</el-descriptions-item>
          <el-descriptions-item label="新增学生">
            <span style="color:#67C23A">{{ importResult.created_students || 0 }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="新增成绩">
            <span style="color:#409EFF">{{ importResult.created_scores || 0 }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="覆盖更新">
            <span style="color:#E6A23C">{{ importResult.updated_scores || 0 }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="跳过(分数相同)">
            <span style="color:#909399">{{ importResult.skipped_same || 0 }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">
            {{ importResult.elapsed_seconds || 0 }} 秒
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div v-if="hasError" style="margin-top:16px">
        <el-divider content-position="left">
          <span style="color:#F56C6C;font-weight:bold">导入错误详情（{{ importResult.errors.length }} 条）</span>
        </el-divider>
        <div style="max-height:300px;overflow-y:auto">
          <el-table :data="importResult.errors" border size="small" max-height="300">
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="row" label="Excel行号" width="100" align="center" />
            <el-table-column prop="reason" label="错误原因" />
          </el-table>
        </div>
      </div>

      <div v-else style="margin-top:12px;text-align:center">
        <el-tag type="success" size="large">
          ✅ 所有数据导入成功！
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'

const exams = ref<any[]>([])
const examId = ref<number | null>(null)
const existingCount = ref(0)
const importResult = ref<any>(null)

// 计算属性
const hasError = computed(() => {
  return importResult.value?.errors && importResult.value.errors.length > 0
})

const resultIconColor = computed(() => {
  return hasError.value ? '#E6A23C' : '#67C23A'
})

const importCardClass = computed(() => {
  return hasError.value ? 'result-card warning' : 'result-card success'
})

const resultTitle = computed(() => {
  if (!importResult.value) return ''
  if (hasError.value) return '⚠️ 导入部分完成，存在错误'
  const r = importResult.value
  if (r.created_scores > 0 && r.updated_scores > 0) return '🎉 成绩导入成功（新增+覆盖）'
  if (r.created_scores > 0) return '🎉 成绩新增导入成功'
  if (r.updated_scores > 0) return '🎉 成绩覆盖更新成功'
  if (r.skipped_same > 0) return '✓ 成绩校验完成'
  return '导入处理完成'
})

onMounted(async () => {
  try { 
    const r = await api.get('/exams')
    exams.value = r.data || []
  } catch (e) {
    console.error('加载考试列表失败:', e)
  }
})

watch(examId, async (val) => {
  importResult.value = null
  if (!val) { 
    existingCount.value = 0
    return 
  }
  try {
    const r = await api.get(`/exams/${val}/stats`)
    existingCount.value = r.data?.scores || 0
  } catch { 
    existingCount.value = 0 
  }
})

async function doImport(options: any) {
  if (!examId.value) { 
    ElMessage.warning('请先选择考试')
    return 
  }

  // 已有成绩时确认
  if (existingCount.value > 0) {
    try {
      await ElMessageBox.confirm(
        `该考试已有 ${existingCount.value} 条成绩，重新导入将覆盖更新原有数据。确定导入？`,
        '确认导入', 
        { 
          type: 'warning', 
          confirmButtonText: '确定导入', 
          cancelButtonText: '取消' 
        }
      )
    } catch { 
      return 
    }
  }

  const fd = new FormData()
  fd.append('file', options.file)
  fd.append('exam_id', String(examId.value))
  
  const loading = ElLoading.service({
    lock: true,
    text: '成绩导入中，大数据量可能需要数十秒，请耐心等待...',
    background: 'rgba(0, 0, 0, 0.7)',
  })
  
  try {
    const r = await api.post('/scores/batch', fd, { 
      headers: { 'Content-Type': 'multipart/form-data' } 
    })
    
    console.log('API响应:', r)
    
    // 保存导入结果
    importResult.value = {
      ...r.data,
      message: r.message
    }
    
    console.log('importResult:', importResult.value)
    
    ElMessage.success(r.message || '导入完成')
    existingCount.value = (r.data?.created_scores || 0) + (r.data?.updated_scores || 0)
  } catch (e: any) {
    console.error('导入失败:', e)
    if (e?.message?.includes('timeout')) {
      ElMessage.error('导入超时：文件过大或系统繁忙，请拆分数据或稍后重试')
    } else {
      ElMessage.error(e?.message || '导入失败')
    }
  } finally {
    loading.close()
  }
}
</script>

<style scoped>
.result-header {
  display: flex;
  align-items: center;
}

.result-stats {
  margin-bottom: 12px;
}

:deep(.result-card.success) {
  border-color: #67C23A;
}

:deep(.result-card.warning) {
  border-color: #E6A23C;
}

:deep(.result-card.success .el-card__header) {
  background-color: #f0f9eb;
}

:deep(.result-card.warning .el-card__header) {
  background-color: #fdf6ec;
}
</style>
