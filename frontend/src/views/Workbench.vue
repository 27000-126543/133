<template>
  <div class="workbench">
    <el-row :gutter="20">
      <el-col :lg="6">
        <el-card class="card-shadow profile-card">
          <div class="profile-header">
            <el-avatar :size="80">
              {{ userStore.user?.full_name?.charAt(0) || 'U' }}
            </el-avatar>
            <div class="profile-info">
              <h3>{{ userStore.user?.full_name }}</h3>
              <p>{{ employeeInfo?.position || '员工' }}</p>
              <el-tag :type="departmentTagType" size="small">
                {{ employeeInfo?.department_name || '未分配部门' }}
              </el-tag>
            </div>
          </div>
          
          <el-divider />
          
          <div class="profile-stats">
            <div class="stat-item">
              <div class="stat-num text-primary">{{ employeeInfo?.certificate_count || 0 }}</div>
              <div class="stat-label">证书总数</div>
            </div>
            <div class="stat-item">
              <div class="stat-num text-success">{{ complianceRate }}%</div>
              <div class="stat-label">合规率</div>
            </div>
            <div class="stat-item">
              <div class="stat-num text-warning">{{ pendingTasks }}</div>
              <div class="stat-label">待办任务</div>
            </div>
          </div>
        </el-card>
        
        <el-card class="card-shadow quick-actions">
          <template #header>快捷操作</template>
          <div class="action-grid">
            <div class="action-item" @click="showUploadDialog = true">
              <el-icon :size="28" color="#409eff"><Upload /></el-icon>
              <span>上传证书</span>
            </div>
            <div class="action-item" @click="goToTasks">
              <el-icon :size="28" color="#e6a23c"><List /></el-icon>
              <span>我的任务</span>
            </div>
            <div class="action-item" @click="goToCertificates">
              <el-icon :size="28" color="#67c23a"><Document /></el-icon>
              <span>我的证书</span>
            </div>
            <div class="action-item" @click="goToProfile">
              <el-icon :size="28" color="#909399"><User /></el-icon>
              <span>个人中心</span>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :lg="18">
        <el-card class="card-shadow">
          <template #header>
            <div class="card-header">
              <span>我的待办任务</span>
              <el-button type="primary" link @click="goToTasks">查看全部</el-button>
            </div>
          </template>
          
          <el-table :data="myTasks" size="default" v-loading="loading">
            <el-table-column prop="title" label="任务标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="task_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="taskTypeColor(row.task_type)">{{ taskTypeText(row.task_type) }}</el-tag>
              </template>
            </el-table-column>
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
            <el-table-column prop="days_overdue" label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.days_overdue && row.days_overdue > 0" type="danger">
                  超期{{ row.days_overdue }}天
                </el-tag>
                <el-tag v-else-if="row.days_overdue !== null && row.days_overdue <= 0" type="warning">
                  剩余{{ Math.abs(row.days_overdue) }}天
                </el-tag>
                <el-tag v-else type="info">处理中</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="handleCompleteTask(row)">
                  处理
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <el-empty v-if="myTasks.length === 0 && !loading" description="暂无待办任务" />
        </el-card>
        
        <el-card class="card-shadow" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <span>合规检查报告</span>
              <el-tag v-if="employeeCompliance?.issues?.length > 0" type="danger">
                {{ employeeCompliance.issues.length }} 项待整改
              </el-tag>
            </div>
          </template>
          
          <div v-if="employeeCompliance">
            <el-alert
              v-if="employeeCompliance.issues?.length > 0"
              title="您有以下合规问题需要处理"
              type="warning"
              :closable="false"
              show-icon
              style="margin-bottom: 16px;"
            />
            
            <el-steps direction="vertical" :active="employeeCompliance.compliant_count" finish-status="success">
              <el-step
                v-for="(issue, index) in employeeCompliance.issues"
                :key="index"
                :title="issue.cert_type_name"
                :description="issue.issue_description"
                status="error"
              />
              <el-step
                v-for="i in employeeCompliance.compliant_count"
                :key="'compliant-' + i"
                title="合规项"
                description="已满足要求"
                status="success"
              />
            </el-steps>
          </div>
        </el-card>
        
        <el-card class="card-shadow" style="margin-top: 20px;">
          <template #header>我的证书列表</template>
          <el-table :data="myCertificates" size="small" v-loading="loading">
            <el-table-column prop="cert_name" label="证书名称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="cert_number" label="证书编号" width="160" />
            <el-table-column prop="expiry_date" label="有效期至" width="120" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row)">
                  {{ getStatusText(row) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="viewCertificate(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
    
    <el-dialog v-model="showUploadDialog" title="上传证书" width="600px" @close="resetUploadForm">
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="证书图片">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            accept="image/*"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">将图片拖到此处，或<em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">
                支持 jpg/png/bmp 格式，大小不超过 10MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item v-if="ocrPreview" label="OCR识别结果">
          <div class="ocr-preview">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="证书名称">
                <span v-if="ocrPreview.cert_name">{{ ocrPreview.cert_name }}</span>
                <el-input v-else v-model="uploadForm.manual_cert_name" placeholder="请手动输入证书名称" />
              </el-descriptions-item>
              <el-descriptions-item label="证书编号">
                <span v-if="ocrPreview.cert_number">{{ ocrPreview.cert_number }}</span>
                <el-input v-else v-model="uploadForm.manual_cert_number" placeholder="请手动输入证书编号" />
              </el-descriptions-item>
              <el-descriptions-item label="颁发机构">
                <span v-if="ocrPreview.issuing_authority">{{ ocrPreview.issuing_authority }}</span>
                <el-input v-else v-model="uploadForm.manual_issuing_authority" placeholder="请手动输入颁发机构" />
              </el-descriptions-item>
              <el-descriptions-item label="签发日期">
                <span v-if="ocrPreview.issue_date">{{ ocrPreview.issue_date }}</span>
                <el-date-picker v-else v-model="uploadForm.manual_issue_date" type="date" placeholder="选择日期" />
              </el-descriptions-item>
              <el-descriptions-item label="有效期至">
                <span v-if="ocrPreview.expiry_date">{{ ocrPreview.expiry_date }}</span>
                <el-date-picker v-else v-model="uploadForm.manual_expiry_date" type="date" placeholder="选择日期" />
              </el-descriptions-item>
            </el-descriptions>
            <el-alert
              v-if="ocrPreview.confidence < 0.7"
              type="warning"
              :title="`识别置信度较低 (${Math.round(ocrPreview.confidence * 100)}%)，请核对或手动填写信息`"
              :closable="false"
              style="margin-top: 12px;"
            />
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="handleOCRPreview" :loading="ocrLoading" v-if="!ocrPreview">
          识别信息
        </el-button>
        <el-button type="success" @click="handleUploadSubmit" :loading="uploadLoading" v-else>
          提交审核
        </el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="completeDialogVisible" title="完成任务" width="500px">
      <el-form :model="completeForm" label-width="80px">
        <el-form-item label="任务" prop="title">
          <el-tag>{{ currentTask?.title }}</el-tag>
        </el-form-item>
        <el-form-item label="处理说明" prop="notes">
          <el-input v-model="completeForm.notes" type="textarea" :rows="4" placeholder="请输入处理说明..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="completeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCompleteTask" :loading="completeLoading">提交</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="certDetailVisible" title="证书详情" width="600px">
      <el-descriptions :column="2" border v-if="currentCertificate">
        <el-descriptions-item label="证书名称">{{ currentCertificate.cert_name }}</el-descriptions-item>
        <el-descriptions-item label="证书编号">{{ currentCertificate.cert_number }}</el-descriptions-item>
        <el-descriptions-item label="证书类型">{{ currentCertificate.cert_type_name }}</el-descriptions-item>
        <el-descriptions-item label="颁发机构">{{ currentCertificate.issuing_authority }}</el-descriptions-item>
        <el-descriptions-item label="签发日期">{{ currentCertificate.issue_date }}</el-descriptions-item>
        <el-descriptions-item label="有效期至">{{ currentCertificate.expiry_date || '长期有效' }}</el-descriptions-item>
        <el-descriptions-item label="状态" :span="2">
          <el-tag :type="getStatusType(currentCertificate)">{{ getStatusText(currentCertificate) }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <div v-if="currentCertificate?.id" class="cert-image">
        <img :src="getCertificateImage(currentCertificate.id)" alt="证书图片" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Upload, List, Document, User, UploadFilled
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { getEmployee, getEmployeeCompliance } from '@/api/common'
import { getTasks, completeTask } from '@/api/task'
import { getCertificates, ocrPreview as ocrPreviewApi, uploadCertificate, getCertificateImage } from '@/api/certificate'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const employeeInfo = ref(null)
const employeeCompliance = ref(null)
const myTasks = ref([])
const myCertificates = ref([])

const showUploadDialog = ref(false)
const uploadRef = ref(null)
const uploadFile = ref(null)
const uploadForm = reactive({
  manual_cert_name: '',
  manual_cert_number: '',
  manual_issuing_authority: '',
  manual_issue_date: '',
  manual_expiry_date: '',
})
const ocrPreview = ref(null)
const ocrLoading = ref(false)
const uploadLoading = ref(false)

const completeDialogVisible = ref(false)
const currentTask = ref(null)
const completeForm = reactive({ notes: '' })
const completeLoading = ref(false)

const certDetailVisible = ref(false)
const currentCertificate = ref(null)

const complianceRate = computed(() => {
  return Math.round((employeeCompliance.value?.compliance_rate || 0) * 100)
})

const pendingTasks = computed(() => {
  return myTasks.value.length
})

const departmentTagType = computed(() => {
  return employeeInfo.value?.department_name ? '' : 'info'
})

async function fetchEmployeeInfo() {
  if (!userStore.user?.employee_id) return
  
  try {
    loading.value = true
    employeeInfo.value = await getEmployee(userStore.user.employee_id)
    employeeCompliance.value = await getEmployeeCompliance(userStore.user.employee_id)
  } catch (error) {
    console.error('Failed to fetch employee info:', error)
  } finally {
    loading.value = false
  }
}

async function fetchMyTasks() {
  try {
    const result = await getTasks({ limit: 10 })
    myTasks.value = result.items || []
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  }
}

async function fetchMyCertificates() {
  try {
    const result = await getCertificates({ limit: 5 })
    myCertificates.value = result.items || []
  } catch (error) {
    console.error('Failed to fetch certificates:', error)
  }
}

function handleFileChange(file) {
  uploadFile.value = file.raw
}

async function handleOCRPreview() {
  if (!uploadFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  try {
    ocrLoading.value = true
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    ocrPreview.value = await ocrPreviewApi(formData)
    
    if (ocrPreview.value.confidence >= 0.7) {
      ElMessage.success('识别成功，请核对信息')
    }
  } catch (error) {
    console.error('OCR preview failed:', error)
    ElMessage.error('识别失败，请手动填写信息')
    ocrPreview.value = {
      cert_name: '',
      cert_number: '',
      issuing_authority: '',
      issue_date: null,
      expiry_date: null,
      confidence: 0
    }
  } finally {
    ocrLoading.value = false
  }
}

async function handleUploadSubmit() {
  if (!uploadFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  
  try {
    uploadLoading.value = true
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    formData.append('employee_id', userStore.user.employee_id)
    
    if (!ocrPreview.value?.cert_name && uploadForm.manual_cert_name) {
      formData.append('manual_cert_name', uploadForm.manual_cert_name)
    }
    if (!ocrPreview.value?.cert_number && uploadForm.manual_cert_number) {
      formData.append('manual_cert_number', uploadForm.manual_cert_number)
    }
    if (!ocrPreview.value?.issuing_authority && uploadForm.manual_issuing_authority) {
      formData.append('manual_issuing_authority', uploadForm.manual_issuing_authority)
    }
    if (uploadForm.manual_issue_date) {
      formData.append('manual_issue_date', uploadForm.manual_issue_date)
    }
    if (uploadForm.manual_expiry_date) {
      formData.append('manual_expiry_date', uploadForm.manual_expiry_date)
    }
    
    const result = await uploadCertificate(formData)
    
    if (result.success) {
      ElMessage.success('证书上传成功，等待审核')
      showUploadDialog.value = false
      fetchMyCertificates()
    } else {
      ElMessage.error(result.message || '上传失败')
    }
  } catch (error) {
    console.error('Upload failed:', error)
  } finally {
    uploadLoading.value = false
  }
}

function resetUploadForm() {
  uploadFile.value = null
  ocrPreview.value = null
  Object.assign(uploadForm, {
    manual_cert_name: '',
    manual_cert_number: '',
    manual_issuing_authority: '',
    manual_issue_date: '',
    manual_expiry_date: '',
  })
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

function handleCompleteTask(task) {
  currentTask.value = task
  completeForm.notes = ''
  completeDialogVisible.value = true
}

async function submitCompleteTask() {
  if (!completeForm.notes.trim()) {
    ElMessage.warning('请输入处理说明')
    return
  }
  
  try {
    completeLoading.value = true
    await completeTask(currentTask.value.id, completeForm.notes)
    ElMessage.success('任务已完成')
    completeDialogVisible.value = false
    fetchMyTasks()
  } catch (error) {
    console.error('Complete task failed:', error)
  } finally {
    completeLoading.value = false
  }
}

function viewCertificate(cert) {
  currentCertificate.value = cert
  certDetailVisible.value = true
}

function goToTasks() { router.push('/tasks') }
function goToCertificates() { router.push('/certificates') }
function goToProfile() { router.push('/profile') }

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

function isOverdue(task) {
  return task.days_overdue && task.days_overdue > 0
}

function getStatusType(row) {
  if (row.is_expired) return 'danger'
  if (row.days_to_expiry !== null && row.days_to_expiry <= 90) return 'warning'
  if (!row.verified) return 'info'
  return 'success'
}

function getStatusText(row) {
  if (row.is_expired) return '已过期'
  if (row.days_to_expiry !== null && row.days_to_expiry <= 90) return '即将到期'
  if (!row.verified) return '待审核'
  return '有效'
}

onMounted(() => {
  fetchEmployeeInfo()
  fetchMyTasks()
  fetchMyCertificates()
})
</script>

<style scoped>
.workbench {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-card {
  margin-bottom: 20px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.profile-info h3 {
  margin: 0 0 4px;
  font-size: 20px;
}

.profile-info p {
  margin: 0 0 8px;
  color: #909399;
}

.profile-stats {
  display: flex;
  justify-content: space-around;
  text-align: center;
}

.stat-num {
  font-size: 24px;
  font-weight: bold;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.text-primary { color: #409eff; }
.text-success { color: #67c23a; }
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; }

.quick-actions {
  margin-bottom: 20px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  border-radius: 8px;
  background: #f5f7fa;
  cursor: pointer;
  transition: all 0.3s;
}

.action-item:hover {
  background: #ecf5ff;
  transform: translateY(-2px);
}

.action-item span {
  margin-top: 8px;
  font-size: 14px;
  color: #606266;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ocr-preview {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}

.cert-image {
  margin-top: 16px;
  text-align: center;
}

.cert-image img {
  max-width: 100%;
  max-height: 400px;
  border-radius: 8px;
  border: 1px solid #eee;
}
</style>
