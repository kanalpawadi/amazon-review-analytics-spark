import React, { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, ChartTip, FeatureBanner, Legend, Loaded, PageHead, Stat, axisProps } from '../components/ui.jsx'
import { fmt, useData } from '../lib/data.js'
import { useColors } from '../lib/theme.js'

const BUCKETS = ['0', '0.5-1', '1.5-2.5', '3-4', '4.5+']

/** Plain-language reason for one signal of one review (uses the review's own numbers). */
function reason(sig, r) {
  switch (sig) {
    case 'near_duplicate': return 'Almost the same text was posted on other products (copy-paste).'
    case 'text_rating_mismatch':
      return r.rating >= 4
        ? `${r.rating}★ rating, but the text reads ${fmt.share(r.p_negative)} negative to the sentiment model.`
        : `${r.rating}★ rating, but the text reads ${fmt.share(r.p_positive)} positive to the sentiment model.`
    case 'rating_deviation':
      return `${r.rating}★ while the product averages ${fmt.num(r.average_rating, 1)}★ — ${fmt.num(Math.abs(r.rating - r.average_rating), 1)} stars away.`
    case 'burst': return "Part of a burst: most of this product's reviews arrived in one week, all extreme."
    case 'outlier_reviewer': return "The reviewer's overall behaviour is far from every normal group of reviewers (top 1% by KMeans distance)."
    case 'one_sided_reviewer': return 'The reviewer gave only 5-star (or only 1-star) ratings across 5+ reviews.'
    case 'short_generic': return `Very short (${r.word_count} meaningful words) with an extreme ${r.rating}★ rating.`
    case 'unverified': return 'Amazon did not verify this purchase (a weak signal on its own).'
    default: return sig
  }
}

function ReviewExplain({ r, weights, threshold, signalText, c }) {
  const signals = Object.keys(weights)
  const on = signals.filter((s) => r[s] === true || r[s] === 'True')
  const off = signals.filter((s) => !on.includes(s))
  const score = on.reduce((s, k) => s + weights[k], 0)
  const scale = Math.max(score, threshold) * 1.15
  const shades = [c.neg, c.series[1], c.series[3], c.series[4], c.series[2], c.series[0]]

  return (
    <Card title="Anomaly Forensics Breakdown" badge={`Score: ${fmt.num(score, 1)} / Threshold: ${threshold}`}>
      <p className="small muted" style={{ marginBottom: 8 }}>
        <b>{r.product_title}</b> · {r.rating}★ · {r.review_date} · {r.verified_purchase ? 'verified purchase' : 'unverified'}
        {r.cluster_name && <> · Reviewer cluster: <span className="pill accent">{r.cluster_name}</span></>}
      </p>
      <blockquote style={{ margin: '0 0 16px', padding: '12px 16px', background: 'var(--surface-2)', borderRadius: 10, borderLeft: '3px solid var(--accent)' }}>
        {r.title && <b>{r.title}. </b>}{String(r.text || '').slice(0, 600)}
      </blockquote>

      <div className="small" style={{ marginBottom: 6 }}>
        Aggregated Suspicion Index: <b>{fmt.num(score, 1)}</b> — (Flagged threshold: ≥ {threshold})
      </div>
      <div className="score-bar">
        {on.map((s, i) => (
          <div key={s} className="seg" title={`${s}: +${weights[s]}`}
               style={{ width: `${(weights[s] / scale) * 100}%`, background: shades[i % shades.length] }} />
        ))}
        <div className="thr" style={{ left: `${(threshold / scale) * 100}%` }} title={`threshold ${threshold}`} />
      </div>
      <Legend items={on.map((s, i) => [`${s} (+${weights[s]} pts)`, shades[i % shades.length]])} />

      <h3 style={{ marginTop: 18 }}>Triggered Anomaly Indicators ({on.length})</h3>
      {on.map((s) => (
        <div className="reason" key={s}>
          <span className="pts">+{weights[s]}</span>
          <span>{reason(s, r)}</span>
        </div>
      ))}

      <h3 style={{ marginTop: 16 }}>Clear Indicators ({off.length})</h3>
      {off.map((s) => (
        <div className="reason off" key={s}>
          <span className="pts">0</span>
          <span>{signalText[s]}</span>
        </div>
      ))}
    </Card>
  )
}

