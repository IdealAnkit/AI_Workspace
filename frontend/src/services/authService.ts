/** API calls belonging to the authentication feature. */
import apiClient from '@/services/apiClient'
import type { ApiResponse, AuthResponse, AuthTokens, AuthUser, LoginCredentials } from '@/types'
import { clearStoredTokens, setStoredTokens } from '@/utils/tokenStorage'

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  const response = await apiClient.post<ApiResponse<AuthResponse>>('/auth/login', credentials)
  setStoredTokens(response.data.data.tokens)
  return response.data.data
}

export async function getCurrentUser(): Promise<AuthUser> {
  const response = await apiClient.get<ApiResponse<AuthUser>>('/auth/me')
  return response.data.data
}

export async function logout(refreshToken: string): Promise<void> {
  try {
    await apiClient.post('/auth/logout', { refresh_token: refreshToken })
  } finally {
    clearStoredTokens()
  }
}

export function persistTokens(tokens: AuthTokens): void {
  setStoredTokens(tokens)
}
