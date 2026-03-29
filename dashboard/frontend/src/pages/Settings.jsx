import React, { useEffect, useState } from 'react'
import { Loader2, Save } from 'lucide-react'
import Connections from './settings/Connections.jsx'

export default function Settings() {
  const [loading, setLoading] = useState(true)
  const [provider, setProvider] = useState('openclaw')
  const [options, setOptions] = useState([])
  const [saving, setSaving] = useState(false)

  const loadSettings = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/settings')
      const data = await response.json()
      setProvider(data.settings?.writing_provider || 'openclaw')
      setOptions(data.options?.writing || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSettings()
  }, [])

  const saveSettings = async () => {
    setSaving(true)
    try {
      await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ writing_provider: provider }),
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="animate-spin text-accent" size={28} />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <section className="card p-4">
        <h1 className="text-lg font-semibold">Settings</h1>
        <p className="mt-1 text-sm text-subtext">Keep only the writing engine and blog publishing connections.</p>

        <div className="mt-4">
          <label className="mb-2 block text-sm font-medium">Writing Provider</label>
          <select
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
            className="w-full rounded border border-border bg-bg px-3 py-2 text-sm"
          >
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={saveSettings}
          disabled={saving}
          className="mt-4 flex items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-bg"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Save Settings
        </button>
      </section>

      <Connections />
    </div>
  )
}
