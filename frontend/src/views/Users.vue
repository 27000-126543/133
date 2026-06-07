<template>
  <div class="page-container">
    <el-card class="card-shadow">
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon>添加用户
          </el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="角色">
          <el-select v-model="filterRole" placeholder="全部角色" clearable style="width: 150px;">
            <el-option label="管理员" value="admin" />
            <el-option label="部门经理" value="manager" />
            <el-option label="普通员工" value="employee" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchUsers">
            <el-icon><Search /></el-icon>查询
          </el-button>
        </el-form-item>
      </el-form>

      <el-table :data="users" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)">{{ roleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              :type="row.is_active ? 'danger' : 'success'"
              size="small"
              link
              @click="toggleActive(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button type="primary" size="small" link @click="resetPassword(row)">
              重置密码
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="addDialogVisible" title="添加用户" width="500px">
      <el-form :model="addForm" label-width="100px" ref="addFormRef">
        <el-form-item label="用户名" prop="username" :rules="[{ required: true, message: '请输入用户名' }]">
          <el-input v-model="addForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name" :rules="[{ required: true, message: '请输入姓名' }]">
          <el-input v-model="addForm.full_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="密码" prop="password" :rules="[{ required: true, message: '请输入密码' }]">
          <el-input v-model="addForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role" :rules="[{ required: true, message: '请选择角色' }]">
          <el-select v-model="addForm.role" placeholder="请选择角色" style="width: 100%;">
            <el-option label="管理员" value="admin" />
            <el-option label="部门经理" value="manager" />
            <el-option label="普通员工" value="employee" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="addForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="addForm.phone" placeholder="请输入电话" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addUser" :loading="adding">确认添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px">
      <el-form :model="resetForm" label-width="100px">
        <el-form-item label="新密码" prop="new_password" :rules="[{ required: true, message: '请输入新密码' }]">
          <el-input v-model="resetForm.new_password" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password" :rules="[{ required: true, message: '请确认新密码' }]">
          <el-input v-model="resetForm.confirm_password" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmReset" :loading="resetting">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { getUsers, toggleUserActive, register, changePassword } from '@/api/auth'

const loading = ref(false)
const adding = ref(false)
const resetting = ref(false)
const filterRole = ref('')
const users = ref([])
const addDialogVisible = ref(false)
const resetDialogVisible = ref(false)
const addFormRef = ref(null)
const addForm = ref({
  username: '',
  full_name: '',
  password: '',
  role: 'employee',
  email: '',
  phone: ''
})
const resetForm = ref({
  new_password: '',
  confirm_password: ''
})
const currentUser = ref(null)

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
    admin: '管理员',
    manager: '部门经理',
    employee: '普通员工'
  }
  return texts[role] || role
}

async function fetchUsers() {
  try {
    loading.value = true
    const params = filterRole.value ? { role: filterRole.value } : {}
    const result = await getUsers(params)
    users.value = result || []
  } catch (error) {
    console.error('Failed to fetch users:', error)
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  addForm.value = {
    username: '',
    full_name: '',
    password: '',
    role: 'employee',
    email: '',
    phone: ''
  }
  addDialogVisible.value = true
}

async function addUser() {
  try {
    if (!addForm.value.username || !addForm.value.full_name || !addForm.value.password || !addForm.value.role) {
      ElMessage.warning('请填写必填项')
      return
    }
    adding.value = true
    await register(addForm.value)
    ElMessage.success('用户添加成功')
    addDialogVisible.value = false
    fetchUsers()
  } catch (error) {
    console.error('Add user failed:', error)
  } finally {
    adding.value = false
  }
}

async function toggleActive(user) {
  try {
    const action = user.is_active ? '禁用' : '启用'
    await ElMessageBox.confirm(`确定要${action}用户 ${user.username} 吗？`, '确认操作', {
      type: 'warning'
    })
    const result = await toggleUserActive(user.id, !user.is_active)
    ElMessage.success(result.message || `用户已${action}`)
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Toggle user failed:', error)
    }
  }
}

function resetPassword(user) {
  currentUser.value = user
  resetForm.value = {
    new_password: '',
    confirm_password: ''
  }
  resetDialogVisible.value = true
}

async function confirmReset() {
  try {
    if (resetForm.value.new_password !== resetForm.value.confirm_password) {
      ElMessage.warning('两次输入的密码不一致')
      return
    }
    if (resetForm.value.new_password.length < 6) {
      ElMessage.warning('密码长度至少6位')
      return
    }
    resetting.value = true
    ElMessage.success('密码重置功能需要后端支持修改其他用户密码')
    resetDialogVisible.value = false
  } catch (error) {
    console.error('Reset password failed:', error)
  } finally {
    resetting.value = false
  }
}

onMounted(() => {
  fetchUsers()
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
</style>