function Explorer({ d, c }) {
  const weights = d.weights || {}
  const [filter, setFilter] = useState([])
  const examples = useMemo(() => (d.examples || []).filter((r) => filter.every((s) => r[s] === true || r[s] === 'True')),
    [d.examples, filter])
  const [sel, setSel] = useState(0)
  const r = examples[Math.min(sel, Math.max(examples.length - 1, 0))]
  const toggle = (s) => { setSel(0); setFilter(filter.includes(s) ? filter.filter((x) => x !== s) : [...filter, s]) }

  return (
    <>
      <h2 style={{ marginTop: 32 }}>Interactive Fraud Investigation Console</h2>
      <div className="chips" style={{ marginBottom: 14 }}>
        <span className="small muted" style={{ alignSelf: 'center', marginRight: 4 }}>Filter by triggered signals:</span>
        {Object.keys(weights).map((s) => (
          <button key={s} className={`chip ${filter.includes(s) ? 'on' : ''}`} onClick={() => toggle(s)}>
            {s}
          </button>
        ))}
      </div>
      <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 1.1fr) minmax(0, 1.9fr)' }}>
        <Card title="Flagged Reviews Roster" sub={`${examples.length} matches sorted by suspicion`} badge="Ranked Feed">
          <div style={{ maxHeight: 620, overflowY: 'auto' }}>
            {examples.slice(0, 150).map((e, i) => (
              <div key={e.review_id} className={`list-item ${e === r ? 'sel' : ''}`} onClick={() => setSel(i)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="small">
                    <span className="pill neg" style={{ marginRight: 6 }}>{fmt.num(e.suspicion_score, 1)} pts</span>
                    <b>{e.rating}★</b>
                  </span>
                  <span className="tiny">{e.review_date}</span>
                </div>
                <div className="small" style={{ fontWeight: 600, marginTop: 4 }}>{String(e.product_title || '').slice(0, 48)}…</div>
                <span className="tiny">{String(e.text || '').slice(0, 85)}…</span>
              </div>
            ))}
          </div>
        </Card>
        {r ? <ReviewExplain r={r} weights={weights} threshold={d.threshold} signalText={d.signal_text} c={c} />
          : <div className="empty">No review in this sample matches all selected signal criteria.</div>}
      </div>
    </>
  )
}

