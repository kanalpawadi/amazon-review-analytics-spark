import React from 'react'

export function HeroShowcase({ image, title, desc, badges = [] }) {
  return (
    <div className="hero-showcase">
      <div className="hero-image-wrap">
        <img src={image} alt={title} className="hero-img" />
        <div className="hero-overlay">
          {badges.length > 0 && (
            <div className="hero-badges">
              {badges.map((b, i) => (
                <span key={i} className={`pill ${b.variant || 'accent'}`}>
                  {b.icon && <span>{b.icon}</span>}
                  {b.text}
                </span>
              ))}
            </div>
          )}
          <h2 className="hero-title">{title}</h2>
          {desc && <p className="hero-desc">{desc}</p>}
        </div>
      </div>
    </div>
  )
}

export function FeatureBanner({ image, title, desc, tags = [], children }) {
  return (
    <div className="feature-banner">
      <div className="feature-banner-img">
        <img src={image} alt={title} />
      </div>
      <div className="feature-banner-content">
        <h2>{title}</h2>
        <p>{desc}</p>
        {tags.length > 0 && (
          <div className="feature-tags">
            {tags.map((t, i) => (
              <span key={i} className="pill accent">{t}</span>
            ))}
          </div>
        )}
        {children}
      </div>
    </div>
  )
}

export function Card({ title, sub, badge, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      {(title || badge) && (
        <div className="card-header-row">
          <div>
            {title && <div className="chart-title">{title}</div>}
            {sub && <div className="chart-sub">{sub}</div>}
          </div>
          {badge && <span className="pill accent">{badge}</span>}
        </div>
      )}
      {children}
    </section>
  )
}

export function Stat({ label, value, note, icon }) {
  return (
    <div className="card stat">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="label">{label}</div>
        {icon && <span style={{ fontSize: '1.2rem', opacity: 0.8 }}>{icon}</span>}
      </div>
      <div className="value">{value}</div>
      {note && <div className="note">{note}</div>}
    </div>
  )
}

export function PageHead({ title, badge, children }) {
  return (
    <header className="page-head">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h1>{title}</h1>
        {badge && <span className="pill accent">{badge}</span>}
      </div>
      {children && <p className="muted">{children}</p>}
    </header>
  )
}

/** Shows loading / missing-data messages; renders children(data) when ready. */
export function Loaded({ state, what, children }) {
  if (state.loading) return <div className="empty">Loading…</div>
  if (state.error || !state.data) {
    return (
      <div className="empty">
        No data for <b>{what}</b> yet. Run <code>06a_dashboard_export.ipynb</code> in Colab, download
        <code>dashboard_data.zip</code> from Google Drive, then run <code>web/scripts/build_data.py</code> and refresh this page.
      </div>
    )
  }
  return children(state.data)
}

/** Recharts tooltip in the app's style. rows: [{label, value, color}] */
export function ChartTip({ active, payload, label, format = (v) => v, title }) {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="tooltip">
      <div className="t-title">{title ? title(payload[0].payload, label) : label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
          <span style={{ color: p.color || p.fill, fontSize: '0.8rem' }}>■</span>
          <span>{p.name}: <b>{format(p.value, p)}</b></span>
        </div>
      ))}
    </div>
  )
}

export function Legend({ items }) {
  return (
    <div className="legend">
      {items.map(([label, color]) => (
        <span key={label}><i style={{ background: color }} />{label}</span>
      ))}
    </div>
  )
}

export function axisProps(c) {
  return {
    tick: { fill: c.text2, fontSize: 11, fontFamily: 'JetBrains Mono, monospace' },
    axisLine: { stroke: c.grid },
    tickLine: false,
  }
}
