import request from '@/utils/request'

export function getTasks(params) {
  return request({
    url: '/tasks/',
    method: 'get',
    params
  })
}

export function getTask(taskId) {
  return request({
    url: `/tasks/${taskId}`,
    method: 'get'
  })
}

export function completeTask(taskId, completionNotes) {
  return request({
    url: `/tasks/${taskId}/complete`,
    method: 'post',
    data: { completion_notes: completionNotes }
  })
}

export function approveTask(taskId, approvalNotes) {
  return request({
    url: `/tasks/${taskId}/approve`,
    method: 'post',
    data: { approval_notes: approvalNotes }
  })
}

export function rejectTask(taskId, rejectReason) {
  return request({
    url: `/tasks/${taskId}/reject`,
    method: 'post',
    data: { reject_reason: rejectReason }
  })
}

export function getTaskStatistics() {
  return request({
    url: '/tasks/statistics/summary',
    method: 'get'
  })
}

export function runDailyCheck() {
  return request({
    url: '/tasks/run-daily-check',
    method: 'post'
  })
}