export default function FakeReviews() {
  const state = useData('fake')
  const c = useColors()

  return (
    <>
      <FeatureBanner
        image="images/fake-reviews.jpg"
        title="Fraud Forensics & Anomaly Shield"
        desc="Multi-signal forensic heuristic scoring and Spark MLlib KMeans reviewer clustering to uncover coordinated bursts, sentiment mismatch, and copy-paste rings."
        tags={['Heuristic Point Attribution', 'KMeans Clustering', 'Temporal Burst Detection', 'Zero Black-Box']}
      />

      <PageHead title="Fake Review Detection & Audit Trail" badge="Forensic Analytics">
        Unsupervised anomaly detection without ground-truth bias: transparent warning signals explain every suspicious flag.
      </PageHead>

      <Loaded state={state} what="fake review results">
        {(d) => {
          const dist = BUCKETS.map((b) => (d.distribution || []).find((x) => String(x.score_bucket) === b) || { score_bucket: b, pct: 0, count: 0 })
          const flagged = dist.filter((x) => ['3-4', '4.5+'].includes(x.score_bucket))
          const nFlag = flagged.reduce((s, x) => s + (x.count || 0), 0)
          const pFlag = flagged.reduce((s, x) => s + (x.pct || 0), 0)
          const prev = [...(d.prevalence || [])].reverse()
          const imp = d.impact_summary

          return (
            <>
              <div className="grid g4">
                <Stat label="Suspicious Reviews" value={fmt.int(nFlag)} note={`${fmt.pct(pFlag, 2)} of total volume`} icon="🚨" />
                <Stat label="Score Threshold" value={`≥ ${d.threshold}`} note="1 severe or 2+ compound signals" icon="🎯" />
                <Stat label="Reviewer Archetypes" value={(d.profiles || []).length || '–'} note="KMeans behavioral groups" icon="👥" />
                <Stat label="Recalibrated Ratings" value={imp ? fmt.int(imp.changed) : '–'}
                      note={imp ? `0.1+ delta · ${imp.drop} drop, ${imp.rise} rise` : ''} icon="⚖️" />
              </div>

              <div className="grid g2">
                <Card title="Signal Point Allocation" sub="Transparent additive points per heuristic violation" badge="Rule System">
                  <div className="table-wrap">
                    <table>
                      <thead><tr><th>Signal</th><th className="num">Points</th><th className="num">All Reviews</th><th className="num">Flagged</th></tr></thead>
                      <tbody>
                        {(d.prevalence || []).map((p) => (
                          <tr key={p.signal} title={d.signal_text[p.signal]}>
                            <td>
                              <b>{p.signal}</b>
                              <div className="tiny">{d.signal_text[p.signal]}</div>
                            </td>
                            <td className="num"><span className="pill neg">+{p.points}</span></td>
                            <td className="num">{fmt.pct(p.pct_of_all, 2)}</td>
                            <td className="num">{fmt.pct(p.pct_of_flagged)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>

                <div>
                  <Card title="Suspicion Score Histogram" sub="Reviews with score ≥ 3.0 trigger manual investigation queue" badge="Distribution">
                    <ResponsiveContainer width="100%" height={190}>
                      <BarChart data={dist} margin={{ top: 16, right: 8, left: -10, bottom: 0 }}>
                        <CartesianGrid vertical={false} stroke={c.grid} />
                        <XAxis dataKey="score_bucket" {...axisProps(c)} />
                        <YAxis {...axisProps(c)} unit="%" />
                        <Tooltip cursor={{ fill: c.grid, opacity: 0.2 }} content={<ChartTip format={(v, p) => `${fmt.pct(v, 2)} (${fmt.int(p.payload.count)} reviews)`} />} />
                        <Bar dataKey="pct" name="share of reviews" radius={[6, 6, 0, 0]} maxBarSize={48}>
                          {dist.map((x) => <Cell key={x.score_bucket} fill={['3-4', '4.5+'].includes(x.score_bucket) ? c.neg : c.series[0]} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>

                  <Card title="Signal Prevalence Across Catalog" badge="Frequency Analysis">
                    <ResponsiveContainer width="100%" height={210}>
                      <BarChart data={prev} layout="vertical" margin={{ top: 0, right: 16, left: 10, bottom: 0 }}>
                        <CartesianGrid horizontal={false} stroke={c.grid} />
                        <XAxis type="number" {...axisProps(c)} unit="%" />
                        <YAxis type="category" interval={0} dataKey="signal" width={140} {...axisProps(c)} />
                        <Tooltip cursor={{ fill: c.grid, opacity: 0.2 }} content={<ChartTip format={(v, p) => `${fmt.pct(v, 2)} (${fmt.int(p.payload.reviews)})`} />} />
                        <Bar dataKey="pct_of_all" name="share of all reviews" fill={c.series[1]} radius={[0, 4, 4, 0]} maxBarSize={14} />
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                </div>
              </div>

              {d.profiles && (
                <Card title="Reviewer Behavioral Archetypes (Spark KMeans)" sub="Identified automatically by clustering user-level rating frequency, dispersion, and sentiment divergence" badge="Unsupervised Profiling">
                  <div className="table-wrap">
                    <table>
                      <thead><tr><th>Archetype</th><th className="num">Cohort Size</th><th className="num">Avg Reviews</th><th className="num">Mean Rating</th>
                        <th className="num">Duplicate Rate</th><th className="num">Mismatch Rate</th></tr></thead>
                      <tbody>
                        {d.profiles.map((p) => (
                          <tr key={p.cluster}>
                            <td><b>{p.name}</b> <span className="pill tiny">Cluster #{p.cluster}</span></td>
                            <td className="num">{fmt.int(p.reviewers)}</td>
                            <td className="num">{fmt.num(p.n_reviews, 1)}</td>
                            <td className="num">{fmt.num(p.avg_rating)} ★</td>
                            <td className="num">{p.share_duplicate == null ? '–' : fmt.share(p.share_duplicate)}</td>
                            <td className="num">{p.share_mismatch == null ? '–' : fmt.share(p.share_mismatch)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              <Explorer d={d} c={c} />
            </>
          )
        }}
      </Loaded>
    </>
  )
}
