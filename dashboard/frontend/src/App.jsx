import React, { useState } from 'react'
import { FileText, LayoutDashboard, ScrollText, Settings } from 'lucide-react'
import Content from './pages/Content.jsx'
import Logs from './pages/Logs.jsx'
import Overview from './pages/Overview.jsx'
import SettingsPage from './pages/Settings.jsx'

const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, component: Overview },
  { id: 'content', label: 'Content', icon: FileText, component: Content },
  { id: 'settings', label: 'Settings', icon: Settings, component: SettingsPage },
  { id: 'logs', label: 'Logs', icon: ScrollText, component: Logs },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const ActiveComponent = TABS.find((tab) => tab.id === activeTab)?.component || Overview

  return (
    <div className="flex h-screen flex-col bg-bg text-text overflow-hidden">
      <header className="flex items-center justify-between border-b border-border bg-card px-4 py-3">
        <div>
          <div className="text-lg font-semibold text-accent">Blog Writer Blog</div>
          <div className="text-xs text-subtext">Blog-only standalone dashboard</div>
        </div>
      </header>

      <nav className="flex border-b border-border bg-card overflow-x-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon
          const active = tab.id === activeTab
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm border-b-2 whitespace-nowrap ${
                active ? 'border-accent text-accent' : 'border-transparent text-subtext hover:text-text'
              }`}
            >
              <Icon size={15} />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </nav>

      <main className="flex-1 overflow-y-auto">
        <ActiveComponent />
      </main>
    </div>
  )
}
