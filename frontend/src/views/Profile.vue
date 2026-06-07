<template>
  <div class="page-container">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="card-shadow profile-card">
          <div class="profile-header">
            <el-avatar :size="100" class="avatar">
              {{ user?.full_name?.charAt(0) || 'U' }}
            </el-avatar>
            <h2>{{ user?.full_name }}</h2>
            <p class="username">@{{ user?.username }}</p>
            <el-tag :type="roleType(user?.role)" size="large" class="role-tag">
              {{ roleText(user?.role) }}
            </el-tag>
          </div>
          
          <el-divider />
          
          <el-descriptions :column="1" border>
            <el-descriptions-item label="邮箱">{{ user?.email || '-' }}</el-descriptions-item>
            <el-descriptions-item label="电话">{{ user?.phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ user?.created_at }}</el-descriptions-item>
            <el-descriptions-item label="上次登录">{{ user?.last_login_at || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      
      <el-col :span="16">
        <el-card class="card-shadow">
          <template #header>
            <div class="card-header">
              <span>账户设置</span>
            </div>
          </template>
          
          <el-tabs v-model="activeTab">
            <el-tab-pane label="基本信息" name="info">
              <el-form :model="profileForm" label-width="100px" style="max-width: 500px;">
                <el-form-item label="姓名">
                  <el-input v-model="profileForm.full_name" placeholder="请输入姓名" />
                </el-form-item>
                <el-form-item label="邮箱">
                  <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
                </el-form-item>
                <el-form-item label="电话">
                  <el-input v-model="profileForm.phone" placeholder="请输入电话" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="updateProfile" :loading="updating">
                    保存修改
                  </el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>
            
            <el-tab-pane label="修改密码" name="password">
              <el-form :model="passwordForm" label-width="120px" style="max-width: 500px;" ref="passwordFormRef">
                <el-form-item
                  label="原密码"
                  prop="old_password"
                  :rules="[{ required: true, message: '请输入原密码' }]"
                >
                  <el-input
                    v-model="passwordForm.old_password"
                    type="password"
                    placeholder="请输入原密码"
                    show-password
                  />
                </el-form-item>
                <el-form-item
                  label="新密码"
                  prop="new_password"
                  :rules="[
                    { required: true, message: '请输入新密码' },
                    { min: 6, message: '密码长度至少6位' }
                  ]"
                >
                  <el-input
                    v-model="passwordForm.new_password"
                    type="password"
                    placeholder="请输入新密码"
                    show-password
                  />
                </el-form-item>
                <el-form-item
                  label="确认新密码"
                  prop="confirm_password"
                  :rules="[
                    { required: true, message: '请确认新密码' },
                    { validator: validateConfirmPassword, trigger: 'blur' }
                  ]"
                >
                  <el-input
                    v-model="passwordForm.confirm_password"
                    type="password"
                    placeholder="请再次输入新密码"
                    show-password
                  />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="changePassword" :loading="changingPassword">
                    修改密码
                  </el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>
            
            <el-tab-pane label="我的证书" name="certs">
              <el-table :data="myCertificates" v-loading="loadingCerts" border stripe>
                <el-table-column prop="certificate_name" label="证书名称" min-width="200" />
                <el-table-column prop="cert_type_name" label="证书类型" width="150" />
                <el-table-column prop="issuing_authority" label="颁发机构" width="180" />
                <el-table-column prop="issue_date" label="颁发日期" width="120" />
                <el-table-column prop="expiry_date" label="到期日期" width="120" />
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="核验状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.is_verified ? 'success' : 'warning'">
                      {{ row.is_verified ? '已核验' : '待核验' }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            
            <el-tab-pane label="我的任务" name="tasks">
              <el-table :data="myTasks" v-loading="loadingTasks" border stripe>
                <el-table-column prop="task_code" label="任务编号" width="140" />
                <el-table-column prop="title" label="任务标题" min-width="200" />
                <el-table-column prop="task_type" label="任务类型" width="120">
                  <template #default="{ row }">
                    <el-tag size="small">{{ taskTypeText(row.task_type) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="deadline" label="截止日期" width="120" />
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="taskStatusType(row.status)">{{ taskStatusText(row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" label="创建时间" width="180" />
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getCurrentUser, changePassword as apiChangePassword } from '@/api/auth'
import { getCertificates } from '@/api/certificate'
import { getTasks } from '@/api/task'

const userStore = useUserStore()
const user = computed(() => userStore.user)

const activeTab = ref('info')
const updating = ref(false)
const changingPassword = ref(false)
const loadingCerts = ref(false)
const loadingTasks = ref(false)
const myCertificates = ref([])
const myTasks = ref([])
const passwordFormRef = ref(null)

const profileForm = ref({
  full_name: '',
  email: '',
  phone: ''
})

const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

function roleType(role) {
  const types = {
    admin: 'danger',
    manager: 'warning',
    employee: 'info'
  }
  return types[role] || 'info'
}

function roleText(role) {
  const texts = {
    admin: '系统管理员',
    manager: '部门经理',
    employee: '普通员工'
  }
  return texts[role] || role
}

function statusType(status) {
  const types = {
    valid: 'success',
    expiring_soon: 'warning',
    expired: 'danger'
  }
  return types[status] || 'info'
}

function statusText(status) {
  const texts = {
    valid: '有效',
    expiring_soon: '即将到期',
    expired: '已过期'
  }
  return texts[status] || status
}

function taskTypeText(type) {
  const texts = {
    reissue: '补办证书',
    renew: '续期证书',
    training: '培训学习',
    other: '其他任务'
  }
  return texts[type] || type
}

function taskStatusType(status) {
  const types = {
    pending: 'warning',
    in_progress: 'primary',
    completed: 'success',
    rejected: 'danger',
    expired: 'info'
  }
  return types[status] || 'info'
}

function taskStatusText(status) {
  const texts = {
    pending: '待处理',
    in_progress: '处理中',
    completed: '已完成',
    rejected: '已驳回',
    expired: '已过期'
  }
  return texts[status] || status
}

function validateConfirmPassword(rule, value, callback) {
  if (value !== passwordForm.value.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

async function fetchUserInfo() {
  try {
    const result = await getCurrentUser()
    userStore.setUser(result)
    profileForm.value = {
      full_name: result.full_name || '',
      email: result.email || '',
      phone: result.phone || ''
    }
  } catch (error) {
    console.error('Failed to fetch user info:', error)
  }
}

async function fetchMyCertificates() {
  try {
    loadingCerts.value = true
    const params = user.value?.employee_id ? { employee_id: user.value.employee_id } : {}
    const result = await getCertificates(params)
    myCertificates.value = result.items || []
  } catch (error) {
    console.error('Failed to fetch certificates:', error)
  } finally {
    loadingCerts.value = false
  }
}

async function fetchMyTasks() {
  try {
    loadingTasks.value = true
    const params = user.value?.employee_id ? { assignee_id: user.value.employee_id } : {}
    const result = await getTasks(params)
    myTasks.value = result.items || []
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  } finally {
    loadingTasks.value = false
  }
}

async function updateProfile() {
  try {
    updating.value = true
    ElMessage.success('个人信息更新功能需要后端支持')
  } catch (error) {
    console.error('Update profile failed:', error)
  } finally {
    updating.value = false
  }
}

async function changePassword() {
  try {
    if (!passwordForm.value.old_password || !passwordForm.value.new_password || !passwordForm.value.confirm_password) {
      ElMessage.warning('请填写所有密码字段')
      return
    }
    if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
      ElMessage.warning('两次输入的密码不一致')
      return
    }
    if (passwordForm.value.new_password.length < 6) {
      ElMessage.warning('新密码长度至少6位')
      return
    }
    
    changingPassword.value = true
    await apiChangePassword(passwordForm.value)
    ElMessage.success('密码修改成功')
    passwordForm.value = {
      old_password: '',
      new_password: '',
      confirm_password: ''
    }
  } catch (error) {
    console.error('Change password failed:', error)
  } finally {
    changingPassword.value = false
  }
}

onMounted(() => {
  fetchUserInfo()
  fetchMyCertificates()
  fetchMyTasks()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.profile-card {
  text-align: center;
}

.profile-header {
  padding: 20px 0;
}

.avatar {
  margin-bottom: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-size: 40px;
  font-weight: bold;
}

.profile-header h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
}

.username {
  margin: 0 0 12px 0;
  color: #909399;
  font-size: 14px;
}

.role-tag {
  margin-top: 8px;
}
</style>
