'use client'

import { useState } from 'react'
import { Users, Plus, Trash2, Shield } from 'lucide-react'

export default function SettingsPage() {
  const [members, setMembers] = useState([
    { id: 1, email: 'user@docmind.com', role: 'owner', joined: '2024-01-15' },
    { id: 2, email: 'team@docmind.com', role: 'manager', joined: '2024-02-01' },
  ])
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')

  const handleInvite = () => {
    if (!inviteEmail) return
    setMembers([...members, { id: Date.now(), email: inviteEmail, role: inviteRole, joined: new Date().toISOString().split('T')[0] }])
    setInviteEmail('')
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-slate-400">Manage workspace and team</p>
      </div>

      {/* Workspace Settings */}
      <div className="glass p-6 rounded-xl space-y-6">
        <div>
          <h2 className="text-xl font-bold mb-4">Workspace</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Workspace Name</label>
              <input type="text" defaultValue="My Workspace" className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 focus:border-blue-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Description</label>
              <textarea defaultValue="My document workspace" rows={3} className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 focus:border-blue-500 outline-none" />
            </div>
            <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium">
              Save Changes
            </button>
          </div>
        </div>
      </div>

      {/* Team Members */}
      <div className="glass p-6 rounded-xl space-y-6">
        <div>
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Users className="w-5 h-5" />
            Team Members
          </h2>

          {/* Invite */}
          <div className="mb-6 p-4 bg-slate-800/50 rounded-lg">
            <div className="flex gap-3">
              <input
                type="email"
                placeholder="team@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
              >
                <option value="member">Member</option>
                <option value="manager">Manager</option>
                <option value="owner">Owner</option>
              </select>
              <button
                onClick={handleInvite}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2 text-sm font-medium transition"
              >
                <Plus className="w-4 h-4" />
                Invite
              </button>
            </div>
          </div>

          {/* Members List */}
          <div className="space-y-2">
            {members.map((member) => (
              <div key={member.id} className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition">
                <div className="flex-1">
                  <p className="font-medium">{member.email}</p>
                  <p className="text-sm text-slate-400">Joined {member.joined}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-xs font-medium">
                    {member.role}
                  </span>
                  <button className="p-2 hover:bg-slate-700 rounded-lg transition">
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="glass p-6 rounded-xl">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5" />
          Security
        </h2>
        <div className="space-y-4">
          <button className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-700 rounded-lg text-left transition">
            <p className="font-medium">Change Password</p>
            <p className="text-sm text-slate-400">Update your account password</p>
          </button>
          <button className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-700 rounded-lg text-left transition">
            <p className="font-medium">Two-Factor Authentication</p>
            <p className="text-sm text-slate-400">Add extra security to your account</p>
          </button>
          <button className="w-full px-4 py-3 bg-red-500/10 hover:bg-red-500/20 rounded-lg text-left transition border border-red-500/20">
            <p className="font-medium text-red-400">Delete Workspace</p>
            <p className="text-sm text-red-300">Permanently remove workspace and all data</p>
          </button>
        </div>
      </div>
    </div>
  )
}
