import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
  id: number
  email: string
  username: string
  role: 'admin' | 'manager' | 'user'
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
}

interface AuthStore {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
  
  // Auth methods
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  verifyToken: () => Promise<boolean>
  refreshUser: () => Promise<void>
  
  // State setters
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      loading: false,
      error: null,

      // Login with email and password
      login: async (email, password) => {
        try {
          set({ loading: true, error: null })
          
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          })

          if (!response.ok) {
            throw new Error('Invalid email or password')
          }

          const data = await response.json()
          set({ 
            token: data.access_token, 
            isAuthenticated: true,
            loading: false 
          })

          // Fetch user details
          await get().refreshUser()
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Login failed'
          set({ error: message, loading: false, isAuthenticated: false })
          throw error
        }
      },

      // Register new user
      register: async (email, username, password) => {
        try {
          set({ loading: true, error: null })
          
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, username, password }),
          })

          if (!response.ok) {
            throw new Error('Registration failed')
          }

          const data = await response.json()
          set({ 
            token: data.access_token, 
            isAuthenticated: true,
            loading: false 
          })

          // Fetch user details
          await get().refreshUser()
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Registration failed'
          set({ error: message, loading: false, isAuthenticated: false })
          throw error
        }
      },

      // Logout and clear auth
      logout: () => {
        set({ 
          user: null, 
          token: null, 
          isAuthenticated: false,
          error: null 
        })
      },

      // Verify token is still valid
      verifyToken: async () => {
        const token = get().token
        if (!token) {
          set({ isAuthenticated: false })
          return false
        }

        try {
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          })

          if (!response.ok) {
            get().logout()
            return false
          }

          // Token is valid, update authenticated state
          set({ isAuthenticated: true })
          return true
        } catch {
          get().logout()
          return false
        }
      },

      // Refresh user data from server
      refreshUser: async () => {
        const token = get().token
        if (!token) {
          set({ isAuthenticated: false })
          return
        }

        try {
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          })

          if (!response.ok) {
            get().logout()
            return
          }

          const user = await response.json()
          set({ user, loading: false, isAuthenticated: true })
        } catch (error) {
          console.error('Failed to refresh user:', error)
          get().logout()
        }
      },

      setUser: (user) => set({ user }),
      setToken: (token) => set({ token, isAuthenticated: !!token }),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

interface DocumentStore {
  documents: Document[]
  currentDocument: Document | null
  setDocuments: (documents: Document[]) => void
  setCurrentDocument: (document: Document | null) => void
}

export const useDocumentStore = create<DocumentStore>((set) => ({
  documents: [],
  currentDocument: null,
  setDocuments: (documents) => set({ documents }),
  setCurrentDocument: (currentDocument) => set({ currentDocument }),
}))

