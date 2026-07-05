'use client'

import { documentsAPI } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import { FileUp, Clock, CheckCircle } from 'lucide-react'

export function Dashboard() {
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', 1],
    queryFn: () => documentsAPI.list(1),
  })

  const stats = [
    { label: 'Total Documents', value: documents?.data?.length || 0, icon: FileUp },
    { label: 'Processing', value: 2, icon: Clock },
    { label: 'Completed', value: 8, icon: CheckCircle },
  ]

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-slate-400">Welcome back! Here's your document overview.</p>
      </div>

      {/* Stats */}
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

      {/* Recent Documents */}
      <div className="glass p-6 rounded-xl">
        <h2 className="text-xl font-bold mb-4">Recent Documents</h2>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-slate-800/50 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {documents?.data?.slice(0, 5).map((doc: any) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition"
              >
                <div>
                  <p className="font-medium">{doc.title}</p>
                  <p className="text-sm text-slate-400">{doc.file_type.toUpperCase()}</p>
                </div>
                <div className="text-right">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    doc.status === 'completed' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'
                  }`}>
                    {doc.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
