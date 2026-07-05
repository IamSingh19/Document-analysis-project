'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'

export default function Home() {
  const router = useRouter()
  const { isAuthenticated, token } = useAuthStore()

  useEffect(() => {
    // If authenticated, go to dashboard
    if (isAuthenticated || token) {
      router.replace('/dashboard')
    } else {
      // Otherwise go to login
      router.replace('/auth/login')
    }
  }, [isAuthenticated, token, router])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 mb-4">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
        <p className="text-white text-lg font-medium">Loading...</p>
      </div>
    </div>
  )
}
