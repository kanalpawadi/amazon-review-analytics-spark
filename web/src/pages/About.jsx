import React, { useState } from 'react'
import { Card, PageHead } from '../components/ui.jsx'

const PIPELINE_STEPS = [
  { step: '01', name: 'Raw Ingestion', tech: 'Amazon 2023 JSON (43.9M)', desc: 'Multi-category e-commerce reviews & metadata' },
  { step: '02', name: 'HDFS Storage', tech: 'Hadoop 3.3 HDFS', desc: 'Distributed replication & fault tolerance' },
  { step: '03', name: 'Columnar Format', tech: 'Snappy Parquet', desc: 'Partitioned by year for fast partition pruning' },
  { step: '04', name: 'Data Warehouse', tech: 'Apache Hive 3.1', desc: 'Schema-on-read metastore tables' },
  { step: '05', name: 'Distributed Prep', tech: 'Apache Spark 3.5', desc: 'Text tokenization, negation retention, deduplication' },
  { step: '06', name: 'ML Intelligence', tech: 'Spark MLlib & ALS', desc: 'TF-IDF Logistic Regression, KMeans, Implicit ALS' },
  { step: '07', name: 'Explainable AI', tech: 'Exact Linear & Cosine XAI', desc: 'Lexical attributions and item-to-item explanations' },
  { step: '08', name: 'Interactive UI', tech: 'React 18 + Vite', desc: 'Zero-latency browser runtime & visual analytics' },
]

export default function About() {
  const [copied, setCopied] = useState(false)

  const copyBibtex = () => {
    const bib = `@misc{hou2024bridging,
  title={Bridging Language and Items for Retrieval and Recommendation},
  author={Yupeng Hou and Jiacheng Li and Zhankui He and An Yan and Xiusi Chen and Julian McAuley},
  year={2024},
  eprint={2403.03952},
  archivePrefix={arXiv},
  primaryClass={cs.IR}
}`
    navigator.clipboard?.writeText(bib)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <>
      <PageHead title="System Architecture & Methodology" badge="DKTE Research Project">
        End-to-end Big Data architecture analyzing 43.9 million customer reviews with Apache Spark, Hadoop HDFS, Apache Hive, and Explainable AI.
      </PageHead>

      <Card title="Distributed End-to-End Processing Pipeline" sub="Architectural progression from raw JSON data to explainable insights" badge="Data Flow">
        <div className="grid g4" style={{ marginTop: 14 }}>
          {PIPELINE_STEPS.map((s) => (
            <div key={s.step} className="card" style={{ background: 'var(--surface-2)', padding: '16px 18px', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span className="pill accent">{s.step}</span>
                <span className="tiny" style={{ fontFamily: 'JetBrains Mono, monospace' }}>{s.tech}</span>
              </div>
              <h3 style={{ fontSize: '0.98rem', margin: '4px 0 6px' }}>{s.name}</h3>
              <p className="tiny muted" style={{ margin: 0 }}>{s.desc}</p>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid g3">
        <Card title="Sentiment: Exact Additive XAI" badge="Spark MLlib">
          <p className="small">
            Multinomial Logistic Regression over TF-IDF n-grams is strictly linear. Consequently, the score gap
            between predicted label and runner-up is identically equal to the sum of term contributions plus global bias.
            This allows 100% exact, non-approximated attribution without SHAP/LIME sampling noise.
          </p>
        </Card>

        <Card title="Fake Reviews: Transparent Forensics" badge="Unsupervised & KMeans">
          <p className="small">
            Without reliable fake review labels in e-commerce, supervised classifiers overfit to synthetic patterns.
            Our multi-signal framework sums forensic points from 8 distinct behavioral anomalies (bursts, copy-paste,
            text-rating dissonance, outlier distance) with KMeans reviewer profiling.
          </p>
        </Card>

        <Card title="Recommendations: Item-to-Item XAI" badge="Implicit ALS">
          <p className="small">
            Matrix factorization computes 64-dimensional latent factor vectors for users and products. Rather than
            presenting black-box recommendations, candidate items are explained by identifying the highest cosine
            similarity product in the user's historical purchase record: <i>"Because you rated X"</i>.
          </p>
        </Card>
      </div>

      <div className="grid g2">
        <Card title="Methodological Safeguards & Limitations" badge="Scientific Rigor">
          <ul className="small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
            <li><b>Ground-Truth Boundaries:</b> Flagged reviews represent high statistical suspicion, not absolute legal fraud proof.</li>
            <li><b>Weak Supervision:</b> Sentiment ground-truth is derived from star ratings (1-2★ negative, 3★ neutral, 4-5★ positive), which carries inherent human rating noise.</li>
            <li><b>Catalog Sparsity:</b> The Amazon dataset has high sparsity (~0.01% density). Unseen cold-start users or newly listed products require content-based fallbacks.</li>
            <li><b>Explanatory Scope:</b> Attributions explain the mathematical mechanics of the model, not necessarily external psychological causation.</li>
          </ul>
        </Card>

        <Card title="Academic Team & Institutional Attribution" badge="DKTE TEI 2026-27">
          <p className="small">
            <b>Institution:</b> DKTE Society's Textile and Engineering Institute (An Autonomous Institute), Ichalkaranji.<br />
            <b>Department:</b> Department of Artificial Intelligence &amp; Data Science.<br />
            <b>Academic Year:</b> 2026–2027 · Final Year B.Tech Capstone Project.<br />
            <b>Project Guide:</b> Prof. P. N. Koshti.
          </p>
          <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span className="small"><b>Dataset Citation:</b> Amazon Reviews 2023 (McAuley Lab, UCSD)</span>
              <button className="link small" onClick={copyBibtex}>{copied ? '✓ Copied BibTeX' : 'Copy BibTeX'}</button>
            </div>
            <p className="tiny muted" style={{ margin: 0 }}>
              Y. Hou, J. Li, Z. He, A. Yan, X. Chen, J. McAuley, <i>"Bridging Language and Items for Retrieval and Recommendation"</i>, arXiv:2403.03952, 2024. Academic non-commercial research use.
            </p>
          </div>
        </Card>
      </div>
    </>
  )
}
