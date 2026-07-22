/**
 * API client configuration.
 * Centralizes base URL and default headers for all HTTP requests.
 * Extend this in Phase 2+ when auth tokens are needed.
 */
import axios, { type InternalAxiosRequestConfig } from 'axios'
import type { ApiResponse, AuthTokens } from '@/types'
import { clearStoredTokens, getStoredTokens, setStoredTokens } from '@/utils/tokenStorage'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

let refreshPromise: Promise<AuthTokens | null> | null = null

async function refreshTokens(): Promise<AuthTokens | null> {
  const tokens = getStoredTokens()
  if (!tokens) return null

  try {
    const response = await refreshClient.post<ApiResponse<AuthTokens>>('/auth/refresh', {
      refresh_token: tokens.refresh_token,
    })
    setStoredTokens(response.data.data)
    return response.data.data
  } catch {
    clearStoredTokens()
    return null
  }
}

apiClient.interceptors.request.use((config) => {
  const accessToken = getStoredTokens()?.access_token
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error) || !error.response || !error.config) {
      return Promise.reject(error)
    }

    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const isTokenLifecycleRequest = [
      '/auth/login',
      '/auth/register',
      '/auth/refresh',
      '/auth/logout',
    ].some((path) => originalRequest.url?.includes(path))
    if (error.response.status !== 401 || originalRequest._retry || isTokenLifecycleRequest) {
      return Promise.reject(error)
    }

    originalRequest._retry = true
    refreshPromise ??= refreshTokens().finally(() => {
      refreshPromise = null
    })
    const newTokens = await refreshPromise
    if (!newTokens) {
      return Promise.reject(error)
    }

    originalRequest.headers.Authorization = `Bearer ${newTokens.access_token}`
    return apiClient(originalRequest)
  }
)

export default apiClient
