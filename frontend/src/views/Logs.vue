<template>
  <div class="page-container">
    <el-card class="card-shadow">
      <template #header>
        <div class="card-header">
          <span>操作日志</span>
          <el-button type="primary" @click="fetchLogs">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="操作类型">
          <el-select v-model="filterAction" placeholder="全部操作" clearable style="width: 180px;">
            <el-option label="用户登录" value="user_login" />
            <el-option label="用户注册" value="user_register" />
            <el-option label="密码修改" value="password_change" />
            <el-option label="证书上传" value="certificate_upload" />
            <el-option label="证书审核" value="certificate_audit" />
            <el-option label="任务创建" value="task_create" />
            <el-option label="任务完成" value="task_complete" />
            <el-option label="报告生成" value="report_generation" />
            <el-option label="培训计划" value="training_plan" />
            <el-option label="数据导入" value="data_import" />
            <el-option label="数据导出" value="data_export" />
          </el-select>
        </el-form-item>
        <el-form-item label="资源类型">
          <el-select v-model="filterResource" placeholder="全部资源" clearable style="width: 150px;">
            <el-option label="用户" value="user" />
            <el-option label="证书" value="certificate" />
            <el-option label="任务" value="task" />
            <el-option label="报告" value="report" />
            <el-option label="培训" value="training" />
            <el-option label="员工" value="employee" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchLogs">
            <el-icon><Search /></el-icon>查询
          </el-button>
        </el-form-item>
      </el-form>

      <el-table :data="logs" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="timestamp" label="操作时间" width="180" />
        <el-table-column prop="user_name" label="操作人" width="120" />
        <el-table-column label="操作类型" width="130">
          <template #default="{ row }">
            <el-tag :type="actionType(row.action)">{{ actionText(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资源类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.resource_type || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_id" label="资源ID" width="100" align="center" />
        <el-table-column prop="ip_address" label="IP地址" width="130" />
        <el-table-column label="操作详情" min-width="300">
          <template #default="{ row }">
            <div v-if="row.details" class="details-cell">
              <el-tooltip :content="formatDetails(row.details)" placement="top">
                <span>{{ formatDetails(row.details) }}</span>
              </el-tooltip>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchLogs"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { getAuditLogs } from '@/api/common'

const loading = ref(false)
const filterAction = ref('')
const filterResource = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const logs = ref([])

function actionType(action) {
  const successTypes = ['user_login', 'certificate_audit', 'task_complete', 'report_generation']
  const warningTypes = ['task_create', 'training_plan']
  const dangerTypes = ['password_change', 'user_register']
  
  if (successTypes.includes(action)) return 'success'
  if (warningTypes.includes(action)) return 'warning'
  if (dangerTypes.includes(action)) return 'danger'
  return 'info'
}

function actionText(action) {
  const texts = {
    user_login: '用户登录',
    user_register: '用户注册',
    password_change: '密码修改',
    certificate_upload: '证书上传',
    certificate_audit: '证书审核',
    task_create: '任务创建',
    task_complete: '任务完成',
    task_approve: '任务审批',
    task_reject: '任务驳回',
    task_escalate: '任务升级',
    report_generation: '报告生成',
    training_plan: '培训计划',
    data_import: '数据导入',
    data_export: '数据导出',
    user_toggle_active: '用户状态变更'
  }
  return texts[action] || action
}

function formatDetails(details) {
  if (typeof details === 'string') {
    return details
  }
  if (typeof details === 'object') {
    const parts = []
    for (const [key, value] of Object.entries(details)) {
      const keyText = {
        username: '用户名',
        role: '角色',
        created_by: '创建人',
        certificate_type: '证书类型',
        certificate_name: '证书名称',
        employee_name: '员工姓名',
        task_type: '任务类型',
        deadline: '截止日期',
        report_month: '报告月份',
        departments_count: '部门数量',
        plan_code: '计划编号',
        plan_name: '计划名称'
      }
      parts.push(`${keyText[key] || key}: ${value}`)
    }
    return parts.join(' | ')
  }
  return '-'
}

async function fetchLogs() {
  try {
    loading.value = true
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    if (filterAction.value) params.action = filterAction.value
    if (filterResource.value) params.resource_type = filterResource.value
    
    const result = await getAuditLogs(params)
    logs.value = result.items || []
    total.value = result.total || 0
  } catch (error) {
    console.error('Failed to fetch logs:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 16px;
}

.details-cell {
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
