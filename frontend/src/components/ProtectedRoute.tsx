import { type ReactNode, useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuthStore } from '@/store/authStore'

interface ProtectedRouteProps {
  children: ReactNode
}

/** Restricts child routes to a restored, authenticated browser session. */
function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation()
  const { initialize, isAuthenticated, isInitializing } = useAuthStore()

  useEffect(() => {
    void initialize()
  }, [initialize])

  if (isInitializing) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-300">Loading…</div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <>{children}</>
}

export default ProtectedRoute
