import React from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, ChartTip, HeroShowcase, Legend, Loaded, PageHead, Stat, axisProps } from '../components/ui.jsx'
import { fmt, useData } from '../lib/data.js'
import { useColors } from '../lib/theme.js'

const sentimentOf = (r) => (r >= 4 ? 'positive' : r === 3 ? 'neutral' : 'negative')

export default function Overview() {
  const state = useData('eda')
  const c = useColors()

  return (
    <>
      <HeroShowcase
        image="images/hero-banner.jpg"
        title="Amazon Product Review Intelligence & Analytics"
        desc="Big data analysis of Amazon Electronics reviews (43.9 million ratings in the full dataset) with Apache Spark, and an explanation for every prediction."
        badges={[
          { icon: '⚡', text: 'Apache Spark 3.5 Ingestion' },
          { icon: '📦', text: 'Electronics Category: 43.9M Total Ratings' },
          { icon: '🧠', text: 'Interactive Explainable AI' },
          { icon: '🎓', text: 'DKTE Final Year Project' }
        ]}
      />

      <PageHead title="Exploratory Data Analysis" badge="Sample: 1% of users · 431,302 reviews">
        Computed on a 1% sample of users (all of their reviews), cleaned with Apache Spark and queried with Spark SQL.
      </PageHead>

      <Loaded state={state} what="the overview">
        {(d) => {
          const o = d.overview || {}
          const ratings = (d.ratings || []).map((r) => ({ ...r, stars: `${r.rating}★`, s: sentimentOf(r.rating) }))
          const yearly = d.yearly || []
          const big = yearly.filter((y) => y.reviews >= 100)
          const cats = [...(d.categories || [])].reverse()

          return (
            <>
              <div className="grid g5">
                <Stat label="Reviews Sample" value={fmt.int(o.reviews)} note="Cleaned & tokenized" icon="💬" />
                <Stat label="Active Users" value={fmt.int(o.users)} note="User cohorts" icon="👥" />
                <Stat label="Catalog Products" value={fmt.int(o.products)} note="Unique ASINs" icon="🏷️" />
                <Stat label="Average Rating" value={`${fmt.num(o.avg_rating)} ★`} note="Skewed positive" icon="⭐" />
                <Stat label="Verified Purchases" value={fmt.pct(o.verified_pct)} note={`${o.first_review} – ${o.last_review}`} icon="🛡️" />
              </div>

              <div className="grid g2">
                <Card
                  title="Star Rating Distribution"
                  sub="Extreme positive skew: 5-star ratings represent the vast majority of volume"
                  badge="Class Imbalance"
                >
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={ratings} margin={{ top: 20, right: 8, left: -10, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke={c.grid} />
                      <XAxis dataKey="stars" {...axisProps(c)} />
                      <YAxis {...axisProps(c)} unit="%" />
                      <Tooltip cursor={{ fill: c.grid, opacity: 0.2 }} content={<ChartTip format={(v) => fmt.pct(v)} />} />
                      <Bar dataKey="pct" name="share of reviews" radius={[6, 6, 0, 0]} maxBarSize={56}
                           label={{ position: 'top', fill: c.text2, fontSize: 12, formatter: (v) => `${v}%` }}>
                        {ratings.map((r) => <Cell key={r.rating} fill={c.sentiment[r.s]} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <Legend items={[['Positive (4-5★)', c.pos], ['Neutral (3★)', c.neu], ['Negative (1-2★)', c.neg]]} />
                </Card>

                <Card
                  title="Top Product Categories"
                  sub="Volume distribution across primary electronics segments"
                  badge="Product Taxonomy"
                >
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={cats} layout="vertical" margin={{ top: 0, right: 16, left: 10, bottom: 0 }}>
                      <CartesianGrid horizontal={false} stroke={c.grid} />
                      <XAxis type="number" {...axisProps(c)} tickFormatter={(v) => fmt.int(v)} />
                      <YAxis type="category" interval={0} dataKey="main_category" width={150} {...axisProps(c)} />
                      <Tooltip cursor={{ fill: c.grid, opacity: 0.2 }}
                               content={<ChartTip format={(v, p) => `${fmt.int(v)} reviews · avg ${fmt.num(p.payload.avg_rating)}★`} />} />
                      <Bar dataKey="reviews" name="reviews" fill={c.series[0]} radius={[0, 6, 6, 0]} maxBarSize={18} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </div>

              <div className="grid g2">
                <Card
                  title="Historical Review Volume (1998 - 2023)"
                  sub="Massive acceleration during 2020 e-commerce peak"
                  badge="Temporal Growth"
                >
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={yearly} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke={c.grid} />
                      <XAxis dataKey="year" {...axisProps(c)} />
                      <YAxis {...axisProps(c)} tickFormatter={(v) => fmt.int(v)} />
                      <Tooltip cursor={{ fill: c.grid, opacity: 0.2 }} content={<ChartTip format={fmt.int} />} />
                      <Bar dataKey="reviews" name="reviews" fill={c.series[0]} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>

                <Card
                  title="Rating Trend Stability"
                  sub="Average rating trend for years with 100+ recorded reviews"
                  badge="Rating Dynamics"
                >
                  <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={big} margin={{ top: 12, right: 12, left: -10, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke={c.grid} />
                      <XAxis dataKey="year" {...axisProps(c)} />
                      <YAxis domain={['auto', 'auto']} {...axisProps(c)} />
                      <Tooltip content={<ChartTip format={(v) => `${fmt.num(v)} ★`} />} />
                      <Line dataKey="avg_rating" name="average rating" stroke={c.series[1]} strokeWidth={3}
                            dot={{ r: 4, fill: c.series[1] }} activeDot={{ r: 6 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>
              </div>

              <div className="grid g2">
                {['positive', 'negative'].map((s) => {
                  const words = [...((d.top_words || {})[s] || [])].slice(0, 12).reverse()
                  return (
                    <Card
                      key={s}
                      title={`Lexical Salience in ${s.toUpperCase()} Reviews`}
                      sub={s === 'negative' ? 'Crucial: "not" negations were specifically preserved during Big Data preprocessing' : 'Top discriminative terms after stop-word filtering'}
                      badge={s === 'positive' ? 'Positive TF-IDF' : 'Negative TF-IDF'}
                    >
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={words} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
                          <CartesianGrid horizontal={false} stroke={c.grid} />
                          <XAxis type="number" {...axisProps(c)} tickFormatter={(v) => fmt.int(v)} />
                          <YAxis type="category" interval={0} dataKey="word" width={70} {...axisProps(c)} />
                          <Tooltip cursor={{ fill: c.grid, opacity: 0.2 }} content={<ChartTip format={fmt.int} />} />
                          <Bar dataKey="count" name="times used" fill={c.sentiment[s]} radius={[0, 6, 6, 0]} maxBarSize={16} />
                        </BarChart>
                      </ResponsiveContainer>
                    </Card>
                  )
                })}
              </div>
            </>
          )
        }}
      </Loaded>
    </>
  )
}
