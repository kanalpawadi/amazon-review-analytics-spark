import React, { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { restoreTheme, toggleTheme } from './lib/theme.js'
import Overview from './pages/Overview.jsx'
import Sentiment from './pages/Sentiment.jsx'
import FakeReviews from './pages/FakeReviews.jsx'
import Recommendations from './pages/Recommendations.jsx'
import Scalability from './pages/Scalability.jsx'
import About from './pages/About.jsx'

const PAGES = [
  ['/', 'Overview', '⚡', Overview],
  ['/sentiment', 'Sentiment + XAI', '🧠', Sentiment],
  ['/fake-reviews', 'Fake Reviews + XAI', '🛡️', FakeReviews],
  ['/recommendations', 'Recommendations', '🎯', Recommendations],
  ['/scalability', 'Scalability & Benchmarks', '📈', Scalability],
  ['/about', 'About the Project', '📖', About],
]

export default function App() {
  const [isDark, setIsDark] = useState(true)

  useEffect(() => {
    restoreTheme()
    setIsDark(document.documentElement.dataset.theme !== 'light')
  }, [])

  const handleToggle = () => {
    toggleTheme()
    setIsDark(document.documentElement.dataset.theme !== 'light')
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand-wrapper">
          <div className="brand-icon">⚡</div>
          <div className="brand">
            Amazon Analytics
            <span>Spark · Hadoop · Hive · XAI</span>
          </div>
        </div>

        <div className="telemetry-badge">
          <span>Built on Apache Spark 3.5</span>
        </div>

        <nav className="nav">
          {PAGES.map(([path, label, icon]) => (
            <NavLink key={path} to={path} end={path === '/'}>
              <span className="nav-icon">{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <button className="theme-btn" onClick={handleToggle}>
            <span>{isDark ? '☀️' : '🌙'}</span>
            <span>Switch to {isDark ? 'Light' : 'Dark'} Mode</span>
          </button>
          <div>
            <b style={{ color: 'var(--text)' }}>DKTE Society's TEI</b><br />
            Dept. of AI &amp; Data Science · 2026-27
          </div>
          <div className="tiny">
            Dataset: Amazon Reviews 2023 (McAuley Lab, UCSD) · 43.9M records
          </div>
        </div>
      </aside>

      <main>
        <Routes>
          {PAGES.map(([path, , , Page]) => <Route key={path} path={path} element={<Page />} />)}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
