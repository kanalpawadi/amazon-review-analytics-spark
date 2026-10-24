import React, { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, ChartTip, FeatureBanner, Loaded, PageHead, Stat, axisProps } from '../components/ui.jsx'
import { fmt, useData } from '../lib/data.js'
import { useColors } from '../lib/theme.js'

/** Amazon titles are very long: show the start, the full name on hover. */
function Name({ text, max = 70 }) {
  const t = String(text || 'unknown product')
  return <span title={t}>{t.length > max ? `${t.slice(0, max).trimEnd()}…` : t}</span>
}

function UserView({ users }) {
  const [query, setQuery] = useState('')
  const list = useMemo(() => users.filter((u) => u.user_id.toLowerCase().includes(query.toLowerCase())), [users, query])
  const [uid, setUid] = useState(users[0]?.user_id)
  const u = users.find((x) => x.user_id === uid) || list[0]
  if (!u) return <div className="empty">No users matching search query in exported cohort.</div>

  return (
    <>
      <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 2fr)' }}>
        <Card title="Customer Cohort Selector" badge={`${list.length} Users`} sub="Select user to inspect latent taste profile">
          <input placeholder="🔍 Filter by User ID..." value={query} onChange={(e) => setQuery(e.target.value)} />
          <select size={8} style={{ marginTop: 10 }} value={u.user_id} onChange={(e) => setUid(e.target.value)}>
            {list.slice(0, 300).map((x) => (
              <option key={x.user_id} value={x.user_id}>{x.user_id}</option>
            ))}
          </select>
          <h3 style={{ marginTop: 20 }}>Historical Rating Footprint ({u.history.length})</h3>
          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            {u.history.map((h, i) => (
              <div key={i} className="small" style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                <span className="pill accent" style={{ marginRight: 6 }}>{h.rating}★</span>
                <Name text={h.title} max={55} />
                <div className="tiny" style={{ marginTop: 2 }}>{h.date}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Personalized Top 10 Recommendations" sub="Spark MLlib Implicit ALS (Hu-Koren-Volinsky) · unrated candidate retrieval" badge="Explainable Vectors">
          {u.recs.map((r) => (
            <div className="rec" key={r.rank}>
              <span className="n">{r.rank}</span>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <b><Name text={r.title} /></b>
                  {r.category && <span className="tiny" style={{ color: 'var(--text-3)' }}>· {r.category}</span>}
                  {r.popular != null && (
                    <span className={`pill ${r.popular ? 'accent' : 'neu'}`}>{r.popular ? '🔥 Popular' : '💎 Niche'}</span>
                  )}
                </div>
                {r.because.length > 0 ? (
                  <div className="because">
                    <span>💡 Recommendation basis: </span>
                    {r.because.map((b, i) => (
                      <span key={i}>
                        {i > 0 && ' and '}
                        Because you highly rated <b><Name text={b.title} max={50} /></b>
                        {' '}(Latent Cosine Similarity: <b style={{ fontFamily: 'JetBrains Mono, monospace' }}>{fmt.num(b.similarity, 3)}</b>)
                      </span>
                    ))}
                  </div>
                ) : <div className="because tiny">Global latent factor prior (no single dominant neighbor item).</div>}
              </div>
            </div>
          ))}
        </Card>
      </div>
      <p className="tiny" style={{ marginTop: 10 }}>
        Vector Attribution Mechanism: Implicit ALS assigns a 64-dimensional latent taste vector to every product and user.
        The system computes the exact cosine similarity between the candidate recommendation and all previously rated items in the user's history to explain why the item emerged.
      </p>
    </>
  )
}

export default function Recommendations() {
  const state = useData('recs')
  const c = useColors()

  return (
    <>
      <FeatureBanner
        image="/images/recommendations.jpg"
        title="Collaborative Filtering & Latent Vector Recs"
        desc="Implicit Alternating Least Squares (ALS) Matrix Factorization on Apache Spark, with item-to-item cosine similarity explanations for every recommendation."
        tags={['Spark Implicit ALS', 'Latent Factor Vectors', 'Cosine Similarity XAI', 'Leave-One-Out Evaluation']}
      />

      <PageHead title="Personalized Recommendations & Vector Explanations" badge="Item-to-Item XAI">
        Personalized catalog discovery on the 5-core Electronics benchmark with transparent item-level taste justifications.
      </PageHead>

      <Loaded state={state} what="recommendation results">
        {(d) => {
          const s = d.stats || {}
          const ranking = d.ranking || []
          const hitKey = ranking[0] ? Object.keys(ranking[0]).find((k) => k.startsWith('hit_rate')) : null
          const ndcgKey = ranking[0] ? Object.keys(ranking[0]).find((k) => k.startsWith('ndcg')) : null
          const colorOf = (m) => (m.startsWith('Baseline') ? c.neu : m.startsWith('Implicit') ? c.series[0] : c.series[1])

          return (
            <>
              <div className="grid g4">
                <Stat label="Ratings Ingested" value={fmt.int(s.ratings)} note={s.user_fraction ? `${fmt.share(s.user_fraction)} user sample` : ''} icon="⭐" />
                <Stat label="Unique Customers" value={fmt.int(s.users)} note="5-core filtered" icon="👥" />
                <Stat label="Catalog Items" value={fmt.int(s.products)} note="Latent item factors" icon="📦" />
                <Stat label="Ratings / User" value={fmt.num(s.ratings_per_user, 1)} note={s.density_pct != null ? `Matrix density ${s.density_pct}%` : ''} icon="📊" />
              </div>

              <div style={{ marginTop: 20 }}>
                {d.users?.length ? <UserView users={d.users} /> : <div className="empty">No recommendation lists exported yet.</div>}
              </div>

              <h2 style={{ marginTop: 32 }}>Evaluation Metrics: Hit Rate @ 10 &amp; NDCG</h2>
              <div className="grid g2">
                {[hitKey, ndcgKey].filter(Boolean).map((k) => (
                  <Card
                    key={k}
                    title={k.replace('_', ' ').replace('@', ' @ ')}
                    sub={k.startsWith('hit') ? "Probability that the held-out next real purchase appears in the top-10 recommendations" : 'Normalized Discounted Cumulative Gain: higher ranks reward higher predictive confidence'}
                    badge="Ranking Quality"
                  >
                    <ResponsiveContainer width="100%" height={230}>
                      <BarChart data={ranking} margin={{ top: 22, right: 8, left: -6, bottom: 0 }}>
                        <CartesianGrid vertical={false} stroke={c.grid} />
                        <XAxis dataKey="model" {...axisProps(c)} tick={{ fill: c.text2, fontSize: 11 }} interval={0} />
                        <YAxis {...axisProps(c)} />
                        <Tooltip cursor={{ fill: c.grid, opacity: 0.2 }} content={<ChartTip format={(v, p) => `${fmt.num(v, 4)} · ${fmt.int(p.payload.products_recommended)} products recommended`} />} />
                        <Bar dataKey={k} name={k} radius={[6, 6, 0, 0]} maxBarSize={56}
                             label={{ position: 'top', fill: c.text2, fontSize: 12, formatter: (v) => fmt.num(v, 4) }}>
                          {ranking.map((r) => <Cell key={r.model} fill={colorOf(r.model)} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                ))}
              </div>

              <div className="grid g2">
                <Card title="Rating Prediction Error (RMSE Benchmark)" sub="Explicit rating regression comparison on test set (lower is superior)" badge="Numerical Error">
                  <div className="table-wrap">
                    <table>
                      <thead><tr><th>Model Formulation</th><th className="num">Test Set RMSE</th></tr></thead>
                      <tbody>
                        {(d.rmse || []).map((r) => (
                          <tr key={r.model}>
                            <td><b>{r.model}</b></td>
                            <td className="num"><b style={{ fontFamily: 'JetBrains Mono, monospace' }}>{fmt.num(r.test_rmse, 4)}</b></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
                <Card title="Why Implicit ALS Outperforms Explicit ALS" badge="Theoretical Insight">
                  <p className="small">
                    <b>Explicit ALS:</b> Minimizes squared error on known star ratings. Under severe sparsity (0.01% density),
                    it suffers from cold products receiving inflated 5-star predicted ratings, degrading real-world top-K hit rate.
                  </p>
                  <p className="small">
                    <b>Implicit ALS (Hu, Koren, Volinsky):</b> Formulates rating as a confidence proxy rather than continuous preference.
                    Unobserved entries are treated as low-confidence negatives, yielding significantly superior retrieval hit rates on future purchases.
                  </p>
                </Card>
              </div>
            </>
          )
        }}
      </Loaded>
    </>
  )
}
