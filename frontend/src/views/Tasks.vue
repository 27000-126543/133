<template>
  <div class="page-container">
    <el-card class="card-shadow">
      <template #header>
        <div class="card-header">
          <span>任务管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="runDailyCheck" v-if="userStore.isAdmin">
              <el-icon><RefreshRight /></el-icon>执行每日检查
            </el-button>
          </div>
        </div>
      </template>
      
      <el-row :gutter="16" class="task-stats">
        <el-col :span="4" v-for="stat in taskStats" :key="stat.label">
          <el-statistic :title="stat.label" :value="stat.value" :value-style="{ color: stat.color }">
            <template #suffix>
              <el-icon :size="16" :color="stat.color"><component :is="stat.icon" /></el-icon>
            </template>
          </el-statistic>
        </el-col>
      </el-row>
      
      <el-tabs v-model="activeTab" class="task-tabs">
        <el-tab-pane label="待处理" name="pending">
          <el-table :data="filteredTasks.pending" v-loading="loading" border stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="task_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="taskTypeColor(row.task_type)">{{ taskTypeText(row.task_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="任务标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="employee_name" label="所属员工" width="100" />
            <el-table-column prop="assignee_name" label="负责人" width="100" />
            <el-table-column prop="priority" label="优先级" width="100">
              <template #default="{ row }">
                <el-tag :type="priorityColor(row.priority)" effect="dark">{{ priorityText(row.priority) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="deadline" label="截止日期" width="120">
              <template #default="{ row }">
                <span :class="{ 'text-danger': isOverdue(row) }">{{ row.deadline }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="escalation_level" label="升级级别" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.escalation_level > 0" type="danger" effect="dark">
                  已升级至主管
                </el-tag>
                <span v-else>正常</span>
              </template>
            </el-table-column>
            <el-table-column prop="reminder_count" label="催办次数" width="90" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.days_overdue && row.days_overdue > 0" type="danger">
                  超期{{ row.days_overdue }}天
                </el-tag>
                <el-tag v-else type="warning">处理中</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="viewTask(row)">查看</el-button>
                <el-button type="success" size="small" @click="handleComplete(row)">处理</el-button>
                <el-button
                  v-if="userStore.isManager"
                  type="warning"
                  size="small"
                  @click="handleApprove(row)"
                >
                  审批
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="已完成" name="completed">
          <el-table :data="filteredTasks.completed" v-loading="loading" border stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="task_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="taskTypeColor(row.task_type)">{{ taskTypeText(row.task_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="任务标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="employee_name" label="所属员工" width="100" />
            <el-table-column prop="assignee_name" label="负责人" width="100" />
            <el-table-column prop="completed_at" label="完成时间" width="180" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="viewTask(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="全部" name="all">
          <el-table :data="allTasks" v-loading="loading" border stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="task_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="taskTypeColor(row.task_type)">{{ taskTypeText(row.task_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="任务标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="employee_name" label="所属员工" width="100" />
            <el-table-column prop="assignee_name" label="负责人" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusColor(row.status)">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="viewTask(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <el-dialog v-model="detailVisible" title="任务详情" width="600px">
      <el-descriptions :column="2" border v-if="currentTask">
        <el-descriptions-item label="任务类型">
          <el-tag :type="taskTypeColor(currentTask.task_type)">{{ taskTypeText(currentTask.task_type) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="优先级">
          <el-tag :type="priorityColor(currentTask.priority)" effect="dark">{{ priorityText(currentTask.priority) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="任务标题" :span="2">{{ currentTask.title }}</el-descriptions-item>
        <el-descriptions-item label="所属员工">{{ currentTask.employee_name }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ currentTask.assignee_name }}</el-descriptions-item>
        <el-descriptions-item label="截止日期">{{ currentTask.deadline }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusColor(currentTask.status)">{{ statusText(currentTask.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="升级级别">
          <el-tag v-if="currentTask.escalation_level > 0" type="danger">已升级</el-tag>
          <span v-else>正常</span>
        </el-descriptions-item>
        <el-descriptions-item label="催办次数">{{ currentTask.reminder_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="任务描述" :span="2">
          <div style="white-space: pre-wrap;">{{ currentTask.description }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="完成说明" :span="2" v-if="currentTask.completed_notes">
          <div style="white-space: pre-wrap;">{{ currentTask.completed_notes }}</div>
        </el-descriptions-item>
      </el-descriptions>
      
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button
          v-if="canHandle(currentTask)"
          type="primary"
          @click="handleComplete(currentTask)"
        >
          处理任务
        </el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="completeVisible" title="处理任务" width="500px">
      <el-form :model="completeForm" label-width="80px">
        <el-form-item label="任务">
          <el-tag>{{ currentTask?.title }}</el-tag>
        </el-form-item>
        <el-form-item label="处理说明" required>
          <el-input v-model="completeForm.notes" type="textarea" :rows="4" placeholder="请输入处理说明..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="completeVisible = false">取消</el-button>
        <el-button type="primary" @click="submitComplete" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  RefreshRight, Clock, Check, Close, Warning, User
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { getTasks, completeTask, approveTask, getTaskStatistics, runDailyCheck as apiRunDailyCheck } from '@/api/task'

const userStore = useUserStore()

const loading = ref(false)
const activeTab = ref('pending')
const allTasks = ref([])
const taskStatsData = ref(null)

const taskStats = computed(() => {
  if (!taskStatsData.value) return []
  
  return [
    { label: '待处理', value: taskStatsData.value.pending + taskStatsData.value.in_progress, color: '#e6a23c', icon: Clock },
    { label: '已升级', value: taskStatsData.value.escalated, color: '#f56c6c', icon: Warning },
    { label: '已完成', value: taskStatsData.value.completed, color: '#67c23a', icon: Check },
    { label: '已过期', value: taskStatsData.value.overdue, color: '#f56c6c', icon: Close },
    { label: '即将到期', value: taskStatsData.value.due_soon, color: '#e6a23c', icon: Clock },
    { label: '总任务', value: taskStatsData.value.total, color: '#409eff', icon: User },
  ]
})

const filteredTasks = computed(() => {
  const pending = ['pending', 'in_progress', 'escalated']
  const completed = ['completed', 'cancelled']
  
  return {
    pending: allTasks.value.filter(t => pending.includes(t.status)),
    completed: allTasks.value.filter(t => completed.includes(t.status)),
  }
})

const detailVisible = ref(false)
const currentTask = ref(null)

const completeVisible = ref(false)
const completeForm = reactive({ notes: '' })
const submitting = ref(false)

async function fetchTasks() {
  try {
    loading.value = true
    const params = {}
    
    if (userStore.isEmployee) {
      params.assignee_id = userStore.user.employee_id
    }
    
    const result = await getTasks({ ...params, limit: 100 })
    allTasks.value = result.items || []
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  } finally {
    loading.value = false
  }
}

async function fetchTaskStats() {
  try {
    taskStatsData.value = await getTaskStatistics()
  } catch (error) {
    console.error('Failed to fetch task stats:', error)
  }
}

function viewTask(task) {
  currentTask.value = task
  detailVisible.value = true
}

function handleComplete(task) {
  currentTask.value = task
  completeForm.notes = ''
  completeVisible.value = true
}

async function submitComplete() {
  if (!completeForm.notes.trim()) {
    ElMessage.warning('请输入处理说明')
    return
  }
  
  try {
    submitting.value = true
    await completeTask(currentTask.value.id, completeForm.notes)
    ElMessage.success('任务已处理')
    completeVisible.value = false
    detailVisible.value = false
    fetchTasks()
    fetchTaskStats()
  } catch (error) {
    console.error('Complete failed:', error)
  } finally {
    submitting.value = false
  }
}

async function handleApprove(task) {
  try {
    await ElMessageBox.confirm('确定审批通过该任务吗？', '提示', { type: 'success' })
    
    await approveTask(task.id, '审批通过')
    ElMessage.success('审批通过')
    fetchTasks()
    fetchTaskStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Approve failed:', error)
    }
  }
}

async function runDailyCheck() {
  try {
    const result = await apiRunDailyCheck()
    ElMessage.success(`每日检查完成，创建了 ${result.details?.tasks_created || 0} 个任务`)
    fetchTasks()
    fetchTaskStats()
  } catch (error) {
    console.error('Daily check failed:', error)
  }
}

function canHandle(task) {
  if (['completed', 'cancelled'].includes(task.status)) return false
  if (userStore.isEmployee && task.assignee_id === userStore.user.employee_id) return true
  if (userStore.isManager) return true
  return false
}

function taskTypeText(type) {
  const types = { renewal: '续期', supplement: '补办', verification: '验证', correction: '更正' }
  return types[type] || type
}

function taskTypeColor(type) {
  const colors = { renewal: 'warning', supplement: 'danger', verification: 'info', correction: 'primary' }
  return colors[type] || ''
}

function priorityText(priority) {
  const priorities = { low: '低', medium: '中', high: '高', urgent: '紧急' }
  return priorities[priority] || priority
}

function priorityColor(priority) {
  const colors = { low: '', medium: 'warning', high: 'danger', urgent: 'danger' }
  return colors[priority] || ''
}

function statusText(status) {
  const statuses = {
    pending: '待处理',
    in_progress: '处理中',
    escalated: '已升级',
    completed: '已完成',
    cancelled: '已取消',
    rejected: '已驳回'
  }
  return statuses[status] || status
}

function statusColor(status) {
  const colors = {
    pending: 'warning',
    in_progress: 'primary',
    escalated: 'danger',
    completed: 'success',
    cancelled: 'info',
    rejected: 'danger'
  }
  return colors[status] || ''
}

function isOverdue(task) {
  return task.days_overdue && task.days_overdue > 0
}

onMounted(() => {
  fetchTasks()
  fetchTaskStats()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-stats {
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.task-tabs {
  margin-top: 16px;
}

.text-danger {
  color: #f56c6c;
}
</style>
