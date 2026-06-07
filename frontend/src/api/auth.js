import request from '@/utils/request'

export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

export function register(data) {
  return request({
    url: '/auth/register',
    method: 'post',
    data
  })
}

export function getCurrentUser() {
  return request({
    url: '/auth/me',
    method: 'get'
  })
}

export function changePassword(data) {
  return request({
    url: '/auth/change-password',
    method: 'post',
    data
  })
}

export function getUsers(params) {
  return request({
    url: '/auth/users',
    method: 'get',
    params
  })
}

export function toggleUserActive(userId, isActive) {
  return request({
    url: `/auth/users/${userId}/toggle-active`,
    method: 'patch',
    params: { is_active: isActive }
  })
}

export function logout() {
  return request({
    url: '/auth/logout',
    method: 'post'
  })
}
