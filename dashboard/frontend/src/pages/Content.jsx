import React, { useEffect, useState } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'

function Column({ title, cards, onApprove, onReject }) {
  return (
    <div className="rounded-lg bg-card/50 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-accent">{title}</h2>
        <span className="rounded-full bg-border px-2 py-0.5 text-xs text-subtext">{cards.length}</span>
      </div>
      <div className="space-y-2">
        {cards.map((card) => (
          <div key={card.id} className="card p-3">
            <div className="text-sm font-medium">{card.title}</div>
            <div className="mt-1 text-xs text-subtext">{card.corner || 'Uncategorized'}</div>
            {card.summary && <div className="mt-2 line-clamp-4 text-xs text-subtext">{card.summary}</div>}
            {card.status === 'review' && (
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => onApprove(card.id)}
                  className="rounded bg-success px-3 py-1 text-xs font-medium text-white"
                >
                  Approve
                </button>
                <button
                  onClick={() => onReject(card.id)}
                  className="rounded bg-error px-3 py-1 text-xs font-medium text-white"
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        ))}
        {cards.length === 0 && <div className="py-6 text-center text-xs text-subtext">No items</div>}
      </div>
    </div>
  )
}

export default function Content() {
  const [columns, setColumns] = useState({})
  const [loading, setLoading] = useState(true)

  const fetchContent = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/content')
      const data = await response.json()
      setColumns(data.columns || {})
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchContent()
  }, [])

  const runManualWrite = async () => {
    await fetch('/api/manual-write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    fetchContent()
  }

  const approve = async (id) => {
    await fetch(`/api/content/${id}/approve`, { method: 'POST' })
    fetchContent()
  }

  const reject = async (id) => {
    await fetch(`/api/content/${id}/reject`, { method: 'POST' })
    fetchContent()
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="animate-spin text-accent" size={28} />
      </div>
    )
  }

  return (
    <div className="space-y-4 p-4 md:p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Content</h1>
          <p className="text-sm text-subtext">Review the current blog content pipeline.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchContent}
            className="flex items-center gap-2 rounded border border-border px-3 py-2 text-xs text-subtext hover:text-text"
          >
            <RefreshCw size={13} />
            Refresh
          </button>
          <button onClick={runManualWrite} className="rounded bg-accent px-3 py-2 text-xs font-medium text-bg">
            Run Collect + Write
          </button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-4">
        <Column title={columns.queue?.label || 'Queue'} cards={columns.queue?.cards || []} onApprove={approve} onReject={reject} />
        <Column title={columns.writing?.label || 'Drafts'} cards={columns.writing?.cards || []} onApprove={approve} onReject={reject} />
        <Column title={columns.review?.label || 'Review'} cards={columns.review?.cards || []} onApprove={approve} onReject={reject} />
        <Column title={columns.published?.label || 'Published'} cards={columns.published?.cards || []} onApprove={approve} onReject={reject} />
      </div>
    </div>
  )
}
