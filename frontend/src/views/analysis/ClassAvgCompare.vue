<template>
  <div>
    <div class="page-header"><h3>班级均分对比</h3><p>各班级各学科前80%学生平均分对比分析</p></div>

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

    <el-card v-if="resultData" v-loading="loading" class="stats-card">
      <div class="info-bar-sticky">
        <div class="info-bar">
          <div class="info-item">
            <span class="info-label">最近考试</span>
            <span class="info-value">{{ resultData.latest_exam.name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">特控线</span>
            <span class="info-value highlight">≥{{ resultData.special_score }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">对比考试</span>
            <span class="info-value">{{ resultData.other_exams.length }}次</span>
          </div>
          <div class="info-item">
            <span class="info-label">班级数量</span>
            <span class="info-value">{{ resultData.classes.length }}个</span>
          </div>
        </div>
      </div>

      <div class="scroll-wrap">
        <el-table :data="tableRows" border size="small" max-height="600"
          :header-cell-style="{ textAlign: 'center', background: '#1a5490', color: '#fff', fontWeight: 600 }"
          :cell-style="{ textAlign: 'center' }"
          :span-method="spanMethod"
          :row-class-name="rowClassName"
          class="compare-table">
          <el-table-column label="学科" width="90" fixed="left" align="center" prop="_subjectName">
            <template #default="{ row }">
              <span class="subject-name">{{ row._subjectName }}</span>
            </template>
          </el-table-column>
          <el-table-column label="考试/类别" width="160" fixed="left" align="center" prop="_examLabel">
            <template #default="{ row }">
              <span class="subject-name">{{ row._examLabel }}</span>
            </template>
          </el-table-column>
          <el-table-column label="合计" width="90" fixed="left" align="center" prop="_total">
            <template #default="{ row }">
              <span v-if="row._total !== undefined && row._total !== null && row._total !== 0"
                class="cell-total">
                {{ row._total }}
              </span>
            </template>
          </el-table-column>
          <el-table-column v-for="cls in resultData.classes" :key="cls.id"
            :label="cls.name" :prop="'c_' + cls.id" width="80" align="center">
            <template #default="{ row }">
              <span v-if="row['c_' + cls.id] !== undefined && row['c_' + cls.id] !== null && row['c_' + cls.id] !== 0"
                :class="getCellClass(row._rowType)">
                {{ row['c_' + cls.id] }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="footer-info">
        <span>说明：<b>考试人数</b>=参加该学科考试人数；<b>80%平均分</b>=单科排名前80%学生的平均分（去掉后20%）；<b>总分平均分</b>=各班级全体学生总分平均分，合计列为全校总分平均分</span>
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
const loading = ref(false)
const resultData = ref<any>(null)

const filteredExams = computed(() =>
  filterYear.value ? exams.value.filter((e: any) => e.enrollment_year == filterYear.value) : []
)

const tableRows = computed(() => {
  if (!resultData.value) return []
  const d = resultData.value
  const classes = d.classes as any[]
  const classIds = classes.map((c: any) => String(c.id))
  const rows: any[] = []

  // 第一行：特控线
  const specialRow: any = { _rowType: 'special', _subjectIndex: -1, _subjectSpan: 1, _subjectName: '特控线', _examLabel: `${d.latest_exam.name}(≥${d.special_score})` }
  let specialTotal = 0
  classIds.forEach((cid: string) => {
    const v = d.special_counts[cid] ?? 0
    specialRow['c_' + cid] = v || null
    specialTotal += v
  })
  specialRow._total = specialTotal || null
  rows.push(specialRow)

  // 总分平均分行（最近考试）
  const totalAvgRow: any = {
    _rowType: 'total-avg', _subjectIndex: -1, _subjectSpan: 1,
    _subjectName: '总分平均分', _examLabel: d.latest_exam.name
  }
  classIds.forEach((cid: string) => {
    totalAvgRow['c_' + cid] = d.class_total_avgs?.[cid] ?? null
  })
  totalAvgRow._total = d.school_total_avg ?? null
  rows.push(totalAvgRow)

  // 各学科
  d.subjects.forEach((subj: any, sIdx: number) => {
    const sn = subj.subject_name
    const rowCount = 2 + subj.other_exam_avgs.length

    // 最近考试：考试人数
    const tRow: any = {
      _rowType: 'takers', _subjectIndex: sIdx, _subjectSpan: rowCount,
      _subjectName: sn, _examLabel: '考试人数'
    }
    let takersTotal = 0
    classIds.forEach((cid: string) => {
      const v = subj.exam_takers[cid] ?? 0
      tRow['c_' + cid] = v || null
      takersTotal += v
    })
    tRow._total = takersTotal || null
    rows.push(tRow)

    // 最近考试：80%平均分（合计=全校前80%平均分）
    const aRow: any = {
      _rowType: 'avg80', _subjectIndex: sIdx, _subjectSpan: 0,
      _subjectName: '', _examLabel: '80%平均分'
    }
    classIds.forEach((cid: string) => {
      aRow['c_' + cid] = subj.avg_80[cid] ?? null
    })
    aRow._total = subj.avg_80_school ?? null
    rows.push(aRow)

    // 其他考试的80%平均分
    subj.other_exam_avgs.forEach((oe: any) => {
      const oeRow: any = {
        _rowType: 'other-avg', _subjectIndex: sIdx, _subjectSpan: 0,
        _subjectName: '', _examLabel: oe.exam_name
      }
      classIds.forEach((cid: string) => {
        oeRow['c_' + cid] = oe.data[cid] ?? null
      })
      oeRow._total = oe.school_avg ?? null
      rows.push(oeRow)
    })
  })

  return rows
})

function spanMethod({ row, column, rowIndex, columnIndex }: any) {
  if (columnIndex === 0) {
    if (row._subjectSpan > 0) {
      return { rowspan: row._subjectSpan, colspan: 1 }
    }
    return { rowspan: 0, colspan: 0 }
  }
  return { rowspan: 1, colspan: 1 }
}

function getCellClass(rowType: string) {
  if (rowType === 'special') return 'cell-special'
  if (rowType === 'total-avg') return 'cell-total-avg'
  return ''
}

function rowClassName({ row }: any) {
  if (row._rowType === 'special') return 'row-special'
  if (row._rowType === 'total-avg') return 'row-total-avg'
  return `row-subj-${row._subjectIndex % 5}`
}

function onYearChange() {
  selectedExamIds.value = []
  resultData.value = null
}

function onExamChange() {
  resultData.value = null
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
    const r = await api.get('/analysis/class-avg-compare', {
      params: {
        enrollment_year: filterYear.value,
        exam_ids: selectedExamIds.value.join(','),
      },
    })
    resultData.value = r.data
    if (!resultData.value?.classes?.length) {
      ElMessage.info('未查询到符合条件的数据')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '查询失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.stats-card { overflow: hidden; }

.info-bar-sticky {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #fff;
  padding-bottom: 4px;
}

.info-bar {
  display: flex; gap: 0;
  background: linear-gradient(135deg, #e8f0fe 0%, #f0f7ff 100%);
  border-radius: 8px; padding: 14px 20px; margin-bottom: 16px;
  border-left: 4px solid var(--edu-blue);
}
.info-item { display: flex; flex-direction: column; gap: 2px; padding: 0 24px; }
.info-item:first-child { padding-left: 0; }
.info-label { font-size: 12px; color: var(--tx-secondary); }
.info-value { font-size: 16px; font-weight: 600; color: var(--edu-blue); }
.info-value.highlight { color: var(--edu-green); font-size: 18px; }

.scroll-wrap { overflow-x: auto; width: 100%; border-radius: 6px; overflow: hidden; }

.compare-table :deep(.el-table__body td) {
  border-bottom: 1px solid #ebeef5;
  height: 36px;
}

.compare-table :deep(.el-table__body tr:hover > td) {
  background: #f5f7fa !important;
}

.subject-name {
  font-weight: 700;
  color: var(--edu-blue);
  font-size: 12px;
}

/* 特控线行 */
.cell-special {
  display: inline-block; min-width: 32px; padding: 3px 8px; border-radius: 18px;
  background: #ffcc00; color: #fff; font-weight: 600; font-size: 12px;
}

/* 总分平均分行 */
.cell-total-avg {
  font-weight: 700; color: #1a5490; font-size: 12px;
}

/* 合计列 */
.cell-total {
  font-weight: 700; color: #1a7c90; font-size: 12px;
}

.compare-table :deep(.el-table__cell) { background: #fff; }

/* 特控线行 */
.compare-table :deep(.row-special td) {
  background: #fff3cd !important;
}

/* 总分平均分行 */
.compare-table :deep(.row-total-avg td) {
  background: #e8f4f8 !important;
}

/* 各学科交替背景色 */
.compare-table :deep(.row-subj-0 td) {
  background: #f0f7ff !important;
}
.compare-table :deep(.row-subj-1 td) {
  background: #fff8f0 !important;
}
.compare-table :deep(.row-subj-2 td) {
  background: #f0fff4 !important;
}
.compare-table :deep(.row-subj-3 td) {
  background: #f9f0ff !important;
}
.compare-table :deep(.row-subj-4 td) {
  background: #f0feff !important;
}

.compare-table :deep(.el-table__body tr:hover > td) {
  background: #e6f0ff !important;
}

.footer-info {
  margin-top: 12px; padding: 10px 14px;
  background: #f8faff; border-radius: 6px;
  color: var(--tx-secondary); font-size: 12px; line-height: 1.8;
}
.footer-info b { color: var(--edu-blue); }
</style>
