import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, logout, getCurrentUser } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isManager = computed(() => ['admin', 'manager'].includes(user.value?.role))
  const isEmployee = computed(() => user.value?.role === 'employee')

  async function loginUser(credentials) {
    const response = await login(credentials)
    token.value = response.access_token
    user.value = response.user
    localStorage.setItem('token', response.access_token)
    localStorage.setItem('user', JSON.stringify(response.user))
    return response
  }

  async function fetchCurrentUser() {
    if (!token.value) return null
    try {
      const response = await getCurrentUser()
      user.value = response
      localStorage.setItem('user', JSON.stringify(response))
      return response
    } catch (error) {
      logoutUser()
      throw error
    }
  }

  function logoutUser() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    try {
      logout()
    } catch (e) {
      console.log('Logout API error:', e)
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    isManager,
    isEmployee,
    loginUser,
    fetchCurrentUser,
    logoutUser
  }
})
