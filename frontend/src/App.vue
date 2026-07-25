<template><RouterView /></template>
<script setup lang="ts">import { RouterView } from 'vue-router'</script>
<style>
:root {
  --edu-blue: #1a5490;
  --edu-dark: #1e3a5f;
  --edu-light: #e8f0fe;
  --edu-gold: #f0a500;
  --edu-green: #2e7d32;
  --bg-page: #f5f7fa;
  --tx-primary: #303133;
  --tx-secondary: #909399;
  --border-color: #e4e7ed;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  font-size: 14px; color: var(--tx-primary); background: var(--bg-page); -webkit-font-smoothing: antialiased; }
.el-menu { border-right: none !important; }
.el-card { border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.el-button--primary { --el-button-bg-color: var(--edu-blue); --el-button-border-color: var(--edu-blue); }
.el-table th.el-table__cell { background: #f0f5fa; color: var(--tx-primary); font-weight: 600; }
.el-statistic__head { font-size: 13px; color: var(--tx-secondary); }
.el-statistic__number { font-size: 24px; font-weight: 700; }
.page-header { margin-bottom: 20px; }
.page-header h3 { margin: 0; font-size: 20px; font-weight: 600; color: var(--tx-primary); }
.page-header p { margin: 4px 0 0; font-size: 13px; color: var(--tx-secondary); }
</style>
