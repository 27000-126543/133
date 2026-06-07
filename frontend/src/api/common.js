import request from '@/utils/request'

export function getDashboardStats() {
  return request({
    url: '/statistics/dashboard',
    method: 'get'
  })
}

export function getMonthlyReports(params) {
  return request({
    url: '/reports/monthly',
    method: 'get',
    params
  })
}

export function generateMonthlyReport() {
  return request({
    url: '/reports/monthly/generate',
    method: 'post'
  })
}

export function downloadReport(reportType, fileName) {
  return request({
    url: `/reports/download/${reportType}/${fileName}`,
    method: 'get',
    responseType: 'blob'
  })
}

export function getTrainingPlans(params) {
  return request({
    url: '/training/plans',
    method: 'get',
    params
  })
}

export function getTrainingCourses() {
  return request({
    url: '/training/courses',
    method: 'get'
  })
}

export function getTrainingNeeds() {
  return request({
    url: '/training/needs',
    method: 'get'
  })
}

export function generateTrainingPlans() {
  return request({
    url: '/training/generate-plans',
    method: 'post'
  })
}

export function getAuditLogs(params) {
  return request({
    url: '/audit-logs',
    method: 'get',
    params
  })
}

export function getEmployees(params) {
  return request({
    url: '/employees/',
    method: 'get',
    params
  })
}

export function getEmployee(empId) {
  return request({
    url: `/employees/${empId}`,
    method: 'get'
  })
}

export function createEmployee(data) {
  return request({
    url: '/employees/',
    method: 'post',
    data
  })
}

export function updateEmployee(empId, data) {
  return request({
    url: `/employees/${empId}`,
    method: 'put',
    data
  })
}

export function getDepartments() {
  return request({
    url: '/employees/departments',
    method: 'get'
  })
}

export function getEmployeeCompliance(empId) {
  return request({
    url: `/employees/${empId}/compliance`,
    method: 'get'
  })
}
