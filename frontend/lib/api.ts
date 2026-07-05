import axios, { AxiosInstance, AxiosError } from 'axios'
import { useAuthStore } from './store'

// API Configuration
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Create axios instance
export const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 second timeout
})

// Request interceptor - Add auth token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

// Response interceptor - Handle errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear auth on 401
      useAuthStore.getState().logout()
      window.location.href = '/auth/login'
    }
    return Promise.reject(error)
  }
)

// API Response Types
export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface UserProfile {
  id: number
  email: string
  username: string
  role: string
  is_verified: boolean
  created_at: string
}

export interface Document {
  id: number
  title: string
  file_type: string
  status: 'processing' | 'completed' | 'failed'
  chunk_count: number
  embedding_count: number
  file_size: number
  created_at: string
  updated_at: string
}

export interface ChatSession {
  session_id: number
  document_id?: number
  created_at: string
}

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ document_id: number; page: number; score: number }>
  created_at: string
}

// Auth API
export const authAPI = {
  register: (email: string, username: string, password: string) =>
    api.post<AuthResponse>('/auth/register', { email, username, password }),
  
  login: (email: string, password: string) =>
    api.post<AuthResponse>('/auth/login', { email, password }),
  
  getProfile: () =>
    api.get<UserProfile>('/auth/me'),
}

// Workspaces API
export const workspacesAPI = {
  list: (skip = 0, limit = 20) =>
    api.get('/workspaces/', {
      params: { skip, limit },
    }),
}

// Documents API
export const documentsAPI = {
  upload: (file: File, workspaceId: number) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/documents/upload?workspace_id=${workspaceId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: (workspaceId: number, skip = 0, limit = 20) =>
    api.get<Document[]>('/documents/', {
      params: { workspace_id: workspaceId, skip, limit },
    }),

  get: (id: number) =>
    api.get<Document>(`/documents/${id}`),

  delete: (id: number) =>
    api.delete(`/documents/${id}`),

  summarize: (id: number) =>
    api.get(`/documents/${id}/summary`),
}

// Chat API
export const chatAPI = {
  createSession: (workspaceId: number, documentIds?: number[]) =>
    api.post<ChatSession>('/chat/sessions', null, {
      params: {
        workspace_id: workspaceId,
        ...(documentIds && documentIds.length > 0 && { document_ids: documentIds }),
      },
    }),

  ask: (sessionId: number, query: string, documentIds?: number[], stream = false) =>
    api.post('/chat/ask', null, {
      params: {
        session_id: sessionId,
        query,
        stream,
        ...(documentIds && documentIds.length > 0 && { document_ids: documentIds }),
      },
    }),

  getMessages: (sessionId: number, skip = 0, limit = 50) =>
    api.get<Message[]>(`/chat/sessions/${sessionId}/messages`, {
      params: { skip, limit },
    }),

  getSessions: (skip = 0, limit = 20) =>
    api.get<any[]>('/chat/sessions', {
      params: { skip, limit },
    }),

  deleteSession: (sessionId: number) =>
    api.delete(`/chat/sessions/${sessionId}`),

  export: (sessionId: number, format: 'md' | 'json' | 'pdf' = 'md') =>
    api.get(`/chat/sessions/${sessionId}/export`, {
      params: { format },
      responseType: 'blob',
    }),
}

// Search API
export const searchAPI = {
  search: (
    query: string,
    workspaceId: number,
    opts?: {
      documentIds?: number[]
      searchType?: 'semantic' | 'keyword' | 'hybrid'
      filterFileType?: string
      skip?: number
      limit?: number
    }
  ) =>
    api.get('/search/', {
      params: {
        query,
        workspace_id: workspaceId,
        document_ids: opts?.documentIds,
        search_type: opts?.searchType || 'hybrid',
        filter_file_type: opts?.filterFileType,
        skip: opts?.skip || 0,
        limit: opts?.limit || 20,
      },
    }),

  suggestions: (query: string, workspaceId: number) =>
    api.get('/search/suggestions', {
      params: { query, workspace_id: workspaceId },
    }),

  filters: (workspaceId: number) =>
    api.get('/search/filters', {
      params: { workspace_id: workspaceId },
    }),
}

// Export API instance for direct use if needed
export default api
