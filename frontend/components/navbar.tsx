'use client'

import { useAuthStore } from '@/lib/store'
import { Bell, Settings, LogOut, Search, Upload } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export function Navbar() {
  const { user, logout } = useAuthStore()
  const router = useRouter()

  return (
    <nav className="h-16 border-b border-slate-800 glass flex items-center justify-between px-6">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative hidden md:flex items-center gap-2 max-w-md w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search documents..."
            className="w-full bg-slate-800/50 text-sm rounded-lg pl-10 pr-4 py-2 border border-slate-700 focus:border-blue-500 outline-none"
          />
        </div>
      </div>

      <div className="flex items-center gap-6">
        <button 
          onClick={() => router.push('/documents')}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition"
        >
          <Upload className="w-4 h-4" />
          Upload
        </button>

        <button 
          onClick={() => alert('No new notifications')}
          className="relative p-2 hover:bg-slate-800 rounded-lg transition"
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        <Link href="/settings" className="p-2 hover:bg-slate-800 rounded-lg transition">
          <Settings className="w-5 h-5" />
        </Link>

        <div className="flex items-center gap-3 pl-6 border-l border-slate-800">
          <div className="text-right">
            <p className="text-sm font-medium">{user?.username || 'Guest'}</p>
            <p className="text-xs text-slate-400">{user?.role || 'user'}</p>
          </div>
          <button
            onClick={() => {
              logout()
              router.push('/auth/login')
            }}
            className="p-2 hover:bg-slate-800 rounded-lg transition"
            title="Logout"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </div>
    </nav>
  )
}
