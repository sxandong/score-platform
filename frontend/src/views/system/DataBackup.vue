<template>
  <div>
    <div class="page-header"><h3>数据备份与恢复</h3><p>保护系统数据安全</p></div>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><span style="font-weight:600">下载备份</span></template>
          <p style="color:var(--tx-secondary);margin-bottom:16px;font-size:13px">
            将当前数据库下载到本地。建议定期备份（如每周一次）。
          </p>
          <el-button type="primary" @click="downloadBackup" :loading="downloading">
            下载数据库备份
          </el-button>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header><span style="font-weight:600">恢复数据</span></template>
          <el-alert type="warning" :closable="false" show-icon style="margin-bottom:12px"
            title="恢复将覆盖当前数据库！请确保已下载备份文件。恢复后需重启应用。" />
          <el-upload :show-file-list="false" :http-request="handleRestore" accept=".db" :disabled="restoring">
            <el-button type="danger" :loading="restoring">上传备份文件并恢复</el-button>
          </el-upload>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const downloading = ref(false); const restoring = ref(false)

function downloadBackup() {
  downloading.value = true
  window.open('/api/system/backup')
  ElMessage.success('备份下载中...')
  setTimeout(() => { downloading.value = false }, 1000)
}

async function handleRestore(options: any) {
  try {
    await ElMessageBox.confirm(
      '恢复操作将覆盖当前所有数据！此操作不可撤销，确定继续？',
      '确认恢复', { type: 'error', confirmButtonText: '确定恢复', cancelButtonText: '取消' }
    )
    restoring.value = true
    const fd = new FormData(); fd.append('file', options.file)
    const r = await api.post('/system/restore', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success(r.message || '恢复完成，请重启应用')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '恢复失败')
  }
  restoring.value = false
}
</script>
