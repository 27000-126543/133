<template>
  <div class="dashboard">
    <el-row :gutter="20" class="stat-cards">
      <el-col :xs="12" :sm="6" v-for="stat in stats" :key="stat.label">
        <div :class="['stat-card', stat.color]">
          <div class="stat-icon">
            <el-icon :size="36"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="charts-row">
      <el-col :lg="16">
        <el-card class="card-shadow">
          <template #header>
            <div class="card-header">
              <span>各部门合规达标率</span>
              <el-button type="primary" size="small" @click="runDailyCheck">
                <el-icon><RefreshRight /></el-icon>执行检查
              </el-button>
            </div>
          </template>
          <v-chart class="chart" :option="departmentChartOption" autoresize />
        </el-card>
      </el-col>
      
      <el-col :lg="8">
        <el-card class="card-shadow">
          <template #header>
            <span>任务状态分布</span>
          </template>
          <v-chart class="chart" :option="taskChartOption" autoresize />
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="lists-row">
      <el-col :lg="12">
        <el-card class="card-shadow">
          <template #header>
            <div class="card-header">
              <span>即将到期证书 (Top 10)</span>
              <el-tag type="warning" effect="dark">90天内</el-tag>
            </div>
          </template>
          <el-table :data="expiringCertificates" size="small" max-height="300">
            <el-table-column prop="employee_name" label="员工" width="100" />
            <el-table-column prop="cert_name" label="证书名称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="expiry_date" label="到期日期" width="120" />
            <el-table-column prop="days_to_expiry" label="剩余天数" width="100">
              <template #default="{ row }">
                <el-tag :type="row.days_to_expiry <= 30 ? 'danger' : 'warning'">
                  {{ row.days_to_expiry }} 天
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :lg="12">
        <el-card class="card-shadow">
          <template #header>
            <div class="card-header">
              <span>已过期证书</span>
              <el-tag type="danger" effect="dark">需处理</el-tag>
            </div>
          </template>
          <el-table :data="expiredCertificates" size="small" max-height="300">
            <el-table-column prop="employee_name" label="员工" width="100" />
            <el-table-column prop="cert_name" label="证书名称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="expiry_date" label="过期日期" width="120" />
            <el-table-column prop="days_expired" label="已过期" width="100">
              <template #default="{ row }">
                <el-tag type="danger">{{ row.days_expired }} 天</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="trend-row">
      <el-col :span="24">
        <el-card class="card-shadow">
          <template #header>
            <span>历史合规趋势 (最近6个月)</span>
          </template>
          <v-chart class="chart trend-chart" :option="trendChartOption" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document, User, Clock, Warning, Check, Close, RefreshRight
} from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent, GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import { getDashboardStats, runDailyCheck as apiRunDailyCheck } from '@/api/common'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

const loading = ref(false)
const dashboardData = ref(null)

const stats = computed(() => {
  if (!dashboardData.value) return []
  
  const certs = dashboardData.value.certificates
  const tasks = dashboardData.value.tasks
  
  return [
    { label: '证书总数', value: certs.total, icon: Document, color: 'blue' },
    { label: '有效证书', value: certs.valid, icon: Check, color: 'green' },
    { label: '即将到期', value: certs.expiring_soon, icon: Clock, color: 'orange' },
    { label: '已过期', value: certs.expired, icon: Warning, color: 'red' },
    { label: '待处理任务', value: tasks.pending + tasks.in_progress, icon: Clock, color: 'purple' },
    { label: '员工总数', value: dashboardData.value.employees.total, icon: User, color: 'blue' },
    { label: '已完成任务', value: tasks.completed, icon: Check, color: 'green' },
    { label: '已过期任务', value: tasks.overdue, icon: Close, color: 'red' },
  ]
})

const expiringCertificates = computed(() => {
  return dashboardData.value?.expiring_certificates || []
})

const expiredCertificates = computed(() => {
  return dashboardData.value?.expired_certificates || []
})

const departmentChartOption = computed(() => {
  const depts = dashboardData.value?.department_compliance || []
  
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: depts.map(d => d.department_name),
      axisLabel: { rotate: 0 }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { formatter: '{value}%' }
    },
    series: [{
      type: 'bar',
      data: depts.map(d => ({
        value: d.compliance_rate,
        itemStyle: {
          color: d.compliance_rate >= 80 ? '#67c23a' : d.compliance_rate >= 60 ? '#e6a23c' : '#f56c6c'
        }
      })),
      barWidth: '40%',
      markLine: {
        data: [{ yAxis: 80, label: { formatter: '80% 达标线' }, lineStyle: { color: '#f56c6c', type: 'dashed' } }]
      },
      label: { show: true, position: 'top', formatter: '{c}%' }
    }]
  }
})

const taskChartOption = computed(() => {
  const tasks = dashboardData.value?.tasks || {}
  
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{c}' },
      emphasis: {
        label: { show: true, fontSize: 16, fontWeight: 'bold' }
      },
      data: [
        { value: tasks.pending || 0, name: '待处理', itemStyle: { color: '#e6a23c' } },
        { value: tasks.in_progress || 0, name: '处理中', itemStyle: { color: '#409eff' } },
        { value: tasks.completed || 0, name: '已完成', itemStyle: { color: '#67c23a' } },
        { value: tasks.overdue || 0, name: '已过期', itemStyle: { color: '#f56c6c' } },
        { value: tasks.escalated || 0, name: '已升级', itemStyle: { color: '#909399' } },
      ]
    }]
  }
})

const trendChartOption = computed(() => {
  const months = ['1月', '2月', '3月', '4月', '5月', '6月']
  const mockData = [75, 78, 82, 79, 85, 88]
  
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['合规达标率', '持证率', '到期率'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      {
        name: '合规达标率',
        type: 'line',
        smooth: true,
        data: mockData,
        itemStyle: { color: '#67c23a' },
        areaStyle: { color: 'rgba(103, 194, 58, 0.3)' }
      },
      {
        name: '持证率',
        type: 'line',
        smooth: true,
        data: [80, 82, 85, 83, 88, 90],
        itemStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64, 158, 255, 0.3)' }
      },
      {
        name: '到期率',
        type: 'line',
        smooth: true,
        data: [15, 12, 10, 18, 8, 5],
        itemStyle: { color: '#f56c6c' },
        areaStyle: { color: 'rgba(245, 108, 108, 0.3)' }
      }
    ]
  }
})

async function fetchDashboardData() {
  try {
    loading.value = true
    dashboardData.value = await getDashboardStats()
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  } finally {
    loading.value = false
  }
}

async function runDailyCheck() {
  try {
    const result = await apiRunDailyCheck()
    ElMessage.success(`每日检查完成，创建了 ${result.details?.tasks_created || 0} 个任务`)
    fetchDashboardData()
  } catch (error) {
    console.error('Daily check failed:', error)
  }
}

onMounted(() => {
  fetchDashboardData()
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stat-cards {
  margin-bottom: 0;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  border-radius: 12px;
  color: white;
  margin-bottom: 20px;
  transition: transform 0.3s, box-shadow 0.3s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  margin-right: 16px;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
  margin-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart {
  height: 320px;
}

.trend-chart {
  height: 360px;
}

.charts-row,
.lists-row,
.trend-row {
  margin-bottom: 0;
}

:deep(.el-col) {
  margin-bottom: 20px;
}
</style>
