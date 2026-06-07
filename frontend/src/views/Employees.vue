<template>
  <div class="page-container">
    <el-row :gutter="20">
      <el-col :lg="18">
        <el-card class="card-shadow">
          <template #header>
            <div class="card-header">
              <span>员工管理</span>
              <el-button v-if="userStore.isAdmin" type="primary" @click="showAddDialog = true">
                <el-icon><Plus /></el-icon>新增员工
              </el-button>
            </div>
          </template>
          
          <div class="search-bar">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索员工姓名、工号..."
              style="width: 300px; margin-right: 12px;"
              clearable
              @keyup.enter="searchEmployees"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select v-model="filterDept" placeholder="部门" style="width: 180px; margin-right: 12px;" clearable>
              <el-option
                v-for="dept in departments"
                :key="dept.id"
                :label="dept.name"
                :value="dept.id"
              />
            </el-select>
            <el-button type="primary" @click="searchEmployees">查询</el-button>
            <el-button @click="resetSearch">重置</el-button>
          </div>
          
          <el-table :data="employees" v-loading="loading" border stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="employee_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="gender" label="性别" width="70" />
            <el-table-column prop="phone" label="电话" width="130" />
            <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
            <el-table-column prop="position" label="岗位" width="120" />
            <el-table-column prop="department_name" label="部门" width="120" />
            <el-table-column prop="certificate_count" label="证书数" width="90" align="center" />
            <el-table-column label="合规率" width="120">
              <template #default="{ row }">
                <el-progress
                  :percentage="Math.round((row.compliance_rate || 0) * 100)"
                  :color="getComplianceColor(row.compliance_rate)"
                  :stroke-width="10"
                />
              </template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '在职' : '离职' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="viewDetail(row)">详情</el-button>
                <el-button
                  v-if="userStore.isAdmin"
                  type="warning"
                  size="small"
                  link
                  @click="editEmployee(row)"
                >
                  编辑
                </el-button>
                <el-button type="info" size="small" link @click="checkCompliance(row)">
                  合规检查
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <div class="pagination">
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.limit"
              :total="pagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="searchEmployees"
              @current-change="searchEmployees"
            />
          </div>
        </el-card>
      </el-col>
      
      <el-col :lg="6">
        <el-card class="card-shadow">
          <template #header>部门统计</template>
          <div class="dept-stats">
            <div v-for="dept in departments" :key="dept.id" class="dept-item">
              <div class="dept-header">
                <span class="dept-name">{{ dept.name }}</span>
                <el-tag size="small">{{ dept.employee_count }}人</el-tag>
              </div>
              <el-progress
                :percentage="Math.round(dept.compliance_rate * 100)"
                :color="getComplianceColor(dept.compliance_rate)"
                :stroke-width="8"
              />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-dialog v-model="detailVisible" title="员工详情" width="700px">
      <el-descriptions :column="2" border v-if="currentEmployee">
        <el-descriptions-item label="工号">{{ currentEmployee.employee_no }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ currentEmployee.name }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ currentEmployee.gender || '-' }}</el-descriptions-item>
        <el-descriptions-item label="部门">{{ currentEmployee.department_name }}</el-descriptions-item>
        <el-descriptions-item label="岗位">{{ currentEmployee.position || '-' }}</el-descriptions-item>
        <el-descriptions-item label="入职日期">{{ currentEmployee.hire_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ currentEmployee.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ currentEmployee.email || '-' }}</el-descriptions-item>
      </el-descriptions>
      
      <el-divider>合规情况</el-divider>
      
      <div v-if="currentEmployee?.compliance_rate !== undefined">
        <el-alert
          v-if="currentEmployee.compliance_rate < 1"
          :title="`存在 ${currentEmployee.issues?.length || 0} 项待整改问题`"
          type="warning"
          :closable="false"
          show-icon
        />
        
        <el-steps direction="vertical" :active="currentEmployee.compliant_count || 0" finish-status="success" style="margin-top: 16px;">
          <el-step
            v-for="(issue, index) in currentEmployee.issues"
            :key="'issue-' + index"
            :title="issue.cert_type_name"
            :description="issue.issue_description"
            status="error"
          />
          <el-step
            v-for="i in (currentEmployee.compliant_count || 0)"
            :key="'ok-' + i"
            title="合规项"
            description="已满足要求"
            status="success"
          />
        </el-steps>
      </div>
      
      <el-divider>证书列表</el-divider>
      
      <el-table :data="currentEmployee?.certificates || []" size="small">
        <el-table-column prop="cert_name" label="证书名称" min-width="150" />
        <el-table-column prop="cert_type_name" label="类型" width="100" />
        <el-table-column prop="expiry_date" label="有效期" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_valid ? 'success' : 'danger'">
              {{ row.is_valid ? '有效' : '无效' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
    
    <el-dialog v-model="showAddDialog" title="新增员工" width="500px">
      <el-form :model="employeeForm" :rules="employeeRules" ref="employeeFormRef" label-width="100px">
        <el-form-item label="工号" prop="employee_no">
          <el-input v-model="employeeForm.employee_no" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="employeeForm.name" />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="employeeForm.gender">
            <el-radio value="男">男</el-radio>
            <el-radio value="女">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="部门" prop="department_id">
          <el-select v-model="employeeForm.department_id" style="width: 100%;">
            <el-option
              v-for="dept in departments"
              :key="dept.id"
              :label="dept.name"
              :value="dept.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="岗位">
          <el-input v-model="employeeForm.position" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="employeeForm.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="employeeForm.email" />
        </el-form-item>
        <el-divider>创建系统账号（可选）</el-divider>
        <el-form-item label="用户名">
          <el-input v-model="employeeForm.username" placeholder="不填写则不创建账号" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="employeeForm.password" type="password" placeholder="设置初始密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitEmployee" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { getEmployees, getEmployee, getDepartments, createEmployee } from '@/api/common'

const userStore = useUserStore()

const loading = ref(false)
const employees = ref([])
const departments = ref([])

const searchKeyword = ref('')
const filterDept = ref(null)

const pagination = reactive({
  page: 1,
  limit: 10,
  total: 0,
})

const detailVisible = ref(false)
const currentEmployee = ref(null)

const showAddDialog = ref(false)
const employeeFormRef = ref(null)
const employeeForm = reactive({
  employee_no: '',
  name: '',
  gender: '男',
  department_id: null,
  position: '',
  phone: '',
  email: '',
  username: '',
  password: '',
})
const submitting = ref(false)

const employeeRules = {
  employee_no: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  department_id: [{ required: true, message: '请选择部门', trigger: 'change' }],
}

async function fetchDepartments() {
  try {
    departments.value = await getDepartments()
  } catch (error) {
    console.error('Failed to fetch departments:', error)
  }
}

async function searchEmployees() {
  try {
    loading.value = true
    
    const params = {
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit,
    }
    
    if (filterDept.value) {
      params.department_id = filterDept.value
    }
    
    const result = await getEmployees(params)
    employees.value = result.items || []
    pagination.total = result.total || 0
  } catch (error) {
    console.error('Search failed:', error)
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  searchKeyword.value = ''
  filterDept.value = null
  pagination.page = 1
  searchEmployees()
}

async function viewDetail(emp) {
  try {
    currentEmployee.value = await getEmployee(emp.id)
    detailVisible.value = true
  } catch (error) {
    console.error('Failed to fetch employee detail:', error)
  }
}

function editEmployee(emp) {
  ElMessage.info('编辑功能开发中')
}

function checkCompliance(emp) {
  viewDetail(emp)
}

async function submitEmployee() {
  if (!employeeFormRef.value) return
  
  try {
    await employeeFormRef.value.validate()
    submitting.value = true
    
    await createEmployee(employeeForm)
    ElMessage.success('员工创建成功')
    showAddDialog.value = false
    searchEmployees()
    fetchDepartments()
  } catch (error) {
    if (error !== false) {
      console.error('Submit failed:', error)
    }
  } finally {
    submitting.value = false
  }
}

function getComplianceColor(rate) {
  if (rate >= 0.8) return '#67c23a'
  if (rate >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

onMounted(() => {
  fetchDepartments()
  searchEmployees()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-bar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.dept-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dept-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.dept-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.dept-name {
  font-weight: 500;
}
</style>
