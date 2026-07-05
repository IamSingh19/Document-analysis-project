'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { documentsAPI, workspacesAPI } from '@/lib/api'
import { useAuthStore } from '@/lib/store'
import { FileUp, Clock, CheckCircle } from 'lucide-react'

export default function DashboardPage() {
  const { user } = useAuthStore()
  const [workspaceId, setWorkspaceId] = useState<number | null>(null)

  // Fetch user's workspace on mount
  useEffect(() => {
    const fetchWorkspace = async () => {
      try {
        const response = await workspacesAPI.list(0, 100)
        const workspaces = response.data as any[]
        if (workspaces.length > 0) {
          setWorkspaceId(workspaces[0].id)
        }
      } catch (error) {
        console.error('Failed to fetch workspace:', error)
      }
    }
    if (user) {
      fetchWorkspace()
    }
  }, [user])

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', workspaceId],
    queryFn: () => documentsAPI.list(workspaceId!),
    enabled: workspaceId !== null,
    refetchInterval: 5000, // Refetch every 5 seconds for real-time updates
    refetchIntervalInBackground: true, // Continue refetching even when tab is not active
  })

  const docs = documents?.data || []
  const stats = [
    { label: 'Total Documents', value: docs.length, icon: FileUp },
    { label: 'Processing', value: docs.filter((d: any) => d.status === 'processing').length, icon: Clock },
    { label: 'Completed', value: docs.filter((d: any) => d.status === 'completed').length, icon: CheckCircle },
  ]

  // Show loading state while fetching workspace
  if (workspaceId === null || isLoading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-slate-400">Welcome back! Here's your workspace overview.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {stats.map(({ label, value, icon: Icon }) => (
          <div key={label} className="glass p-6 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">{label}</p>
                <p className="text-3xl font-bold mt-2">{value}</p>
              </div>
              <Icon className="w-10 h-10 text-blue-500 opacity-20" />
            </div>
          </div>
        ))}
      </div>

      <div className="glass p-6 rounded-xl">
        <h2 className="text-xl font-bold mb-4">Recent Documents</h2>
        <div className="space-y-3">
          {docs.slice(0, 5).map((doc: any) => (
            <div
              key={doc.id}
              className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg"
            >
              <div>
                <p className="font-medium">{doc.title}</p>
                <p className="text-sm text-slate-400">{doc.file_type.toUpperCase()}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                doc.status === 'completed' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'
              }`}>
                {doc.status}
              </span>
            </div>
          ))}
          {docs.length === 0 && (
            <p className="text-slate-400 text-center py-8">No documents yet. Upload one to get started.</p>
          )}
        </div>
      </div>
    </div>
  )
}
