'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, MessageCircle, Loader2, AlertCircle, Copy, Download, Check } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuthStore } from '@/lib/store'
import { chatAPI, workspacesAPI, documentsAPI } from '@/lib/api'
import Link from 'next/link'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ document_id: number; page: number; score?: number }>
  created_at: string
}

interface ChatSession {
  session_id: number
  workspace_id: number
  document_ids: number[]
  created_at: string
}

interface Document {
  id: number
  title: string
  file_type: string
  status: 'processing' | 'completed' | 'failed'
  chunk_count: number
  embedding_count: number
  file_size: number
  created_at: string
}

export default function ChatPage() {
  const { token, user } = useAuthStore()
  const [session, setSession] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDocs, setSelectedDocs] = useState<number[]>([])
  const [showDocSelector, setShowDocSelector] = useState(true)
  const [currentResponse, setCurrentResponse] = useState('')
  const [documents, setDocuments] = useState<Document[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [workspaceId, setWorkspaceId] = useState<number | null>(null)
  const messagesEnd = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
    }, 0)
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentResponse, scrollToBottom])

  // Load initial state on mount
  useEffect(() => {
    if (!user) return
    
    const initializeChat = async () => {
      try {
        // Get user's workspace
        const workspacesRes = await workspacesAPI.list(0, 100)
        const workspaces = workspacesRes.data as any[]
        
        if (workspaces.length === 0) {
          setError('No workspace found. Please contact support.')
          return
        }
        
        const wsId = workspaces[0].id
        setWorkspaceId(wsId)
        // Documents will be loaded by the useEffect hook
        setShowDocSelector(true)
      } catch (err) {
        console.error('Error initializing chat:', err)
      }
    }
    initializeChat()
  }, [user])

  const loadDocuments = async (wsId: number) => {
    try {
      setLoadingDocs(true)
      const docsRes = await documentsAPI.list(wsId, 0, 100)
      const docs = docsRes.data as Document[]
      setDocuments(docs.filter(d => d.status === 'completed'))
    } catch (err) {
      console.error('Error loading documents:', err)
    } finally {
      setLoadingDocs(false)
    }
  }

  // Set up auto-refresh for documents every 5 seconds
  useEffect(() => {
    if (!workspaceId) return
    
    // Initial load
    loadDocuments(workspaceId)
    
    // Set up interval for real-time updates
    const interval = setInterval(() => {
      loadDocuments(workspaceId)
    }, 5000)
    
    return () => clearInterval(interval)
  }, [workspaceId])

  const initializeSession = useCallback(async (docIds: number[]) => {
    try {
      if (!user || !workspaceId) return
      
      const newSession = await chatAPI.createSession(workspaceId, docIds)
      setSession(newSession.data as ChatSession)
      setMessages([])
      setShowDocSelector(false)
      setSelectedDocs(docIds)
    } catch (err: any) {
      console.error('Session initialization error:', err)
      setError(err.response?.data?.detail || 'Failed to initialize chat session')
    }
  }, [user, workspaceId])

  const handleSendMessage = async () => {
    if (!input.trim()) return
    if (!session) {
      setError('Creating session...')
      return
    }

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: input,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError(null)
    setCurrentResponse('')

    try {
      // Build query string with document IDs
      const queryParams = new URLSearchParams()
      queryParams.append('session_id', session.session_id.toString())
      queryParams.append('query', input)
      queryParams.append('stream', 'true')
      
      // Always send the document IDs from the session
      const docsToSend = selectedDocs.length > 0 ? selectedDocs : session.document_ids
      if (docsToSend && docsToSend.length > 0) {
        docsToSend.forEach(id => queryParams.append('document_ids', id.toString()))
      }

      // Stream the response using Server-Sent Events
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat/ask?${queryParams.toString()}`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Failed to get response: ${response.status} ${errorText}`)
      }

      setStreaming(true)
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullResponse = ''
      let sources: any[] = []

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))

                if (data.type === 'content') {
                  fullResponse += data.content
                  setCurrentResponse(fullResponse)
                } else if (data.type === 'complete') {
                  sources = data.sources || []
                } else if (data.type === 'error') {
                  setError(data.message)
                }
              } catch (e) {
                // Skip invalid JSON
              }
            }
          }
        }
      }

      setStreaming(false)

      // Add assistant message to chat
      if (fullResponse) {
        const assistantMessage: Message = {
          id: Date.now() + 1,
          role: 'assistant',
          content: fullResponse,
          sources: sources,
          created_at: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, assistantMessage])
      }

      setCurrentResponse('')
    } catch (err: any) {
      setError(err.message || 'Failed to get response')
      setStreaming(false)
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const exportChat = async () => {
    if (!session) return
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat/sessions/${session.session_id}/export?format=md`,
        {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )
      
      if (!response.ok) {
        throw new Error(`Failed to export: ${response.status}`)
      }
      
      // Get the filename from headers
      const contentDisposition = response.headers.get('content-disposition')
      let filename = `chat_export.md`
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      
      // Create blob and download
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      setError(null)
    } catch (err) {
      console.error('Export error:', err)
      setError('Failed to export chat')
    }
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <MessageCircle className="w-12 h-12 text-blue-500 mx-auto" />
          <p className="text-slate-400">Please log in to use chat</p>
          <Link href="/auth/login" className="text-blue-500 hover:text-blue-400">
            Go to login
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-950 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-800 px-6 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-lg font-semibold text-white">Document Chat</h1>
          <p className="text-xs text-slate-500 mt-1">
            {selectedDocs.length > 0
              ? `Chatting with ${selectedDocs.length} document(s)`
              : 'Select documents to chat'}
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={exportChat}
            className="flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && !streaming && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <MessageCircle className="w-16 h-16 text-slate-700 mb-4" />
            <h2 className="text-xl font-semibold text-slate-300 mb-2">
              Start a conversation
            </h2>
            <p className="text-slate-500 max-w-md">
              Upload documents and ask me anything about them. I'll search through the content
              and provide detailed, cited answers.
            </p>
            <div className="mt-6 space-y-2 text-sm text-slate-400">
              <p>💡 Try asking:</p>
              <ul className="space-y-1">
                <li>• Summarize the main points</li>
                <li>• What are the key findings?</li>
                <li>• Compare section X with section Y</li>
              </ul>
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map((msg, idx) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-2xl px-4 py-3 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-800 text-slate-100 border border-slate-700'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-1">
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                  {msg.role === 'assistant' && (
                    <button
                      onClick={() => copyToClipboard(msg.content)}
                      className="flex-shrink-0 p-1 text-slate-500 hover:text-slate-300"
                      title="Copy response"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-700">
                    <p className="text-xs font-medium text-slate-400 mb-2">Sources:</p>
                    <div className="space-y-1">
                      {msg.sources.map((src, i) => (
                        <div key={i} className="text-xs text-slate-500">
                          📄 Document {src.document_id}, Page {src.page}
                          {src.score && ` (${(src.score * 100).toFixed(0)}% match)`}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Streaming response */}
        {streaming && currentResponse && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start"
          >
            <div className="max-w-2xl px-4 py-3 rounded-lg bg-slate-800 text-slate-100 border border-slate-700">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{currentResponse}</p>
              <div className="flex gap-1 mt-2">
                {[...Array(3)].map((_, i) => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Loading spinner */}
        {loading && !currentResponse && (
          <div className="flex justify-start">
            <div className="px-4 py-3 rounded-lg bg-slate-800 text-slate-100">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Processing your question...</span>
              </div>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-center"
          >
            <div className="max-w-2xl w-full px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-red-400">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-red-500 hover:text-red-400 flex-shrink-0"
              >
                ✕
              </button>
            </div>
          </motion.div>
        )}

        <div ref={messagesEnd} />
      </div>

      {/* Input area */}
      <div className="border-t border-slate-800 p-6 bg-gradient-to-t from-slate-950 to-slate-950/50 backdrop-blur-sm">
        {selectedDocs.length === 0 && !showDocSelector && (
          <div className="mb-4 p-4 rounded-lg bg-slate-800/50 border border-slate-700">
            <p className="text-sm text-slate-400">
              No documents selected.{' '}
              <button
                onClick={() => setShowDocSelector(true)}
                className="text-blue-400 hover:text-blue-300"
              >
                Select documents
              </button>{' '}
              to start chatting.
            </p>
          </div>
        )}

        <div className="space-y-3">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSendMessage()
                }
              }}
              placeholder="Ask about your documents..."
              disabled={loading}
              className="flex-1 bg-slate-800/50 border border-slate-700 text-slate-100 placeholder-slate-600 rounded-lg px-4 py-3 focus:border-blue-500 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed transition"
            />
            <button
              onClick={handleSendMessage}
              disabled={loading || !input.trim()}
              className="px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-2 transition"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>

          {/* Quick suggestions */}
          {messages.length < 2 && selectedDocs.length > 0 && session && (
            <div className="flex flex-wrap gap-2">
              {['Summarize', 'Key points', 'Extract main ideas', 'Compare sections'].map(
                (suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="text-xs px-3 py-1.5 bg-slate-800/50 hover:bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-300 rounded-full transition"
                  >
                    {suggestion}
                  </button>
                )
              )}
            </div>
          )}

          {/* Document selector */}
          {showDocSelector && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-300">Select documents</label>
                <button
                  onClick={() => setShowDocSelector(false)}
                  className="text-xs text-slate-500 hover:text-slate-400"
                >
                  Hide
                </button>
              </div>
              
              {loadingDocs ? (
                <div className="flex items-center gap-2 py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-slate-500" />
                  <span className="text-xs text-slate-500">Loading documents...</span>
                </div>
              ) : documents.length === 0 ? (
                <p className="text-xs text-slate-500">
                  Upload documents in the Documents tab, then select them here to chat.
                </p>
              ) : (
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {documents.map((doc) => (
                    <label key={doc.id} className="flex items-center gap-2 p-2 hover:bg-slate-700/50 rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedDocs.includes(doc.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedDocs([...selectedDocs, doc.id])
                          } else {
                            setSelectedDocs(selectedDocs.filter(id => id !== doc.id))
                          }
                        }}
                        className="rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-slate-300 truncate">{doc.title}</p>
                        <p className="text-xs text-slate-500">{doc.file_type} • {doc.chunk_count} chunks</p>
                      </div>
                      {doc.status === 'completed' && (
                        <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                      )}
                    </label>
                  ))}
                </div>
              )}
              
              {selectedDocs.length > 0 && (
                <button
                  onClick={() => initializeSession(selectedDocs)}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition"
                >
                  Start Chat with {selectedDocs.length} document(s)
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
