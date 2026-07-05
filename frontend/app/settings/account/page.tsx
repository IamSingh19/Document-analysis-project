'use client'

import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import Link from 'next/link'

export default function AccountPage() {
  const router = useRouter()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    router.push('/auth/login')
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-white">Loading user data...</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Account Settings</h1>
        <p className="text-slate-400">Manage your profile and account preferences</p>
      </div>

      {/* User Info Card */}
      <div className="bg-slate-800 rounded-xl p-6 mb-6">
        <h2 className="text-xl font-semibold text-white mb-4">Profile Information</h2>
        
        <div className="space-y-4">
          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Email Address</label>
            <p className="text-white bg-slate-700 rounded-lg px-4 py-2">{user.email}</p>
          </div>

          {/* Username */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Username</label>
            <p className="text-white bg-slate-700 rounded-lg px-4 py-2">{user.username}</p>
          </div>

          {/* Role */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Role</label>
            <p className="text-white bg-slate-700 rounded-lg px-4 py-2 capitalize">{user.role}</p>
          </div>

          {/* Member Since */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Member Since</label>
            <p className="text-white bg-slate-700 rounded-lg px-4 py-2">
              {new Date(user.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Status</label>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <p className="text-white">{user.is_verified ? 'Verified' : 'Not Verified'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Security Section */}
      <div className="bg-slate-800 rounded-xl p-6 mb-6">
        <h2 className="text-xl font-semibold text-white mb-4">Security</h2>
        <p className="text-slate-400 text-sm mb-4">Your account is protected with JWT authentication</p>
        
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition">
          Change Password
        </button>
      </div>

      {/* Danger Zone */}
      <div className="bg-red-900/20 border border-red-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-red-400 mb-4">Danger Zone</h2>
        
        <button
          onClick={handleLogout}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition"
        >
          Logout
        </button>
        
        <p className="text-slate-400 text-sm mt-4">
          You will be signed out and redirected to the login page.
        </p>
      </div>

      {/* Back Button */}
      <div className="mt-8">
        <Link
          href="/dashboard"
          className="text-blue-400 hover:text-blue-300 transition"
        >
          ← Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
