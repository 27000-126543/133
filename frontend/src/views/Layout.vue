<template>
  <el-container class="layout-container">
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="logo">
        <el-icon :size="32" color="#409eff"><Promotion /></el-icon>
        <span v-if="!isCollapse">证书管理系统</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        unique-opened
      >
        <template v-for="item in menuItems" :key="item.path">
          <el-menu-item
            v-if="!item.roles || item.roles.includes(userRole)"
            :index="item.path"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
      
      <div class="collapse-btn" @click="toggleSidebar">
        <el-icon>
          <Fold v-if="!isCollapse" />
          <Expand v-else />
        </el-icon>
      </div>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-tooltip content="刷新数据">
            <el-button type="primary" plain :icon="Refresh" circle @click="refreshData" />
          </el-tooltip>
          
          <el-dropdown @command="handleCommand">
            <div class="user-info">
              <el-avatar :size="32" :src="userAvatar">
                {{ userStore.user?.full_name?.charAt(0) || 'U' }}
              </el-avatar>
              <span class="username">{{ userStore.user?.full_name }}</span>
              <el-tag :type="roleTagType" size="small" effect="dark">
                {{ roleText }}
              </el-tag>
              <el-icon><CaretBottom /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item command="password">
                  <el-icon><Lock /></el-icon>修改密码
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
    
    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="400px"
    >
      <el-form ref="passwordForm" :model="passwordForm" :rules="passwordRules" label-width="100px">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword" :loading="passwordLoading">确认</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh, User, Lock, SwitchButton, CaretBottom,
  Fold, Expand, Promotion,
  Odometer, Monitor, Document, List,
  DataAnalysis, Reading, UserFilled, Notebook, Setting
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { changePassword } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const sidebarWidth = computed(() => isCollapse.value ? '64px' : '210px')

const userRole = computed(() => userStore.user?.role || 'employee')
const roleText = computed(() => {
  const roles = { admin: '管理员', manager: '部门经理', employee: '员工' }
  return roles[userRole.value] || '员工'
})
const roleTagType = computed(() => {
  const types = { admin: 'danger', manager: 'warning', employee: 'success' }
  return types[userRole.value] || 'success'
})

const userAvatar = ref('')

const activeMenu = computed(() => route.path)
const currentPageTitle = computed(() => route.meta.title || '')

const menuItems = computed(() => {
  const baseItems = [
    { path: '/dashboard', title: '仪表盘', icon: Odometer, roles: ['admin', 'manager'] },
    { path: '/workbench', title: '工作台', icon: Monitor, roles: ['admin', 'manager', 'employee'] },
    { path: '/certificates', title: '证书管理', icon: Document, roles: ['admin', 'manager', 'employee'] },
    { path: '/tasks', title: '任务管理', icon: List, roles: ['admin', 'manager', 'employee'] },
    { path: '/employees', title: '员工管理', icon: User, roles: ['admin', 'manager'] },
    { path: '/reports', title: '报告中心', icon: DataAnalysis, roles: ['admin', 'manager'] },
    { path: '/training', title: '培训管理', icon: Reading, roles: ['admin', 'manager'] },
    { path: '/users', title: '用户管理', icon: UserFilled, roles: ['admin'] },
    { path: '/logs', title: '操作日志', icon: Notebook, roles: ['admin'] },
    { path: '/profile', title: '个人中心', icon: Setting, roles: ['admin', 'manager', 'employee'] },
  ]
  return baseItems
})

const passwordDialogVisible = ref(false)
const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})
const passwordLoading = ref(false)

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.value.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 6, message: '密码长度至少6位', trigger: 'blur' }],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

function toggleSidebar() {
  isCollapse.value = !isCollapse.value
}

function handleCommand(command) {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'password':
      passwordDialogVisible.value = true
      passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
      break
    case 'logout':
      handleLogout()
      break
  }
}

async function handleChangePassword() {
  try {
    passwordLoading.value = true
    await changePassword(passwordForm.value)
    ElMessage.success('密码修改成功，请重新登录')
    passwordDialogVisible.value = false
    userStore.logoutUser()
    router.push('/login')
  } catch (error) {
    console.error('Change password error:', error)
  } finally {
    passwordLoading.value = false
  }
}

function handleLogout() {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    userStore.logoutUser()
    router.push('/login')
    ElMessage.success('已退出登录')
  }).catch(() => {})
}

function refreshData() {
  window.location.reload()
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background: #304156;
  transition: width 0.3s;
  display: flex;
  flex-direction: column;
  position: relative;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #1f2d3d;
  white-space: nowrap;
  overflow: hidden;
}

:deep(.el-menu) {
  border-right: none;
  flex: 1;
}

:deep(.el-menu-item) {
  height: 50px;
  line-height: 50px;
}

.collapse-btn {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #bfcbd9;
  cursor: pointer;
  border-top: 1px solid #1f2d3d;
  transition: background 0.3s;
}

.collapse-btn:hover {
  background: #263445;
  color: #fff;
}

.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 4px;
  transition: background 0.3s;
}

.user-info:hover {
  background: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #303133;
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
