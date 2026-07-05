'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  Search,
  BarChart3,
  Settings,
} from 'lucide-react'

const navigation = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Documents', href: '/documents', icon: FileText },
  { label: 'Chat', href: '/chat', icon: MessageSquare },
  { label: 'Search', href: '/search', icon: Search },
  { label: 'Analytics', href: '/analytics', icon: BarChart3 },
  { label: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 border-r border-slate-800 glass flex flex-col">
      <Link href="/" className="p-6 font-bold text-xl bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
        DocMind AI
      </Link>

      <nav className="flex-1 px-4 py-6 space-y-2">
        {navigation.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-4 py-2 rounded-lg transition ${
              pathname === href
                ? 'bg-slate-800 text-blue-400'
                : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
            }`}
          >
            <Icon className="w-5 h-5" />
            <span className="text-sm font-medium">{label}</span>
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-800 space-y-3">
        <div className="glass p-4 rounded-lg">
          <p className="text-xs text-slate-400 mb-2">Workspace</p>
          <p className="text-sm font-medium">Personal</p>
        </div>
      </div>
    </aside>
  )
}
