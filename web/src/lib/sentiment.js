/**
 * The Spark-trained sentiment model (Phase 4a), running in the browser, with exact explanations.
 *
 * Same steps as Spark: clean text -> words (2+ letters, stop words removed, negations kept)
 * -> words + word pairs -> TF-IDF -> Logistic Regression (3 classes) -> softmax.
 *
 * Explanation: Logistic Regression is linear, so the gap between the winning class and the
 * runner-up splits EXACTLY into one number per term plus a bias:
 *     logit[win] - logit[runner] = (b[win] - b[runner]) + sum_j (w[win][j] - w[runner][j]) * x_j
 * Each word's share = its single-word term + half of every word pair it belongs to.
 */
export function cleanText(title, text) {
  let c = `${title || ''} ${text || ''}`
  c = c.replace(/<[^>]+>/g, ' ')
  c = c.replace(/&#?[a-zA-Z0-9]+;/g, ' ')
  c = c.replace(/https?:\/\/\S+|www\.\S+/g, ' ')
  c = c.toLowerCase()
  c = c.replace(/n't\b/g, ' not')
  c = c.replace(/[^a-z ]/g, ' ')
  c = c.replace(/\s+/g, ' ')
  return c.trim()
}

export class SentimentModel {
  constructor(json) {
    this.classes = json.classes
    this.index = new Map(json.terms.map((t, i) => [t, i]))
    this.idf = json.idf
    this.coef = json.coef
    this.intercept = json.intercept
    this.stop = new Set(json.stop_words)
    this.info = { terms: json.terms.length, termsFull: json.terms_full, maxDiff: json.max_prob_diff_vs_spark }
  }

  /** removed: Set of words the user switched off (what-if test). */
  analyze(title, text, removed = new Set()) {
    const cleaned = cleanText(title, text)
    const words = cleaned ? cleaned.split(' ') : []
    const view = words.map((w) => ({
      word: w,
      status: w.length < 2 || this.stop.has(w) ? 'stop' : removed.has(w) ? 'removed' : 'kept',
      attr: 0,
      known: false,
    }))
    const kept = view.filter((v) => v.status === 'kept')

    // term counts: single words + consecutive pairs of the kept words
    const terms = new Map()
    const add = (term) => terms.set(term, (terms.get(term) || 0) + 1)
    kept.forEach((v) => add(v.word))
    for (let k = 0; k + 1 < kept.length; k++) add(`${kept[k].word} ${kept[k + 1].word}`)

    const C = this.classes.length
    const logits = [...this.intercept]
    const feats = []
    for (const [term, count] of terms) {
      const j = this.index.get(term)
      if (j === undefined) continue
      const x = count * this.idf[j]
      feats.push({ term, j, x, count })
      for (let c = 0; c < C; c++) logits[c] += this.coef[c][j] * x
    }
    const mx = Math.max(...logits)
    const ex = logits.map((l) => Math.exp(l - mx))
    const sum = ex.reduce((a, b) => a + b, 0)
    const probs = ex.map((e) => e / sum)
    const order = probs.map((p, i) => i).sort((a, b) => probs[b] - probs[a])
    const [win, runner] = order

    const diff = (j) => this.coef[win][j] - this.coef[runner][j]
    const contributions = feats
      .map((f) => ({ term: f.term, count: f.count, value: diff(f.j) * f.x, toWinner: this.coef[win][f.j] * f.x }))
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))

    // per-word share for highlighting (one occurrence at a time)
    const perOcc = (term) => {
      const j = this.index.get(term)
      return j === undefined ? 0 : diff(j) * this.idf[j]
    }
    kept.forEach((v, k) => {
      const uni = perOcc(v.word)
      v.known = this.index.has(v.word)
      v.attr = uni
      if (k > 0) v.attr += perOcc(`${kept[k - 1].word} ${v.word}`) / 2
      if (k + 1 < kept.length) v.attr += perOcc(`${v.word} ${kept[k + 1].word}`) / 2
    })

    return {
      cleaned,
      tokens: view,
      probs: Object.fromEntries(this.classes.map((c, i) => [c, probs[i]])),
      label: this.classes[win],
      runnerUp: this.classes[runner],
      bias: this.intercept[win] - this.intercept[runner],
      gap: logits[win] - logits[runner],
      contributions,
      pairsUsed: contributions.filter((c) => c.term.includes(' ')).map((c) => c.term),
      unknown: [...new Set(kept.filter((v) => !v.known).map((v) => v.word))],
    }
  }
}
