<template>
  <div>
    <div class="page-header"><h3>学生排名统计</h3><p>统计学生历次考试总分排名的平均值、最高排名、最低排名</p></div>

    <el-form :inline="true">
      <el-form-item label="入学年份">
        <el-select v-model="filterYear" placeholder="请选择" style="width:140px" @change="onYearChange">
          <el-option v-for="y in yearOptions" :key="y" :label="y + '年'" :value="y" />
        </el-select>
      </el-form-item>
      <el-form-item label="选择考试">
        <el-select v-model="selectedExamIds" multiple placeholder="请先选择入学年份" style="width:500px"
          :disabled="!filterYear" @change="onExamChange">
          <el-option v-for="e in filteredExams" :key="e.id" :label="e.name" :value="e.id" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadData" :loading="loading"
          :disabled="!filterYear || selectedExamIds.length < 2">
          生成统计
        </el-button>
      </el-form-item>
    </el-form>

    <el-alert v-if="filterYear && selectedExamIds.length < 2 && selectedExamIds.length > 0"
      title="请至少选择2次考试" type="warning" :closable="false" style="margin-bottom:12px" />

    <el-card v-if="tableData.length" v-loading="loading" class="stats-card">
      <div class="summary-bar">
        <div class="summary-item">
          <span class="summary-label">参与学生</span>
          <span class="summary-value">{{ tableData.length }}<small>人</small></span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-label">统计考试</span>
          <span class="summary-value">{{ exams.length }}<small>次</small></span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-label">平均排名中位数</span>
          <span class="summary-value">{{ medianRank }}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-label">最佳平均排名</span>
          <span class="summary-value best">{{ tableData[0]?.avg_rank || '-' }}</span>
        </div>
      </div>

      <div class="scroll-wrap">
        <el-table :data="tableData" border stripe size="small"
          :cell-style="{textAlign:'center'}" :header-cell-style="{textAlign:'center'}"
          :row-class-name="rowClassName">
          <el-table-column type="index" label="序号" width="60" fixed>
            <template #default="{row, $index}">
              <span v-if="$index < 3" :class="['medal', `medal-${$index + 1}`]">{{ $index + 1 }}</span>
              <span v-else>{{ $index + 1 }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="student_no" label="学籍号" width="130" fixed />
          <el-table-column prop="name" label="姓名" width="80" fixed />
          <el-table-column prop="class_name" label="班级" width="110" fixed />
          <el-table-column label="历次考试总分排名" :label-class-name="'group-header'">
            <el-table-column v-for="ex in exams" :key="ex.id" :label="ex.name" width="140">
              <template #default="{row}">
                <span v-if="row.ranks[ex.id] !== undefined" :class="['rank-badge', rankClass(row.ranks[ex.id])]">
                  {{ row.ranks[ex.id] }}
                </span>
                <span v-else class="rank-miss">-</span>
              </template>
            </el-table-column>
          </el-table-column>
          <el-table-column prop="avg_rank" label="总分排名平均值" width="130" sortable align="center">
            <template #default="{row}">
              <span class="avg-rank-badge">{{ row.avg_rank }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="best_rank" label="最高排名" width="110" sortable align="center">
            <template #default="{row}">
              <span class="best-rank-badge">{{ row.best_rank }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="worst_rank" label="最低排名" width="110" sortable align="center">
            <template #default="{row}">
              <span class="worst-rank-badge">{{ row.worst_rank }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="footer-info">
        <span>共 {{ tableData.length }} 名学生，已按平均排名升序排列</span>
        <span class="legend">
          <span class="legend-item"><i class="dot dot-top10"></i>前10名</span>
          <span class="legend-item"><i class="dot dot-top30"></i>前30名</span>
          <span class="legend-item"><i class="dot dot-top50"></i>前50名</span>
          <span class="legend-item"><i class="dot dot-top100"></i>前100名</span>
          <span class="legend-item"><i class="dot dot-top200"></i>前200名</span>
          <span class="legend-item"><i class="dot dot-normal"></i>其他</span>
        </span>
      </div>
    </el-card>
    <el-empty v-else-if="!loading" description="请选择入学年份和至少2次考试后生成统计" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const exams = ref<any[]>([])
const selectedExamIds = ref<number[]>([])
const filterYear = ref<number | null>(null)
const yearOptions = Array.from({ length: 7 }, (_, i) => new Date().getFullYear() - 6 + i)
const tableData = ref<any[]>([])
const loading = ref(false)

const filteredExams = computed(() =>
  filterYear.value ? exams.value.filter((e: any) => e.enrollment_year == filterYear.value) : []
)

const medianRank = computed(() => {
  if (!tableData.value.length) return '-'
  const sorted = [...tableData.value].map(s => s.avg_rank).sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid] : ((sorted[mid - 1] + sorted[mid]) / 2).toFixed(1)
})

function onYearChange() {
  selectedExamIds.value = []
  tableData.value = []
}

function onExamChange() {
  tableData.value = []
}

onMounted(async () => {
  try {
    const r = await api.get('/exams')
    exams.value = r.data
  } catch {}
})

async function loadData() {
  if (!filterYear.value || selectedExamIds.value.length < 2) {
    ElMessage.warning('请选择入学年份和至少2次考试')
    return
  }
  loading.value = true
  try {
    const r = await api.get('/analysis/student-rank-stats', {
      params: {
        enrollment_year: filterYear.value,
        exam_ids: selectedExamIds.value.join(','),
      },
    })
    exams.value = r.data?.exams || exams.value
    tableData.value = r.data?.students || []
    if (!tableData.value.length) {
      ElMessage.info('未查询到符合条件的数据')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '查询失败')
  } finally {
    loading.value = false
  }
}

function rankClass(rank: number | undefined): string {
  if (rank === undefined) return ''
  if (rank <= 10) return 'rank-top10'
  if (rank <= 30) return 'rank-top30'
  if (rank <= 50) return 'rank-top50'
  if (rank <= 100) return 'rank-top100'
  if (rank <= 200) return 'rank-top200'
  return 'rank-normal'
}

function rowClassName({ $index }: { $index: number }) {
  if ($index < 3) return 'top-row'
  return ''
}
</script>

<style scoped>
.stats-card { overflow: hidden; }

/* 汇总栏 */
.summary-bar {
  display: flex; align-items: center; gap: 0;
  background: linear-gradient(135deg, #e8f0fe 0%, #f0f7ff 100%);
  border-radius: 8px; padding: 14px 20px; margin-bottom: 16px;
  border-left: 4px solid var(--edu-blue);
}
.summary-item { display: flex; flex-direction: column; gap: 2px; padding: 0 20px; }
.summary-label { font-size: 12px; color: var(--tx-secondary); }
.summary-value { font-size: 22px; font-weight: 700; color: var(--edu-blue); }
.summary-value small { font-size: 12px; font-weight: 400; margin-left: 2px; color: var(--tx-secondary); }
.summary-value.best { color: var(--edu-green); }
.summary-divider { width: 1px; height: 32px; background: var(--border-color); }

/* 表格 */
.scroll-wrap { overflow-x: auto; width: 100%; border-radius: 6px; overflow: hidden; }
:deep(.el-table) { border-radius: 6px; }
:deep(.el-table th.el-table__cell) {
  background: linear-gradient(180deg, #e8f0fe, #d6e4f7) !important;
  color: var(--edu-blue); font-weight: 600; text-align: center;
  border-right: 1px solid #c8d6e8 !important;
}
:deep(.el-table td.el-table__cell) { border-right: 1px solid #ebeef5 !important; }
:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: #f8faff;
}
:deep(.group-header) {
  background: linear-gradient(180deg, #1a5490, #1e3a5f) !important;
  color: #1a5490 !important; font-weight: 700 !important; font-size: 13px !important;
}
:deep(.top-row td) { background: linear-gradient(90deg, #fffbe6, #fffdf5) !important; }

/* 奖牌 */
.medal {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%; font-size: 13px; font-weight: 700; color: #fff;
}
.medal-1 { background: linear-gradient(135deg, #ffd700, #ffb700); box-shadow: 0 2px 6px rgba(255,183,0,.4); }
.medal-2 { background: linear-gradient(135deg, #c0c0c0, #a8a8a8); box-shadow: 0 2px 6px rgba(168,168,168,.4); }
.medal-3 { background: linear-gradient(135deg, #cd7f32, #b8732e); box-shadow: 0 2px 6px rgba(184,115,46,.4); }

/* 排名徽章 */
.rank-badge {
  display: inline-block; min-width: 36px; padding: 2px 8px; border-radius: 12px;
  font-size: 13px; font-weight: 600; color: #fff;
}
.rank-top10 { background: #ffd700; color: #fff; font-weight: 700; }
.rank-top30 { background: #44CEF6; color: #fff; font-weight: 700; }
.rank-top50 { background: #0aa344; color: #fff; font-weight: 700; }
.rank-top100 { background: #3de1ad; color: #fff; font-weight: 700; }
.rank-top200 { background: #8D4BBB; color: #fff; }
.rank-normal { background: #999999; color: #fff; }
.rank-miss { color: #c0c4cc; }

/* 统计列徽章 */
.avg-rank-badge {
  display: inline-block; min-width: 44px; padding: 3px 10px; border-radius: 4px;
  background: var(--edu-blue); color: #fff; font-weight: 700; font-size: 14px;
}
.best-rank-badge {
  display: inline-block; min-width: 36px; padding: 3px 10px; border-radius: 4px;
  background: rgba(46,125,50,.15); color: var(--edu-green); font-weight: 700; font-size: 13px;
}
.worst-rank-badge {
  display: inline-block; min-width: 36px; padding: 3px 10px; border-radius: 4px;
  background: rgba(224,64,64,.1); color: #e04040; font-weight: 600; font-size: 13px;
}

/* 底部信息 */
.footer-info {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 12px; color: var(--tx-secondary); font-size: 12px;
}
.legend { display: flex; gap: 16px; }
.legend-item { display: flex; align-items: center; gap: 4px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot-top10 { background: #ffd700; }
.dot-top30 { background: #44CEF6; }
.dot-top50 { background: #0aa344; }
.dot-top100 { background: #3de1ad; }
.dot-top200 { background: #8D4BBB; }
.dot-normal { background: #999999; }
</style>
