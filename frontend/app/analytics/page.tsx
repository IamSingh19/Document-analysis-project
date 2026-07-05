'use client'

import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const usageData = [
  { date: 'Mon', documents: 5, questions: 24 },
  { date: 'Tue', documents: 3, questions: 18 },
  { date: 'Wed', documents: 8, questions: 42 },
  { date: 'Thu', documents: 2, questions: 15 },
  { date: 'Fri', documents: 12, questions: 58 },
  { date: 'Sat', documents: 4, questions: 22 },
  { date: 'Sun', documents: 6, questions: 31 },
]

const topDocs = [
  { name: 'Q1 Financial Report', questions: 145, views: 342 },
  { name: 'Product Roadmap', questions: 98, views: 276 },
  { name: 'API Documentation', questions: 87, views: 201 },
]

export default function AnalyticsPage() {
  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Analytics</h1>
        <p className="text-slate-400">Track your document usage and engagement</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Documents', value: '24', icon: '📄', trend: '+3' },
          { label: 'Questions Asked', value: '1.2K', icon: '💬', trend: '+18%' },
          { label: 'Team Members', value: '8', icon: '👥', trend: '+1' },
          { label: 'Avg. Response Time', value: '1.2s', icon: '⚡', trend: '-0.3s' },
        ].map((kpi) => (
          <div key={kpi.label} className="glass p-6 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">{kpi.label}</p>
                <p className="text-3xl font-bold mt-2">{kpi.value}</p>
                <p className="text-green-400 text-xs mt-2">{kpi.trend}</p>
              </div>
              <div className="text-4xl opacity-20">{kpi.icon}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Usage Over Time */}
        <div className="glass p-6 rounded-xl">
          <h2 className="text-lg font-bold mb-6">Usage Over Time</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={usageData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
              <Legend />
              <Line type="monotone" dataKey="questions" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Document Uploads */}
        <div className="glass p-6 rounded-xl">
          <h2 className="text-lg font-bold mb-6">Documents Uploaded</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={usageData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
              <Bar dataKey="documents" fill="#8b5cf6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Documents */}
      <div className="glass p-6 rounded-xl">
        <h2 className="text-lg font-bold mb-6">Most Accessed Documents</h2>
        <div className="space-y-4">
          {topDocs.map((doc, idx) => (
            <div key={idx} className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition">
              <div className="flex-1">
                <h3 className="font-medium">{doc.name}</h3>
                <div className="flex gap-6 text-sm text-slate-400 mt-1">
                  <span>💬 {doc.questions} questions</span>
                  <span>👁 {doc.views} views</span>
                </div>
              </div>
              <div className="w-24 h-8 bg-blue-500/20 rounded-lg flex items-center justify-end px-2">
                <span className="text-sm font-medium text-blue-400">{((doc.questions / 145) * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
