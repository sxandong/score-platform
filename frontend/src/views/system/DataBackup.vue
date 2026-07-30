<template>
  <div>
    <div class="page-header"><h3>数据备份与恢复</h3><p>保护系统数据安全</p></div>

    <el-row :gutter="20" class="cards-row">
      <!-- 下载备份 -->
      <el-col :span="8" class="cards-col">
        <el-card class="feature-card" shadow="hover" v-show="true">
          <div class="card-icon-wrapper" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <el-icon :size="32" color="#fff"><Download /></el-icon>
          </div>
          <div class="card-content">
            <h4 class="card-title">下载备份</h4>
            <p class="card-desc">
              将当前数据库下载到本地。建议定期备份（如每周一次），防止数据丢失。
            </p>
            <div class="card-footer">
              <el-button type="primary" @click="downloadBackup" :loading="downloading" size="large">
                <el-icon><Download /></el-icon>
                <span style="margin-left:6px">下载数据库备份</span>
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 恢复数据 -->
      <el-col :span="8" class="cards-col">
        <el-card class="feature-card" shadow="hover">
          <div class="card-icon-wrapper" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <el-icon :size="32" color="#fff"><Refresh /></el-icon>
          </div>
          <div class="card-content">
            <h4 class="card-title">恢复数据</h4>
            <p class="card-desc">
              从备份文件恢复数据库。此操作将覆盖当前数据，且不可撤销，请谨慎操作。
            </p>
            <div class="restore-area">
              <el-input 
                :model-value="selectedFile?.name || ''" 
                placeholder="请选择备份文件" 
                readonly
                size="default"
              >
                <template #append>
                  <el-button :disabled="restoring" @click="fileInputRef?.click()">
                    <el-icon><FolderOpened /></el-icon>
                  </el-button>
                </template>
              </el-input>
              <input ref="fileInputRef" type="file" accept=".db" style="display:none" @change="onFileChange" />
            </div>
            <div class="card-footer">
              <el-button 
                type="danger" 
                :loading="restoring" 
                :disabled="!selectedFile" 
                @click="startRestore"
                size="large"
              >
                <el-icon><Refresh /></el-icon>
                <span style="margin-left:6px">上传并恢复</span>
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 系统初始化 -->
      <el-col :span="8" class="cards-col">
        <el-card class="feature-card" shadow="hover">
          <div class="card-icon-wrapper" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <el-icon :size="32" color="#fff"><Warning /></el-icon>
          </div>
          <div class="card-content">
            <h4 class="card-title">系统初始化</h4>
            <p class="card-desc">
              清空所有业务数据（考试、成绩、学生、班级等），保留管理员账号、角色权限等系统配置。
            </p>
            <div class="card-footer">
              <el-button type="warning" :loading="initializing" @click="startInit" size="large">
                <el-icon><Warning /></el-icon>
                <span style="margin-left:6px">系统初始化</span>
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 提示信息 -->
    <el-card class="tips-card" shadow="never">
      <el-row :gutter="30">
        <el-col :span="8">
          <div class="tip-item">
            <el-icon :size="20" color="#409EFF"><InfoFilled /></el-icon>
            <span>备份是数据安全的第一道防线</span>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="tip-item">
            <el-icon :size="20" color="#E6A23C"><Warning /></el-icon>
            <span>恢复操作会覆盖当前数据</span>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="tip-item">
            <el-icon :size="20" color="#F56C6C"><CircleClose /></el-icon>
            <span>初始化前系统会自动创建备份</span>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Download, Refresh, Warning, FolderOpened, InfoFilled, CircleClose } from '@element-plus/icons-vue'
import api, { axiosInstance } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const downloading = ref(false); const restoring = ref(false); const initializing = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
  }
}

async function downloadBackup() {
  downloading.value = true
  try {
    const res = await axiosInstance.get('/system/backup', { responseType: 'blob' })
    let filename = 'backup.db'
    const disposition = res.headers?.['content-disposition'] || ''
    const match = disposition.match(/filename=(.+)$/)
    if (match) filename = match[1].replace(/["']/g, '')

    const blob = res.data instanceof Blob ? res.data : new Blob([res.data], { type: 'application/octet-stream' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('备份下载完成')
  } catch (e: any) {
    ElMessage.error(e.message || '下载失败')
  } finally {
    downloading.value = false
  }
}

async function startRestore() {
  if (!selectedFile.value) return
  try {
    await ElMessageBox.confirm(
      '恢复操作将覆盖当前所有数据！此操作不可撤销，确定继续？',
      '确认恢复', { type: 'error', confirmButtonText: '确定恢复', cancelButtonText: '取消' }
    )
    restoring.value = true
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    const r = await api.post('/system/restore', fd)
    ElMessage.success(r.message || '恢复完成')
    selectedFile.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '恢复失败')
  } finally {
    restoring.value = false
  }
}

async function startInit() {
  try {
    await ElMessageBox.confirm(
      '此操作将清空所有业务数据（考试、成绩、学生、班级等）！\n\n系统会自动创建当前数据的备份。\n\n确定要执行系统初始化吗？',
      '确认系统初始化', 
      { 
        type: 'error', 
        confirmButtonText: '确定初始化', 
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--warning'
      }
    )
    
    const { value } = await ElMessageBox.prompt(
      '请输入 "确认初始化" 以继续执行此操作',
      '最终确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        inputPattern: /^确认初始化$/,
        inputErrorMessage: '输入内容不正确'
      }
    )
    
    if (value !== '确认初始化') {
      return
    }
    
    initializing.value = true
    const r = await api.post('/system/init')
    ElMessage.success(r.message || '系统初始化完成')
  } catch (e: any) {
    if (e !== 'cancel' && e !== 'confirm') {
      ElMessage.error(e.message || '系统初始化失败')
    }
  } finally {
    initializing.value = false
  }
}
</script>

<style scoped>
.cards-row {
  display: flex;
  align-items: stretch;
}

.cards-col {
  display: flex;
}

.feature-card {
  flex: 1;
  border-radius: 12px;
  border: none;
  transition: all 0.3s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.feature-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.feature-card :deep(.el-card__body) {
  padding: 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
}

.card-content {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 8px 0;
  flex-shrink: 0;
}

.card-desc {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin: 0 0 20px 0;
  flex: 1;
}

.card-footer {
  margin-top: auto;
  flex-shrink: 0;
}

.card-footer .el-button {
  width: 100%;
}

.restore-area {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.tips-card {
  margin-top: 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
}

.tips-card :deep(.el-card__body) {
  padding: 20px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
</style>
