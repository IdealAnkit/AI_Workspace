/** Zustand state for the currently authenticated browser session. */
import { create } from 'zustand'

import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
} from '@/services/authService'
import type { AuthUser, LoginCredentials } from '@/types'
import { clearStoredTokens, getStoredTokens } from '@/utils/tokenStorage'

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  isInitializing: boolean
  initialize: () => Promise<void>
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isInitializing: true,

  initialize: async () => {
    if (!getStoredTokens()) {
      set({ user: null, isAuthenticated: false, isInitializing: false })
      return
    }

    try {
      const user = await getCurrentUser()
      set({ user, isAuthenticated: true, isInitializing: false })
    } catch {
      clearStoredTokens()
      set({ user: null, isAuthenticated: false, isInitializing: false })
    }
  },

  login: async (credentials) => {
    const result = await loginRequest(credentials)
    set({ user: result.user, isAuthenticated: true, isInitializing: false })
  },

  logout: async () => {
    const refreshToken = getStoredTokens()?.refresh_token
    try {
      if (refreshToken) await logoutRequest(refreshToken)
    } finally {
      clearStoredTokens()
      set({ user: null, isAuthenticated: false, isInitializing: false })
    }
  },
}))
