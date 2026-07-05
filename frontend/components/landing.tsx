'use client'

import Link from 'next/link'
import { Zap, FileText, Sparkles } from 'lucide-react'

export function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Navigation */}
      <nav className="fixed top-0 w-full border-b border-slate-800/50 glass z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            DocMind AI
          </h1>
          <div className="flex gap-4">
            <Link href="/auth/login" className="px-4 py-2 text-sm hover:text-blue-400 transition">
              Sign In
            </Link>
            <Link
              href="/auth/register"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 py-40 text-center">
        <div className="space-y-6">
          <h2 className="text-6xl font-bold">
            Chat with Your{' '}
            <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              Documents
            </span>
          </h2>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            DocMind AI uses advanced RAG to help you understand documents instantly.
            Ask questions, get instant answers with citations.
          </p>
          <Link
            href="/auth/register"
            className="inline-block px-8 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition"
          >
            Start Free Trial
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <h3 className="text-3xl font-bold text-center mb-12">Why DocMind AI?</h3>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              icon: FileText,
              title: 'Multi-Format Support',
              desc: 'PDF, Word, PowerPoint, CSV, and more',
            },
            {
              icon: Sparkles,
              title: 'AI-Powered',
              desc: 'RAG with semantic search for accurate answers',
            },
            {
              icon: Zap,
              title: 'Lightning Fast',
              desc: 'Sub-second search and instant responses',
            },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="glass p-6 rounded-xl space-y-3">
              <Icon className="w-8 h-8 text-blue-400" />
              <h4 className="text-lg font-bold">{title}</h4>
              <p className="text-slate-400">{desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
