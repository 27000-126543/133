<template>
  <div class="page-container">
    <el-card class="card-shadow">
      <template #header>
        <div class="card-header">
          <span>报告中心</span>
          <el-button type="primary" @click="generateReport" :loading="generating">
            <el-icon><Plus /></el-icon>生成月度报告
          </el-button>
        </div>
      </template>
      
      <el-row :gutter="16" class="quick-stats">
        <el-col :span="8" v-for="stat in quickStats" :key="stat.label">
          <div :class="['stat-card', stat.color]">
            <el-icon :size="32"><component :is="stat.icon" /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
      
      <el-tabs v-model="activeTab" style="margin-top: 20px;">
        <el-tab-pane label="月度报告" name="monthly">
          <el-table :data="reports" v-loading="loading" border stripe>
            <el-table-column prop="report_month" label="报告月份" width="120" />
            <el-table-column prop="department_name" label="部门" width="150" />
            <el-table-column prop="total_employees" label="员工总数" width="100" align="center" />
            <el-table-column prop="certified_employees" label="持证人数" width="100" align="center" />
            <el-table-column label="合规达标率" width="140">
              <template #default="{ row }">
                <el-tag :type="row.compliance_rate >= 80 ? 'success' : 'danger'">
                  {{ row.compliance_rate.toFixed(2) }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="持证率" width="120">
              <template #default="{ row }">
                {{ row.certification_rate.toFixed(2) }}%
              </template>
            </el-table-column>
            <el-table-column label="到期率" width="120">
              <template #default="{ row }">
                <el-tag :type="row.expiry_rate > 10 ? 'warning' : 'info'">
                  {{ row.expiry_rate.toFixed(2) }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="expiring_soon" label="即将到期" width="100" align="center" />
            <el-table-column prop="expired" label="已过期" width="100" align="center" />
            <el-table-column prop="pending_tasks" label="待处理任务" width="110" align="center" />
            <el-table-column prop="created_at" label="生成时间" width="180" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.pdf_path"
                  type="primary"
                  size="small"
                  link
                  @click="downloadReport('pdf', row.pdf_path)"
                >
                  下载PDF
                </el-button>
                <el-button
                  v-if="row.excel_path"
                  type="success"
                  size="small"
                  link
                  @click="downloadReport('excel', row.excel_path)"
                >
                  下载Excel
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="培训需求" name="training">
          <el-alert
            v-if="trainingNeeds.length > 0"
            :title="`检测到 ${trainingNeeds.length} 个部门需要专项培训`"
            type="warning"
            :closable="false"
            show-icon
            style="margin-bottom: 16px;"
          />
          
          <el-empty v-if="trainingNeeds.length === 0" description="暂无培训需求" />
          
          <el-row :gutter="16" v-else>
            <el-col :span="12" v-for="need in trainingNeeds" :key="need.department_id">
              <el-card class="training-need-card">
                <template #header>
                  <div class="card-header">
                    <span>{{ need.department_name }}</span>
                    <el-tag type="danger" effect="dark">
                      连续{{ need.consecutive_months }}个月不达标
                    </el-tag>
                  </div>
                </template>
                <p>当前合规率: <strong>{{ (need.current_rate * 100).toFixed(2) }}%</strong></p>
                <div class="history">
                  <div v-for="(item, index) in need.compliance_history" :key="index" class="history-item">
                    <span>{{ item.month }}</span>
                    <el-progress
                      :percentage="(item.rate * 100).toFixed(0)"
                      color="#f56c6c"
                      :stroke-width="6"
                    />
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
          
          <div style="margin-top: 20px;" v-if="trainingNeeds.length > 0">
            <el-button type="primary" @click="generateTrainingPlans">
              <el-icon><MagicStick /></el-icon>自动生成培训计划
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <el-dialog v-model="reportPreviewVisible" title="报告预览" width="90%">
      <div class="report-preview">
        <iframe
          v-if="currentReportUrl"
          :src="currentReportUrl"
          style="width: 100%; height: 600px; border: none;"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Document, User, Warning, MagicStick } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  getMonthlyReports, generateMonthlyReport,
  getTrainingNeeds, generateTrainingPlans as apiGeneratePlans
} from '@/api/common'
import download from 'downloadjs'

const userStore = useUserStore()

const loading = ref(false)
const generating = ref(false)
const activeTab = ref('monthly')
const reports = ref([])
const trainingNeeds = ref([])

const quickStats = computed(() => [
  { label: '总报告数', value: reports.value.length, icon: Document, color: 'blue' },
  { label: '平均合规率', value: avgCompliance, icon: User, color: 'green' },
  { label: '需培训部门', value: trainingNeeds.value.length, icon: Warning, color: 'red' },
])

const avgCompliance = computed(() => {
  if (reports.value.length === 0) return '0%'
  const avg = reports.value.reduce((sum, r) => sum + r.compliance_rate, 0) / reports.value.length
  return avg.toFixed(1) + '%'
})

const reportPreviewVisible = ref(false)
const currentReportUrl = ref('')

async function fetchReports() {
  try {
    loading.value = true
    const result = await getMonthlyReports()
    reports.value = result.items || []
  } catch (error) {
    console.error('Failed to fetch reports:', error)
  } finally {
    loading.value = false
  }
}

async function fetchTrainingNeeds() {
  try {
    const result = await getTrainingNeeds()
    trainingNeeds.value = result.needs || []
  } catch (error) {
    console.error('Failed to fetch training needs:', error)
  }
}

async function generateReport() {
  try {
    generating.value = true
    const result = await generateMonthlyReport()
    ElMessage.success('报告生成成功')
    fetchReports()
  } catch (error) {
    console.error('Generate report failed:', error)
  } finally {
    generating.value = false
  }
}

function downloadReport(type, filePath) {
  const fileName = filePath.split('/').pop()
  const url = `/api/reports/download/${type}/${fileName}`
  
  window.open(url, '_blank')
}

async function generateTrainingPlans() {
  try {
    const result = await apiGeneratePlans()
    ElMessage.success(result.message || `已生成 ${result.plans?.length || 0} 个培训计划`)
  } catch (error) {
    console.error('Generate training plans failed:', error)
  }
}

onMounted(() => {
  fetchReports()
  fetchTrainingNeeds()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-stats {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 12px;
  color: white;
}

.stat-card.blue { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.stat-card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
.stat-card.red { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }

.stat-value {
  font-size: 24px;
  font-weight: bold;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
}

.training-need-card {
  margin-bottom: 16px;
}

.history {
  margin-top: 12px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.history-item span {
  width: 70px;
  font-size: 12px;
  color: #909399;
}

.report-preview {
  width: 100%;
  min-height: 600px;
}
</style>
