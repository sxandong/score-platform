import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'
import type { ApiResponse } from '@/types/api'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    const data = response.data as ApiResponse
    if (response.config.responseType === 'blob') return response
    if (data.code !== 200) {
      if (data.code === 401 && !response.config.skipAuthRedirect) {
        const authStore = useAuthStore()
        authStore.logout()
        router.push('/login')
      }
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    return data
  },
  async (error) => {
    const config = error.config || {}
    const skipAuthRedirect = config.skipAuthRedirect || false

    if (error.response?.status === 401 && !skipAuthRedirect) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const res = await axios.post<unknown, ApiResponse<{ access_token: string; refresh_token: string }>>(
            '/api/auth/refresh', { refresh_token: refreshToken }
          )
          if (res.code === 200) {
            const { access_token, refresh_token } = res.data
            localStorage.setItem('access_token', access_token)
            localStorage.setItem('refresh_token', refresh_token)
            error.config.headers.Authorization = `Bearer ${access_token}`
            return api.request(error.config)
          }
        } catch {
          // refresh failed, redirect to login
        }
      }
      const authStore = useAuthStore()
      authStore.logout()
      router.push('/login')
    }

    const errorMessage = error.response?.data?.message || error.message || '请求失败'
    return Promise.reject(new Error(errorMessage))
  },
)

export default api