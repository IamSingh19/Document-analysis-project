'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchAPI } from '@/lib/api'
import { Search, FileText, ExternalLink } from 'lucide-react'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState('hybrid')
  const [workspaceId] = useState(1)

  const { data: results, isLoading, refetch } = useQuery({
    queryKey: ['search', query, workspaceId, searchType],
    queryFn: () => searchAPI.search(query, workspaceId, { searchType: searchType as any }),
    enabled: query.length > 0,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    refetch()
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Search</h1>
        <p className="text-slate-400">Search across all your documents</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="relative">
          <Search className="absolute left-4 top-3 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What do you want to find?"
            className="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-12 pr-4 py-3 focus:border-blue-500 outline-none text-lg"
          />
        </div>

        <div className="flex gap-3">
          {['semantic', 'keyword', 'hybrid'].map((type) => (
            <button
              key={type}
              onClick={() => setSearchType(type)}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                searchType === type
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>
      </form>

      {/* Results */}
      {query && (
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            {isLoading ? 'Searching...' : `Found ${results?.data?.results?.length || 0} results`}
          </p>

          {results?.data?.results?.map((result: any) => (
            <div key={result.chunk_id} className="glass p-6 rounded-xl hover:bg-slate-800/50 transition">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-slate-400">Document {result.document_id}</span>
                    <span className="text-sm text-slate-500">• Page {result.page}</span>
                  </div>
                  <h3 className="font-medium text-lg mb-2">
                    Relevance: {(result.score * 100).toFixed(0)}%
                  </h3>
                </div>
                <button className="p-2 hover:bg-slate-700 rounded-lg transition">
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>

              <p className="text-slate-300 text-sm leading-relaxed mb-3">
                {result.highlight}
              </p>

              <div className="flex gap-2 flex-wrap">
                <span className="text-xs px-2 py-1 bg-slate-800/50 rounded-full text-slate-400">
                  {result.score > 0.8 ? 'Highly relevant' : result.score > 0.5 ? 'Relevant' : 'Somewhat relevant'}
                </span>
              </div>
            </div>
          ))}

          {!isLoading && results?.data?.results?.length === 0 && (
            <div className="text-center py-12">
              <Search className="w-12 h-12 mx-auto opacity-20 mb-4" />
              <p className="text-slate-400">No results found. Try different keywords.</p>
            </div>
          )}
        </div>
      )}

      {!query && (
        <div className="text-center py-20">
          <Search className="w-20 h-20 mx-auto opacity-10 mb-4" />
          <p className="text-slate-400 text-lg">Enter a search query to get started</p>
        </div>
      )}
    </div>
  )
}
