<template>
  <div class="page-container">
    <el-card class="card-shadow">
      <template #header>
        <div class="card-header">
          <span>证书管理</span>
          <div class="header-actions">
            <el-button v-if="userStore.isManager" type="primary" @click="showUploadDialog = true">
              <el-icon><Plus /></el-icon>上传证书
            </el-button>
            <el-button @click="handleExport">
              <el-icon><Download /></el-icon>导出
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="search-form">
        <el-form :inline="true" :model="searchForm">
          <el-form-item label="员工">
            <el-input v-model="searchForm.employee_name" placeholder="员工姓名" clearable style="width: 150px;" />
          </el-form-item>
          <el-form-item label="工号">
            <el-input v-model="searchForm.employee_no" placeholder="工号" clearable style="width: 150px;" />
          </el-form-item>
          <el-form-item label="证书类型">
            <el-select v-model="searchForm.cert_type_id" placeholder="全部" clearable style="width: 180px;">
              <el-option
                v-for="type in certTypes"
                :key="type.id"
                :label="type.name"
                :value="type.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 120px;">
              <el-option label="有效" value="valid" />
              <el-option label="待审核" value="unverified" />
              <el-option label="已过期" value="expired" />
              <el-option label="已替换" value="replaced" />
            </el-select>
          </el-form-item>
          <el-form-item label="快速筛选">
            <el-radio-group v-model="quickFilter">
              <el-radio-button value="all">全部</el-radio-button>
              <el-radio-button value="expiring">即将到期</el-radio-button>
              <el-radio-button value="expired">已过期</el-radio-button>
              <el-radio-button value="unverified">待审核</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="searchCertificates">
              <el-icon><Search /></el-icon>查询
            </el-button>
            <el-button @click="resetSearch">
              <el-icon><Refresh /></el-icon>重置
            </el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <el-table :data="certificates" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="employee_name" label="员工" width="100" />
        <el-table-column prop="employee_no" label="工号" width="100" />
        <el-table-column prop="department_name" label="部门" width="120" />
        <el-table-column prop="cert_name" label="证书名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="cert_type_name" label="类型" width="120" />
        <el-table-column prop="cert_number" label="证书编号" width="160" />
        <el-table-column prop="issuing_authority" label="颁发机构" min-width="150" show-overflow-tooltip />
        <el-table-column prop="issue_date" label="签发日期" width="110" />
        <el-table-column prop="expiry_date" label="有效期至" width="110" />
        <el-table-column prop="days_to_expiry" label="剩余天数" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.days_to_expiry !== null" :type="getExpiryTagType(row)">
              {{ row.days_to_expiry }} 天
            </el-tag>
            <span v-else>长期</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row)">
              {{ getStatusText(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewCertificate(row)">
              查看
            </el-button>
            <el-button
              v-if="userStore.isManager && !row.verified"
              type="success"
              size="small"
              link
              @click="handleVerify(row, true)"
            >
              通过
            </el-button>
            <el-button
              v-if="userStore.isManager && !row.verified"
              type="danger"
              size="small"
              link
              @click="handleVerify(row, false)"
            >
              驳回
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
          @size-change="searchCertificates"
          @current-change="searchCertificates"
        />
      </div>
    </el-card>
    
    <el-dialog v-model="showUploadDialog" title="上传证书" width="600px" @close="resetUploadForm">
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="员工" required>
          <el-select v-model="uploadForm.employee_id" placeholder="请选择员工" filterable style="width: 100%;">
            <el-option
              v-for="emp in employees"
              :key="emp.id"
              :label="`${emp.name} (${emp.employee_no})`"
              :value="emp.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="证书类型" required>
          <el-select v-model="uploadForm.cert_type_id" placeholder="请选择证书类型" filterable style="width: 100%;">
            <el-option
              v-for="type in certTypes"
              :key="type.id"
              :label="type.name"
              :value="type.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="证书图片" required>
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
              <div class="el-upload__tip">支持 jpg/png/bmp 格式，大小不超过 10MB</div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item v-if="ocrPreview" label="OCR识别结果">
          <div class="ocr-preview">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="证书名称">{{ ocrPreview.cert_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="证书编号">{{ ocrPreview.cert_number || '-' }}</el-descriptions-item>
              <el-descriptions-item label="颁发机构">{{ ocrPreview.issuing_authority || '-' }}</el-descriptions-item>
              <el-descriptions-item label="签发日期">{{ ocrPreview.issue_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="有效期至">{{ ocrPreview.expiry_date || '长期' }}</el-descriptions-item>
            </el-descriptions>
            <div class="confidence-info">
              <span>识别置信度: </span>
              <el-progress
                :percentage="Math.round((ocrPreview.confidence || 0) * 100)"
                :color="ocrPreview.confidence >= 0.7 ? '#67c23a' : '#e6a23c'"
                :stroke-width="12"
              />
            </div>
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="handleOCRPreview" :loading="ocrLoading" v-if="uploadFile && !ocrPreview">
          识别信息
        </el-button>
        <el-button type="success" @click="handleUploadSubmit" :loading="uploadLoading" v-else>
          提交
        </el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="detailVisible" title="证书详情" width="700px">
      <el-descriptions :column="2" border v-if="currentCert">
        <el-descriptions-item label="员工姓名">{{ currentCert.employee_name }}</el-descriptions-item>
        <el-descriptions-item label="工号">{{ currentCert.employee_no }}</el-descriptions-item>
        <el-descriptions-item label="部门">{{ currentCert.department_name }}</el-descriptions-item>
        <el-descriptions-item label="证书类型">{{ currentCert.cert_type_name }}</el-descriptions-item>
        <el-descriptions-item label="证书名称" :span="2">{{ currentCert.cert_name }}</el-descriptions-item>
        <el-descriptions-item label="证书编号">{{ currentCert.cert_number }}</el-descriptions-item>
        <el-descriptions-item label="颁发机构" :span="2">{{ currentCert.issuing_authority }}</el-descriptions-item>
        <el-descriptions-item label="签发日期">{{ currentCert.issue_date }}</el-descriptions-item>
        <el-descriptions-item label="有效期至">{{ currentCert.expiry_date || '长期有效' }}</el-descriptions-item>
        <el-descriptions-item label="状态" :span="2">
          <el-tag :type="getStatusType(currentCert)">{{ getStatusText(currentCert) }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      
      <div v-if="currentCert?.id" class="cert-image-preview">
        <h4>证书图片</h4>
        <img :src="getCertificateImage(currentCert.id)" alt="证书图片" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Download, Search, Refresh, UploadFilled
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  getCertificates, getCertificateTypes, verifyCertificate,
  uploadCertificate, ocrPreview as ocrPreviewApi, getCertificateImage, exportCertificates
} from '@/api/certificate'
import { getEmployees } from '@/api/common'
import download from 'downloadjs'

const userStore = useUserStore()

const loading = ref(false)
const certificates = ref([])
const certTypes = ref([])
const employees = ref([])

const searchForm = reactive({
  employee_name: '',
  employee_no: '',
  cert_type_id: null,
  status: '',
})

const quickFilter = ref('all')

const pagination = reactive({
  page: 1,
  limit: 10,
  total: 0,
})

const showUploadDialog = ref(false)
const uploadRef = ref(null)
const uploadFile = ref(null)
const uploadForm = reactive({
  employee_id: null,
  cert_type_id: null,
})
const ocrPreview = ref(null)
const ocrLoading = ref(false)
const uploadLoading = ref(false)

const detailVisible = ref(false)
const currentCert = ref(null)

watch(quickFilter, () => {
  searchCertificates()
})

async function fetchCertTypes() {
  try {
    certTypes.value = await getCertificateTypes()
  } catch (error) {
    console.error('Failed to fetch cert types:', error)
  }
}

async function fetchEmployees() {
  try {
    const result = await getEmployees({ limit: 1000 })
    employees.value = result.items || []
  } catch (error) {
    console.error('Failed to fetch employees:', error)
  }
}

async function searchCertificates() {
  try {
    loading.value = true
    
    const params = {
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit,
    }
    
    if (searchForm.employee_name) {
      params.employee_name = searchForm.employee_name
    }
    if (searchForm.employee_no) {
      params.employee_no = searchForm.employee_no
    }
    if (searchForm.cert_type_id) {
      params.cert_type_id = searchForm.cert_type_id
    }
    
    if (quickFilter.value === 'expiring') {
      params.only_expiring = true
    } else if (quickFilter.value === 'expired') {
      params.only_expired = true
    } else if (quickFilter.value === 'unverified') {
      params.only_unverified = true
    } else if (searchForm.status) {
      if (searchForm.status === 'unverified') {
        params.only_unverified = true
      } else {
        params.status = searchForm.status
      }
    }
    
    const result = await getCertificates(params)
    certificates.value = result.items || []
    pagination.total = result.total || 0
  } catch (error) {
    console.error('Search failed:', error)
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  Object.assign(searchForm, {
    employee_name: '',
    employee_no: '',
    cert_type_id: null,
    status: '',
  })
  quickFilter.value = 'all'
  pagination.page = 1
  searchCertificates()
}

async function handleExport() {
  try {
    const blob = await exportCertificates()
    download(blob, `certificates_${Date.now()}.xlsx`)
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Export failed:', error)
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
  } catch (error) {
    console.error('OCR preview failed:', error)
    ocrPreview.value = { confidence: 0 }
  } finally {
    ocrLoading.value = false
  }
}

async function handleUploadSubmit() {
  if (!uploadFile.value || !uploadForm.employee_id || !uploadForm.cert_type_id) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  try {
    uploadLoading.value = true
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    formData.append('employee_id', uploadForm.employee_id)
    formData.append('cert_type_id', uploadForm.cert_type_id)
    
    if (ocrPreview.value) {
      if (ocrPreview.value.cert_name) {
        formData.append('manual_cert_name', ocrPreview.value.cert_name)
      }
      if (ocrPreview.value.cert_number) {
        formData.append('manual_cert_number', ocrPreview.value.cert_number)
      }
      if (ocrPreview.value.issuing_authority) {
        formData.append('manual_issuing_authority', ocrPreview.value.issuing_authority)
      }
      if (ocrPreview.value.issue_date) {
        formData.append('manual_issue_date', ocrPreview.value.issue_date)
      }
      if (ocrPreview.value.expiry_date) {
        formData.append('manual_expiry_date', ocrPreview.value.expiry_date)
      }
    }
    
    const result = await uploadCertificate(formData)
    
    if (result.success) {
      ElMessage.success('证书上传成功')
      showUploadDialog.value = false
      searchCertificates()
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
  uploadForm.employee_id = null
  uploadForm.cert_type_id = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

function viewCertificate(cert) {
  currentCert.value = cert
  detailVisible.value = true
}

async function handleVerify(cert, verified) {
  const action = verified ? '通过' : '驳回'
  
  try {
    await ElMessageBox.confirm(
      `确定要${action}该证书吗？`,
      '提示',
      { type: verified ? 'success' : 'warning' }
    )
    
    const notes = verified ? '审核通过' : '审核不通过'
    await verifyCertificate(cert.id, verified, notes)
    
    ElMessage.success(`证书已${action}`)
    searchCertificates()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Verify failed:', error)
    }
  }
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
  if (row.status === 'replaced') return '已替换'
  return '有效'
}

function getExpiryTagType(row) {
  if (row.days_to_expiry <= 30) return 'danger'
  if (row.days_to_expiry <= 90) return 'warning'
  return 'success'
}

onMounted(() => {
  fetchCertTypes()
  fetchEmployees()
  searchCertificates()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.search-form {
  margin-bottom: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.ocr-preview {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}

.confidence-info {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.cert-image-preview {
  margin-top: 20px;
  text-align: center;
}

.cert-image-preview img {
  max-width: 100%;
  max-height: 500px;
  border-radius: 8px;
  border: 1px solid #eee;
}
</style>
