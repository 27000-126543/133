<template>
  <div class="page-container">
    <el-card class="card-shadow">
      <template #header>
        <div class="card-header">
          <span>培训管理</span>
          <el-button type="primary" @click="generatePlans" :loading="generating">
            <el-icon><MagicStick /></el-icon>自动生成培训计划
          </el-button>
        </div>
      </template>

      <el-row :gutter="16" class="quick-stats">
        <el-col :span="6" v-for="stat in quickStats" :key="stat.label">
          <div :class="['stat-card', stat.color]">
            <el-icon :size="28"><component :is="stat.icon" /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <el-tabs v-model="activeTab" style="margin-top: 20px;">
        <el-tab-pane label="培训计划" name="plans">
          <el-form :inline="true" class="filter-form">
            <el-form-item label="状态">
              <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 150px;">
                <el-option label="待开始" value="pending" />
                <el-option label="进行中" value="in_progress" />
                <el-option label="已完成" value="completed" />
                <el-option label="已取消" value="cancelled" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="fetchPlans">
                <el-icon><Search /></el-icon>查询
              </el-button>
            </el-form-item>
          </el-form>

          <el-table :data="plans" v-loading="loading" border stripe>
            <el-table-column prop="plan_code" label="计划编号" width="140" />
            <el-table-column prop="name" label="计划名称" min-width="200" />
            <el-table-column prop="department_name" label="责任部门" width="130" />
            <el-table-column label="培训周期" width="220">
              <template #default="{ row }">
                {{ row.start_date }} ~ {{ row.end_date }}
              </template>
            </el-table-column>
            <el-table-column prop="course_count" label="课程数" width="80" align="center" />
            <el-table-column prop="target_count" label="培训人数" width="100" align="center" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="viewPlan(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="课程库" name="courses">
          <el-table :data="courses" v-loading="loadingCourses" border stripe>
            <el-table-column prop="course_code" label="课程编号" width="130" />
            <el-table-column prop="name" label="课程名称" min-width="200" />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column prop="cert_type_name" label="对应证书" width="150" />
            <el-table-column prop="duration_hours" label="时长(小时)" width="100" align="center" />
            <el-table-column prop="provider" label="提供方" width="150" />
            <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="detailVisible" title="培训计划详情" width="700px">
      <el-descriptions :column="2" border v-if="currentPlan">
        <el-descriptions-item label="计划编号">{{ currentPlan.plan_code }}</el-descriptions-item>
        <el-descriptions-item label="责任部门">{{ currentPlan.department_name }}</el-descriptions-item>
        <el-descriptions-item label="计划名称" :span="2">{{ currentPlan.name }}</el-descriptions-item>
        <el-descriptions-item label="开始日期">{{ currentPlan.start_date }}</el-descriptions-item>
        <el-descriptions-item label="结束日期">{{ currentPlan.end_date }}</el-descriptions-item>
        <el-descriptions-item label="课程数量">{{ currentPlan.course_count }}</el-descriptions-item>
        <el-descriptions-item label="培训人数">{{ currentPlan.target_count }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(currentPlan.status)">{{ statusText(currentPlan.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ currentPlan.created_at }}</el-descriptions-item>
        <el-descriptions-item label="培训原因" :span="2">{{ currentPlan.reason }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick, Search, Reading, Document, User, Warning } from '@element-plus/icons-vue'
import {
  getTrainingPlans, getTrainingCourses, generateTrainingPlans as apiGeneratePlans
} from '@/api/common'

const loading = ref(false)
const loadingCourses = ref(false)
const generating = ref(false)
const activeTab = ref('plans')
const filterStatus = ref('')
const plans = ref([])
const courses = ref([])
const detailVisible = ref(false)
const currentPlan = ref(null)

const quickStats = computed(() => [
  { label: '总计划数', value: plans.value.length, icon: Document, color: 'blue' },
  { label: '进行中', value: plans.value.filter(p => p.status === 'in_progress').length, icon: Reading, color: 'green' },
  { label: '待开始', value: plans.value.filter(p => p.status === 'pending').length, icon: User, color: 'orange' },
  { label: '低合规部门', value: plans.value.filter(p => p.status === 'pending').length, icon: Warning, color: 'red' },
])

function statusType(status) {
  const types = {
    pending: 'warning',
    in_progress: 'primary',
    completed: 'success',
    cancelled: 'info'
  }
  return types[status] || 'info'
}

function statusText(status) {
  const texts = {
    pending: '待开始',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消'
  }
  return texts[status] || status
}

async function fetchPlans() {
  try {
    loading.value = true
    const params = filterStatus.value ? { status: filterStatus.value } : {}
    const result = await getTrainingPlans(params)
    plans.value = result.items || []
  } catch (error) {
    console.error('Failed to fetch plans:', error)
  } finally {
    loading.value = false
  }
}

async function fetchCourses() {
  try {
    loadingCourses.value = true
    const result = await getTrainingCourses()
    courses.value = result || []
  } catch (error) {
    console.error('Failed to fetch courses:', error)
  } finally {
    loadingCourses.value = false
  }
}

async function generatePlans() {
  try {
    generating.value = true
    const result = await apiGeneratePlans()
    ElMessage.success(result.message || '培训计划生成成功')
    fetchPlans()
  } catch (error) {
    console.error('Generate plans failed:', error)
  } finally {
    generating.value = false
  }
}

function viewPlan(plan) {
  currentPlan.value = plan
  detailVisible.value = true
}

onMounted(() => {
  fetchPlans()
  fetchCourses()
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
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  color: white;
}

.stat-card.blue { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.stat-card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
.stat-card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.stat-card.red { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }

.stat-value {
  font-size: 22px;
  font-weight: bold;
}

.stat-label {
  font-size: 13px;
  opacity: 0.9;
}

.filter-form {
  margin-bottom: 16px;
}
</style>
