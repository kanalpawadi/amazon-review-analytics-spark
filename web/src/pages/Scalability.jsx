import React, { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, ChartTip, FeatureBanner, Legend, Loaded, PageHead, axisProps } from '../components/ui.jsx'
import { fmt, useData } from '../lib/data.js'
import { useColors } from '../lib/theme.js'

const STEP_TEXT = {
  sql_aggregation: 'Spark SQL distributed group-by & aggregation over Parquet storage',
  text_cleaning: 'Phase 2 regex tokenization, punctuation strip, and negation preservation (CPU bound)',
  sentiment_scoring: 'TF-IDF Vectorization + Logistic Regression inference over millions of reviews (ML inference)',
  als_training: 'Iterative Alternating Least Squares matrix factorization (5 iterations, shuffle heavy)',
}

function View({ runs, c }) {
  const steps = [...new Set(runs.map((r) => r.step))]
  const [step, setStep] = useState(steps[0])
  const cores = [...new Set(runs.map((r) => r.cores))].sort((a, b) => a - b)
  const fracs = [...new Set(runs.map((r) => r.data_fraction))].sort((a, b) => a - b)
  const rows = useMemo(() => fracs.map((f) => {
    const o = { fraction: `${Math.round(f * 100)}%` }
    cores.forEach((k) => { o[`c${k}`] = runs.find((r) => r.step === step && r.data_fraction === f && r.cores === k)?.seconds })
    return o
  }), [runs, step])
  const base = cores[0]
  const full = fracs[fracs.length - 1]
  const speed = cores.map((k) => {
    const t1 = runs.find((r) => r.step === step && r.data_fraction === full && r.cores === base)?.seconds
    const tk = runs.find((r) => r.step === step && r.data_fraction === full && r.cores === k)?.seconds
    return { cores: k, seconds: tk, speedup: t1 && tk ? t1 / tk : null, ideal: k / base }
  })

  return (
    <>
      {runs[0]?.platform && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <span className="pill accent">Compute Infrastructure</span>
          <span className="small muted">Benchmarked on: <b style={{ color: 'var(--text)' }}>{runs[0].platform}</b></span>
        </div>
      )}
      <div className="chips" style={{ marginBottom: 14 }}>
        {steps.map((s) => (
          <button key={s} className={`chip ${s === step ? 'on' : ''}`} onClick={() => setStep(s)}>
            {s.replace('_', ' ').toUpperCase()}
          </button>
        ))}
      </div>
      <p className="small muted" style={{ marginBottom: 18 }}>{STEP_TEXT[step]}</p>

      <div className="grid g2">
        <Card title="Execution Time vs Data Ingestion Fraction" sub="Runtime progression across worker core counts (lower is faster)" badge="Core Scaling">
          <ResponsiveContainer width="100%" height={290}>
            <LineChart data={rows} margin={{ top: 12, right: 16, left: -6, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={c.grid} />
              <XAxis dataKey="fraction" {...axisProps(c)} />
              <YAxis {...axisProps(c)} unit="s" />
              <Tooltip content={<ChartTip format={(v) => `${fmt.int(v)} s`} />} />
              {cores.map((k, i) => (
                <Line
                  key={k}
                  dataKey={`c${k}`}
                  name={`${k} ${k === 1 ? 'core' : 'cores'}`}
                  stroke={c.series[i % c.series.length]}
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <Legend items={cores.map((k, i) => [`${k} ${k === 1 ? 'core' : 'cores'}`, c.series[i % c.series.length]])} />
        </Card>

        <Card title={`Speed-Up & Efficiency on 100% Data`} sub={`Baseline core configuration (${base} core); Ideal = Amdahl Linear Upper Bound`} badge="Amdahl Analysis">
          <div className="table-wrap">
            <table>
              <thead><tr><th>Worker Cores</th><th className="num">Runtime</th><th className="num">Speed-up</th><th className="num">Ideal</th><th className="num">Parallel Efficiency</th></tr></thead>
              <tbody>
                {speed.map((s) => (
                  <tr key={s.cores}>
                    <td><b>{s.cores} {s.cores === 1 ? 'Core' : 'Cores'}</b></td>
                    <td className="num">{fmt.int(s.seconds)} s</td>
                    <td className="num"><b style={{ color: 'var(--accent)', fontFamily: 'JetBrains Mono, monospace' }}>{s.speedup ? `${s.speedup.toFixed(2)}×` : '–'}</b></td>
                    <td className="num" style={{ fontFamily: 'JetBrains Mono, monospace' }}>{s.ideal.toFixed(1)}×</td>
                    <td className="num">
                      {s.speedup ? (
                        <span className={`pill ${s.speedup / s.ideal > 0.7 ? 'pos' : 'neu'}`}>
                          {fmt.share(s.speedup / s.ideal)}
                        </span>
                      ) : '–'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="tiny" style={{ marginTop: 12 }}>
            Amdahl's Law Effect: Shuffle network I/O, HDFS serialization, and driver orchestration represent non-parallelizable bottlenecks,
            capping theoretical linear speedup in distributed clusters.
          </p>
        </Card>
      </div>
    </>
  )
}

export default function Scalability() {
  const state = useData('scalability')
  const c = useColors()

  return (
    <>
      <FeatureBanner
        image="/images/scalability.jpg"
        title="Distributed Cluster Scaling & Dataproc Benchmarks"
        desc="Empirical performance benchmarks measuring execution time, speedup ratio, and parallel efficiency across multi-core Spark nodes."
        tags={['Apache Spark 3.5', 'Hadoop HDFS', 'Dataproc Cluster', 'Amdahl Law Benchmarks']}
      />

      <PageHead title="Distributed Cluster Scalability" badge="Dataproc Telemetry">
        Empirical evaluation of Apache Spark scaling across varying data fractions and CPU worker allocations.
      </PageHead>
      <Loaded state={state} what="scalability runs">
        {(d) => (d.runs && d.runs.length
          ? <View runs={d.runs} c={c} />
          : <div className="empty">No scalability runs yet recorded in the export data.</div>)}
      </Loaded>
    </>
  )
}
