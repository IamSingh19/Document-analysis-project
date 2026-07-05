'use client'

import { ReactNode, useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from './store'

interface ProtectedRouteProps {
  children: ReactNode
}

/**
 * ProtectedRoute Component
 * 
 * Wraps pages that require authentication
 * - Redirects to login if not authenticated
 * - Verifies token on mount
 * - Shows loading state while verifying
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, token, loading, verifyToken, logout } = useAuthStore()
  const [isVerified, setIsVerified] = useState(false)
  const [isHydrated, setIsHydrated] = useState(false)

  // Wait for Zustand store to hydrate from localStorage
  useEffect(() => {
    setIsHydrated(true)
  }, [])

  useEffect(() => {
    // Don't check until store is hydrated
    if (!isHydrated) return

    const checkAuth = async () => {
      // If on auth pages, allow access
      if (pathname?.includes('/auth')) {
        setIsVerified(true)
        return
      }

      // If no token, redirect to login
      if (!token) {
        router.push('/auth/login')
        return
      }

      // Verify token is still valid
      const isValid = await verifyToken()
      
      if (!isValid) {
        logout()
        router.push('/auth/login')
        return
      }

      setIsVerified(true)
    }

    checkAuth()
  }, [token, pathname, router, verifyToken, logout, isHydrated])

  // Auth pages don't need verification
  if (pathname?.includes('/auth')) {
    return <>{children}</>
  }

  // Show loading while hydrating or verifying
  if (!isHydrated || loading || !isVerified) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 mb-4">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
          <p className="text-white text-lg font-medium">Verifying authentication...</p>
          <p className="text-slate-400 text-sm mt-2">Please wait</p>
        </div>
      </div>
    )
  }

  // Not authenticated, redirect to login
  if (!isAuthenticated) {
    router.push('/auth/login')
    return null
  }

  // Authenticated, render protected content
  return <>{children}</>
}

/**
 * Use in layout.tsx:
 * 
 * import { ProtectedRoute } from '@/lib/protected-route'
 * 
 * export default function RootLayout({ children }) {
 *   return (
 *     <ProtectedRoute>
 *       {children}
 *     </ProtectedRoute>
 *   )
 * }
 */
