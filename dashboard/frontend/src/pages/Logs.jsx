import React, { useEffect, useState } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'collector', label: 'Collector' },
  { value: 'writer', label: 'Writer' },
  { value: 'publisher', label: 'Publisher' },
  { value: 'error', label: 'Errors' },
]

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filter) params.set('filter', filter)
      const response = await fetch(`/api/logs?${params.toString()}`)
      const data = await response.json()
      setLogs(data.logs || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [filter])

  return (
    <div className="space-y-4 p-4 md:p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Logs</h1>
          <p className="text-sm text-subtext">Recent collector, writer, and publisher logs.</p>
        </div>
        <button
          onClick={fetchLogs}
          className="flex items-center gap-2 rounded border border-border px-3 py-2 text-xs text-subtext hover:text-text"
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item.value}
            onClick={() => setFilter(item.value)}
            className={`rounded-full border px-3 py-1 text-xs ${
              filter === item.value ? 'border-accent text-accent' : 'border-border text-subtext'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <Loader2 className="animate-spin text-accent" size={24} />
          </div>
        ) : (
          <div className="max-h-[70vh] overflow-y-auto">
            {logs.map((log, index) => (
              <div key={`${log.time}-${index}`} className="grid grid-cols-[160px_90px_1fr] gap-2 border-b border-border px-3 py-2 text-xs">
                <span className="text-subtext">{log.time}</span>
                <span className="text-subtext">[{log.module}]</span>
                <span>{log.message}</span>
              </div>
            ))}
            {logs.length === 0 && <div className="p-6 text-center text-sm text-subtext">No log entries found.</div>}
          </div>
        )}
      </div>
    </div>
  )
}
