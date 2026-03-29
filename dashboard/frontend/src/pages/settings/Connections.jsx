import React, { useEffect, useState } from 'react'
import { CheckCircle2, Circle, Loader2, RefreshCw } from 'lucide-react'

function ConnectionCard({ item, onRefresh }) {
  const [inputValue, setInputValue] = useState('')
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)

  const testConnection = async () => {
    setTesting(true)
    try {
      const response = await fetch(`/api/connections/${item.id}/test`, { method: 'POST' })
      const data = await response.json()
      window.alert(data.message)
      onRefresh()
    } finally {
      setTesting(false)
    }
  }

  const saveConnection = async () => {
    if (!inputValue.trim()) return
    setSaving(true)
    try {
      await fetch(`/api/connections/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: inputValue.trim() }),
      })
      setInputValue('')
      onRefresh()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-2">
          {item.connected ? <CheckCircle2 size={16} className="text-success" /> : <Circle size={16} className="text-subtext" />}
          <div>
            <div className="text-sm font-medium">{item.name}</div>
            <div className="text-xs text-subtext">{item.description}</div>
          </div>
        </div>
        <span className="text-xs text-subtext">{item.connected ? 'Connected' : 'Missing'}</span>
      </div>

      {item.key_masked && <div className="mt-3 text-xs text-subtext">{item.key_masked}</div>}

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          onClick={testConnection}
          disabled={testing}
          className="rounded border border-border px-3 py-1 text-xs text-subtext"
        >
          {testing ? 'Testing...' : 'Test'}
        </button>

        {item.id !== 'openclaw' && (
          <>
            <input
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              placeholder={item.id === 'blogger' ? 'BLOG_MAIN_ID' : 'API key'}
              className="min-w-[180px] rounded border border-border bg-bg px-3 py-1 text-xs"
            />
            <button
              onClick={saveConnection}
              disabled={saving}
              className="rounded bg-accent px-3 py-1 text-xs font-medium text-bg"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default function Connections() {
  const [connections, setConnections] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchConnections = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/connections')
      const data = await response.json()
      setConnections(data.connections || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConnections()
  }, [])

  return (
    <section className="card p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-accent">Connections</h2>
          <p className="text-xs text-subtext">Writing providers and Blogger publishing state.</p>
        </div>
        <button onClick={fetchConnections} className="flex items-center gap-2 text-xs text-subtext">
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="animate-spin text-accent" size={24} />
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {connections.map((item) => (
            <ConnectionCard key={item.id} item={item} onRefresh={fetchConnections} />
          ))}
        </div>
      )}
    </section>
  )
}
