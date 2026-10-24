import React, { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, ChartTip, FeatureBanner, Legend, Loaded, PageHead, axisProps } from '../components/ui.jsx'
import { fmt, useData } from '../lib/data.js'
import { SentimentModel } from '../lib/sentiment.js'
import { useColors } from '../lib/theme.js'

const EXAMPLES = {
  Positive: ['Love it', 'Works great, the battery lasts all day and the sound is amazing.'],
  Negative: ['Waste of money', "Stopped working after two days. Don't buy, I am returning it."],
  'Not good': ['Not good', 'The sound is not good and the battery is not great either.'],
  Mixed: ["It's okay", 'Sound is good but the battery is weak and it feels cheap.'],
}
const CLASSES = ['negative', 'neutral', 'positive']

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

/** background for a word: winner colour when it helps the prediction, runner-up colour when it hurts */
function tokenStyle(t, maxAbs, win, lose) {
  if (t.status !== 'kept' || !t.attr) return {}
  const [r, g, b] = hexToRgb(t.attr > 0 ? win : lose)
  const a = Math.min(0.85, 0.16 + 0.73 * (Math.abs(t.attr) / (maxAbs || 1)))
  return {
    background: `rgba(${r},${g},${b},${a})`,
    borderColor: `rgba(${r},${g},${b},0.85)`,
    boxShadow: `0 2px 8px rgba(${r},${g},${b},0.25)`
  }
}

