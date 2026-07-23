import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const permissions = ref<string[]>([])
  const roles = ref<string[]>([])

  const isLoggedIn = ref(!!token.value)

  async function login(username: string, password: string) {
    const res = await api.post('/auth/login', { username, password })
    const data = res.data
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
    permissions.value = data.user.permissions || []
    roles.value = data.user.roles || []
    isLoggedIn.value = true

    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)

    return data
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    permissions.value = []
    roles.value = []
    isLoggedIn.value = false
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function hasRole(role: string): boolean {
    return roles.value.includes(role)
  }

  function hasPermission(perm: string): boolean {
    return permissions.value.includes(perm)
  }

  return { user, token, refreshToken, permissions, roles, isLoggedIn, login, logout, hasRole, hasPermission }
})
