'use client'

import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { documentsAPI, workspacesAPI } from '@/lib/api'
import { useAuthStore } from '@/lib/store'
import { FileUp, Search, Filter, Trash2, Eye } from 'lucide-react'

export default function DocumentsPage() {
  const { user } = useAuthStore()
  const [workspaceId, setWorkspaceId] = useState<number | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedFileType, setSelectedFileType] = useState('all')
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [showFilters, setShowFilters] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  const { data: docs, isLoading, refetch } = useQuery({
    queryKey: ['documents', workspaceId],
    queryFn: () => documentsAPI.list(workspaceId!),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 1,
    enabled: workspaceId !== null, // Only fetch when workspace is loaded
    refetchInterval: 5000, // Refetch every 5 seconds for real-time updates
    refetchIntervalInBackground: true, // Continue refetching even when tab is not active
  })

  const documents = docs?.data || []
  const filtered = documents.filter((doc: any) => {
    const matchesSearch = doc.title.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesType = selectedFileType === 'all' || doc.file_type === selectedFileType
    const matchesStatus = selectedStatus === 'all' || doc.status === selectedStatus
    return matchesSearch && matchesType && matchesStatus
  })

  const fileTypes = ['all', ...new Set(documents.map((d: any) => d.file_type))]
  const statuses = ['all', ...new Set(documents.map((d: any) => d.status))]

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) {
      console.log('No file selected')
      return
    }

    if (!workspaceId) {
      alert('Workspace not loaded. Please wait and try again.')
      return
    }

    try {
      const response = await documentsAPI.upload(file, workspaceId)
      console.log('Upload successful:', response.data)
      alert(`✓ ${file.name} uploaded successfully!`)
      refetch()
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (error) {
      console.error('Upload failed:', error)
      alert('Upload failed. Check console for details.')
    }
  }

  const handleDelete = async (docId: number, docTitle: string) => {
    if (confirm(`Delete "${docTitle}"?`)) {
      try {
        await documentsAPI.delete(docId)
        alert('Document deleted')
        refetch()
      } catch (error) {
        alert('Delete failed')
      }
    }
  }

  const handleView = (doc: any) => {
    alert(`Viewing: ${doc.title}\nType: ${doc.file_type}\nSize: ${(doc.file_size / 1024 / 1024).toFixed(2)} MB\nStatus: ${doc.status}`)
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Documents</h1>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            hidden
            onChange={handleUpload}
            accept=".pdf,.docx,.pptx,.txt,.csv,.md"
          />
          <button 
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition"
          >
            <FileUp className="w-4 h-4" />
            Upload
          </button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="space-y-3">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2 focus:border-blue-500 outline-none"
            />
          </div>
          <button 
            onClick={() => setShowFilters(!showFilters)}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg flex items-center gap-2"
          >
            <Filter className="w-4 h-4" />
            Filter
          </button>
        </div>

        {/* Filter Options */}
        {showFilters && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 space-y-3">
            <div>
              <label className="text-sm font-medium text-slate-300">File Type</label>
              <div className="flex gap-2 mt-2 flex-wrap">
                {fileTypes.map(type => (
                  <button
                    key={type}
                    onClick={() => setSelectedFileType(type)}
                    className={`px-3 py-1 rounded-lg text-sm transition ${
                      selectedFileType === type
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-700 hover:bg-slate-600'
                    }`}
                  >
                    {type === 'all' ? 'All Types' : type.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-300">Status</label>
              <div className="flex gap-2 mt-2 flex-wrap">
                {statuses.map(status => (
                  <button
                    key={status}
                    onClick={() => setSelectedStatus(status)}
                    className={`px-3 py-1 rounded-lg text-sm transition ${
                      selectedStatus === status
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-700 hover:bg-slate-600'
                    }`}
                  >
                    {status === 'all' ? 'All Status' : status.charAt(0).toUpperCase() + status.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="glass rounded-xl overflow-hidden">
        <div className="grid grid-cols-1 divide-y divide-slate-800">
          {isLoading ? (
            [...Array(5)].map((_, i) => (
              <div key={i} className="p-4 animate-pulse">
                <div className="h-4 bg-slate-700 rounded w-1/4 mb-2" />
                <div className="h-3 bg-slate-800 rounded w-1/3" />
              </div>
            ))
          ) : filtered.length === 0 ? (
            <div className="p-12 text-center text-slate-400">
              <FileUp className="w-12 h-12 mx-auto opacity-20 mb-4" />
              <p>No documents match your filters. Upload one to get started.</p>
            </div>
          ) : (
            filtered.map((doc: any) => (
              <div key={doc.id} className="p-4 hover:bg-slate-800/50 transition flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="font-medium">{doc.title}</h3>
                  <div className="flex gap-4 text-sm text-slate-400 mt-1">
                    <span>{doc.file_type.toUpperCase()}</span>
                    <span>{doc.chunk_count} chunks</span>
                    <span>{(doc.file_size / 1024 / 1024).toFixed(2)} MB</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    doc.status === 'completed' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'
                  }`}>
                    {doc.status}
                  </span>
                  <button 
                    onClick={() => handleView(doc)}
                    className="p-2 hover:bg-slate-700 rounded-lg transition"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={() => handleDelete(doc.id, doc.title)}
                    className="p-2 hover:bg-slate-700 rounded-lg transition"
                  >
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
