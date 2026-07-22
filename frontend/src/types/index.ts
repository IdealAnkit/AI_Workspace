/**
 * Global application types.
 * Add shared TypeScript interfaces and types here.
 * Feature-specific types should live in their respective feature folders.
 */

export interface ApiResponse<T> {
  data: T
  message: string
  success: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export type UserRole = 'admin' | 'user'

export interface AuthUser {
  id: string
  email: string
  username: string
  full_name: string
  role: UserRole
  is_active: boolean
  is_verified: boolean
  created_at: string
  updated_at: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
}

export interface AuthResponse {
  tokens: AuthTokens
  user: AuthUser
}

export interface LoginCredentials {
  email: string
  password: string
}