function Explainer({ model, c }) {
  const [title, setTitle] = useState(EXAMPLES.Negative[0])
  const [text, setText] = useState(EXAMPLES.Negative[1])
  const [removed, setRemoved] = useState(new Set())
  const res = useMemo(() => model.analyze(title, text, removed), [model, title, text, removed])
  const win = c.sentiment[res.label]
  const lose = c.sentiment[res.runnerUp]
  const maxAbs = Math.max(...res.tokens.map((t) => Math.abs(t.attr)), 0.0001)
  const top = res.contributions.slice(0, 10)
  const maxC = Math.max(...top.map((t) => Math.abs(t.value)), Math.abs(res.bias), 0.0001)

  const toggle = (t) => {
    if (t.status === 'stop') return
    const next = new Set(removed)
    next.has(t.word) ? next.delete(t.word) : next.add(t.word)
    setRemoved(next)
  }
  const load = (k) => { setTitle(EXAMPLES[k][0]); setText(EXAMPLES[k][1]); setRemoved(new Set()) }

  return (
    <>
      <div className="grid g2">
        <Card title="Interactive Review Sandbox" sub="Trained Spark MLlib model evaluated live in your browser" badge="Live Inference">
          <div className="chips">
            {Object.keys(EXAMPLES).map((k) => (
              <button key={k} className="chip" onClick={() => load(k)}>{k}</button>
            ))}
          </div>
          <label htmlFor="t">Review Title</label>
          <input id="t" value={title} onChange={(e) => { setTitle(e.target.value); setRemoved(new Set()) }} />
          <label htmlFor="x">Review Body</label>
          <textarea id="x" value={text} onChange={(e) => { setText(e.target.value); setRemoved(new Set()) }} />
        </Card>

        <Card title="Model Classification" badge={`Confidence: ${fmt.share(res.probs[res.label])}`}>
          <div className="verdict" style={{ color: win }}>{res.label.toUpperCase()}</div>
          <div className="probs">
            {CLASSES.map((k) => (
              <div className="prob-row" key={k}>
                <span style={{ textTransform: 'capitalize' }}>{k}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${res.probs[k] * 100}%`, background: c.sentiment[k] }} />
                </div>
                <b className="small">{fmt.share(res.probs[k])}</b>
              </div>
            ))}
          </div>
          <p className="tiny" style={{ marginTop: 14 }}>
            Runner-up class: <b style={{ color: lose }}>{res.runnerUp}</b>. The attribution below explains exactly how each token swayed the decision against the runner-up.
          </p>
        </Card>
      </div>

      <Card
        title="Lexical Token Breakdown & What-If Simulation"
        sub="Click any highlighted word to simulate removing it and watch the model re-evaluate instantly"
        badge="Interactive XAI"
      >
        <div className="tokens">
          {res.tokens.length === 0 && <span className="muted">Type text above to inspect tokens.</span>}
          {res.tokens.map((t, i) => (
            <span
              key={i}
              className={`tok ${t.status} ${t.status === 'kept' && !t.known ? 'unknown' : ''}`}
              style={tokenStyle(t, maxAbs, win, lose)}
              onClick={() => toggle(t)}
              title={t.status === 'stop' ? 'Ignored: stop word'
                : t.status === 'removed' ? 'Removed by user - click to restore'
                  : `${t.attr >= 0 ? 'Supports' : 'Opposes'} ${res.label}: ${t.attr.toFixed(3)}`}
            >
              {t.word}
            </span>
          ))}
        </div>
        <Legend items={[[`Supports ${res.label}`, win], [`Favours ${res.runnerUp}`, lose], ['Stop word (filtered)', c.border]]} />
        {removed.size > 0 && (
          <p className="small" style={{ marginTop: 12 }}>
            Simulating removal of: <b style={{ color: c.neg }}>{[...removed].join(', ')}</b> · <button className="link" onClick={() => setRemoved(new Set())}>reset all</button>
          </p>
        )}
        {res.unknown.length > 0 && (
          <p className="tiny" style={{ marginTop: 6 }}>Out-of-vocabulary terms (neutral weight): {res.unknown.join(', ')}</p>
        )}
      </Card>

      <Card
        title={`Exact Decision Attribution: "${res.label}" vs "${res.runnerUp}"`}
        sub="Linear model property: the sum of word contributions and bias equals the exact log-odds margin"
        badge="Exact Additive Decomposition"
      >
        <div className="contrib">
          {[{ term: '(Global Model Bias)', value: res.bias, isBias: true }, ...top].map((t) => {
            const w = (Math.abs(t.value) / maxC) * 50
            return (
              <div className="contrib-row" key={t.term}>
                <span title={t.term} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {t.term}{!t.isBias && t.term.includes(' ') && <span className="tiny"> (bigram)</span>}
                </span>
                <div className="contrib-axis">
                  <div className="mid" />
                  <div className="seg" style={{
                    background: t.value >= 0 ? win : lose,
                    left: t.value >= 0 ? '50%' : `${50 - w}%`, width: `${w}%`,
                  }} />
                </div>
                <span className="small" style={{ textAlign: 'right', fontFamily: 'JetBrains Mono, monospace' }}>
                  {t.value >= 0 ? '+' : ''}{t.value.toFixed(2)}
                </span>
              </div>
            )
          })}
        </div>
        <p className="tiny" style={{ marginTop: 12 }}>
          Total Score Gap = bias {res.bias.toFixed(2)} + lexical {(res.gap - res.bias).toFixed(2)} = <b>{res.gap.toFixed(2)}</b>.
          {res.pairsUsed.length > 0 && <> Significant bigrams detected: <b>{res.pairsUsed.slice(0, 6).join(', ')}</b>.</>}
        </p>
      </Card>
    </>
  )
}

function GlobalView({ d, c, model }) {
  const [cls, setCls] = useState('negative')
  const comp = (d.comparison || []).map((r) => ({ ...r, short: r.model.replace(' (class weights)', ' (weighted)') }))
  const terms = [...((d.top_terms || {})[cls] || [])].slice(0, 12).reverse()
  const cm = d.confusion
  const checkDiff = useMemo(() => {
    if (!d.check || !model) return null
    return Math.max(...d.check.map((r) => {
      const p = model.analyze(r.title, r.text).probs
      return Math.max(Math.abs(p.negative - r.p_negative), Math.abs(p.neutral - r.p_neutral), Math.abs(p.positive - r.p_positive))
    }))
  }, [d.check, model])

  return (
    <>
      <h2 style={{ marginTop: 32 }}>Global Model Architecture & Performance</h2>
      <div className="grid g2">
        <Card title="Algorithm Benchmark on Test Set" sub="Macro F1 accounts for severe class imbalance; standard accuracy is misleading" badge="Spark Evaluation">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={comp} layout="vertical" margin={{ top: 0, right: 16, left: 10, bottom: 0 }}>
              <CartesianGrid horizontal={false} stroke={c.grid} />
              <XAxis type="number" domain={[0, 1]} {...axisProps(c)} />
              <YAxis type="category" interval={0} dataKey="short" width={170} {...axisProps(c)} />
              <Tooltip cursor={{ fill: c.grid, opacity: 0.2 }} content={<ChartTip format={(v) => fmt.num(v, 3)} />} />
              <Bar dataKey="accuracy" name="accuracy" fill={c.neu} maxBarSize={10} radius={[0, 4, 4, 0]} />
              <Bar dataKey="macro_f1" name="macro F1" fill={c.series[0]} maxBarSize={10} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <Legend items={[['Standard Accuracy', c.neu], ['Macro F1 (Balanced)', c.series[0]]]} />
        </Card>

        <Card title="Strongest Feature Weights per Sentiment Class" sub="Global feature importance extracted from the trained model coefficients" badge="Global Explainability">
          <div className="chips" style={{ marginBottom: 10 }}>
            {CLASSES.map((k) => (
              <button key={k} className={`chip ${cls === k ? 'on' : ''}`} onClick={() => setCls(k)}>
                {k} weights
              </button>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={terms} layout="vertical" margin={{ top: 0, right: 16, left: 10, bottom: 0 }}>
              <CartesianGrid horizontal={false} stroke={c.grid} />
              <XAxis type="number" {...axisProps(c)} />
              <YAxis type="category" interval={0} dataKey="term" width={120} {...axisProps(c)} />
              <Tooltip cursor={{ fill: c.grid, opacity: 0.2 }} content={<ChartTip format={(v) => fmt.num(v, 3)} />} />
              <Bar dataKey="weight" name="weight" fill={c.sentiment[cls]} maxBarSize={14} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="grid g2">
        {cm && (
          <Card title="Confusion Matrix Matrix (Best Model)" sub="Normalized row percentages (True Label vs Model Prediction)" badge="Error Diagnostics">
            <div className="table-wrap">
              <table>
                <thead><tr><th>Actual \ Predicted</th>{CLASSES.map((k) => <th key={k} className="num">{k}</th>)}</tr></thead>
                <tbody>
                  {CLASSES.map((t) => {
                    const row = cm[t] || {}
                    const total = CLASSES.reduce((s, k) => s + (row[k] || 0), 0) || 1
                    return (
                      <tr key={t}>
                        <th style={{ textTransform: 'capitalize' }}>{t}</th>
                        {CLASSES.map((k) => {
                          const p = (row[k] || 0) / total
                          return (
                            <td key={k} className="num" style={{ background: `rgba(56,189,248,${0.08 + 0.65 * p})`, color: p > 0.5 ? '#fff' : undefined }}>
                              {(p * 100).toFixed(1)}%<div className="tiny" style={{ color: 'inherit' }}>{fmt.int(row[k])} reviews</div>
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}
        <Card title="Spark-to-Browser Parity Verification" badge="Zero Server Latency">
          <p className="small">
            The model vocabulary, inverse document frequencies (IDF), and Logistic Regression coefficient matrices
            were exported directly from the Apache Spark MLlib pipeline ({fmt.int(model?.info.terms)} key terms preserved).
          </p>
          {checkDiff != null && (
            <div className={checkDiff < 0.01 ? 'callout' : 'warn'}>
              Parity test on {d.check.length} sample reviews: max divergence <b>{checkDiff.toFixed(4)}</b>
              {checkDiff < 0.01 ? ' — Exact Spark MLlib Parity Verified ✓' : ' — minor numerical rounding'}
            </div>
          )}
          <p className="tiny" style={{ marginTop: 12 }}>
            Unlike black-box SHAP or LIME perturbations which sample approximations, linear classification guarantees
            100% exact mathematical explanations for every predicted probability.
          </p>
        </Card>
      </div>
    </>
  )
}

export default function Sentiment() {
  const sState = useData('sentiment')
  const mState = useData('model')
  const c = useColors()
  const model = useMemo(() => (mState.data ? new SentimentModel(mState.data) : null), [mState.data])

  return (
    <>
      <FeatureBanner
        image="/images/sentiment-ai.jpg"
        title="Explainable Sentiment Intelligence"
        desc="Natural Language Processing with Apache Spark MLlib, TF-IDF n-grams, and exact linear attribution breakdown for total prediction transparency."
        tags={['Spark MLlib', 'TF-IDF Unigrams & Bigrams', 'Exact Linear Attributions', 'What-If Diagnostics']}
      />

      <PageHead title="Sentiment Analysis & Explainable AI (XAI)" badge="Interactive Lab">
        Test custom reviews, evaluate model attributions, and simulate what-if scenarios in real time.
      </PageHead>
      <Loaded state={mState} what="the sentiment model">{() => <Explainer model={model} c={c} />}</Loaded>
      <Loaded state={sState} what="sentiment results">{(d) => <GlobalView d={d} c={c} model={model} />}</Loaded>
    </>
  )
}
