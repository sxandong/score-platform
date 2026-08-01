import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'
import type { ApiResponse, UserInfo, LoginResponse } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const token = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const permissions = ref<string[]>([])
  const roles = ref<string[]>([])

  const isLoggedIn = ref(!!token.value)
  const mustChangePassword = computed(() => user.value?.must_change_password ?? false)

  async function login(username: string, password: string): Promise<LoginResponse> {
    const res = await api.post<unknown, ApiResponse<LoginResponse>>(
      '/auth/login',
      { username, password },
      { skipAuthRedirect: true }
    )
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

  async function fetchUser(): Promise<void> {
    if (!token.value) return
    try {
      const res = await api.get<unknown, ApiResponse<UserInfo>>('/auth/me')
      user.value = res.data
      permissions.value = res.data.permissions || []
      roles.value = res.data.roles || []
      isLoggedIn.value = true
    } catch {
      logout()
    }
  }

  async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword })
    if (user.value) {
      user.value.must_change_password = false
    }
  }

  function logout(): void {
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

  return {
    user, token, refreshToken, permissions, roles, isLoggedIn, mustChangePassword,
    login, fetchUser, changePassword, logout, hasRole, hasPermission,
  }
})