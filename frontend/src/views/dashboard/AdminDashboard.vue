<template>
  <div>
    <h3>系统仪表盘</h3>
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="6"><el-card><el-statistic title="用户总数" :value="stats.users" /></el-card></el-col>
      <el-col :span="6"><el-card><el-statistic title="考试数" :value="stats.exams" /></el-card></el-col>
      <el-col :span="6"><el-card><el-statistic title="成绩记录" :value="stats.scores" /></el-card></el-col>
      <el-col :span="6"><el-card><el-statistic title="班级数" :value="stats.classes" /></el-card></el-col>
    </el-row>
    <el-card style="margin-top:16px">
      <template #header>快捷操作</template>
      <el-row :gutter="16">
        <el-col :span="6"><el-button type="primary" @click="$router.push('/exams')" style="width:100%">考试管理</el-button></el-col>
        <el-col :span="6"><el-button type="success" @click="$router.push('/scores/entry')" style="width:100%">录入成绩</el-button></el-col>
        <el-col :span="6"><el-button type="warning" @click="$router.push('/analysis/class-compare')" style="width:100%">班级对比</el-button></el-col>
        <el-col :span="6"><el-button type="info" @click="$router.push('/reports')" style="width:100%">导出报表</el-button></el-col>
      </el-row>
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { reactive, onMounted } from 'vue'
import api from '@/api'
const stats = reactive({ users: 0, exams: 0, scores: 0, classes: 0 })
onMounted(async () => { try { const r = await api.get('/users'); stats.users = r.meta?.total || 0 } catch {} })
</script>
