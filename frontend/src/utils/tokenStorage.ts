/** Browser storage helpers for the current authentication token pair. */
import type { AuthTokens } from '@/types'

const TOKEN_STORAGE_KEY = 'ai-workspace.auth.tokens'

export function getStoredTokens(): AuthTokens | null {
  const value = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (!value) return null

  try {
    return JSON.parse(value) as AuthTokens
  } catch {
    clearStoredTokens()
    return null
  }
}

export function setStoredTokens(tokens: AuthTokens): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens))
}

export function clearStoredTokens(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}
