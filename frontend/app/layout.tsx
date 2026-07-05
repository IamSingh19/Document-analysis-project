'use client'

import './globals.css'
import { ThemeProvider } from '@/lib/providers'
import { ProtectedRoute } from '@/lib/protected-route'
import { Navbar } from '@/components/navbar'
import { Sidebar } from '@/components/sidebar'
import { usePathname } from 'next/navigation'
import { useHydration } from '@/lib/hooks'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const isAuthPage = pathname?.includes('/auth')
  const isHydrated = useHydration()

  // Avoid hydration mismatch - wait for client-side hydration
  if (!isHydrated) {
    return (
      <html lang="en" suppressHydrationWarning>
        <head>
          <meta charSet="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
        </head>
        <body className="bg-slate-950 text-slate-100">
          <div className="flex items-center justify-center min-h-screen">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        </body>
      </html>
    )
  }

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="bg-slate-950 text-slate-100">
        <ThemeProvider>
          <ProtectedRoute>
            {isAuthPage ? (
              // Auth pages don't need layout
              children
            ) : (
              // Protected pages with layout
              <div className="flex h-screen">
                <Sidebar />
                <div className="flex-1 flex flex-col">
                  <Navbar />
                  <main className="flex-1 overflow-hidden">
                    {children}
                  </main>
                </div>
              </div>
            )}
          </ProtectedRoute>
        </ThemeProvider>
      </body>
    </html>
  )
}
