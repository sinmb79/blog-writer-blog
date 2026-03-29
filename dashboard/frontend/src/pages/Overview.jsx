import React, { useEffect, useState } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'

function MetricCard({ label, value }) {
  return (
    <div className="card p-4">
      <div className="text-xs text-subtext">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  )
}

export default function Overview() {
  const [overview, setOverview] = useState(null)
  const [pipeline, setPipeline] = useState([])
  const [activity, setActivity] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [overviewRes, pipelineRes, activityRes] = await Promise.all([
        fetch('/api/overview'),
        fetch('/api/pipeline'),
        fetch('/api/activity'),
      ])
      const overviewData = await overviewRes.json()
      const pipelineData = await pipelineRes.json()
      const activityData = await activityRes.json()
      setOverview(overviewData.kpi || {})
      setPipeline(pipelineData.steps || [])
      setActivity(activityData.logs || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [])

  if (loading && !overview) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="animate-spin text-accent" size={28} />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Overview</h1>
          <p className="text-sm text-subtext">Collection, writing, review, and publishing at a glance.</p>
        </div>
        <button
          onClick={fetchAll}
          className="flex items-center gap-2 rounded border border-border px-3 py-2 text-xs text-subtext hover:text-text"
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Published Today" value={overview?.today ?? 0} />
        <MetricCard label="Published This Week" value={overview?.this_week ?? 0} />
        <MetricCard label="Pending Review" value={overview?.pending_review ?? 0} />
        <MetricCard label="Drafts" value={overview?.drafts ?? 0} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card p-4">
          <h2 className="mb-3 text-sm font-semibold text-accent">Pipeline</h2>
          <div className="space-y-2">
            {pipeline.map((step) => (
              <div key={step.id} className="flex items-center justify-between border-b border-border py-2 last:border-0">
                <span className="text-sm">{step.name}</span>
                <span className="text-xs text-subtext">
                  {step.status}
                  {step.done_at ? ` · ${step.done_at}` : ''}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="card p-4">
          <h2 className="mb-3 text-sm font-semibold text-accent">Recent Activity</h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {activity.map((item, index) => (
              <div key={`${item.time}-${index}`} className="grid grid-cols-[56px_80px_1fr] gap-2 text-xs">
                <span className="text-subtext">{item.time}</span>
                <span className="text-subtext">[{item.module}]</span>
                <span>{item.message}</span>
              </div>
            ))}
            {activity.length === 0 && <div className="text-sm text-subtext">No recent log entries.</div>}
          </div>
        </section>
      </div>
    </div>
  )
}
