import { useEffect, useState } from 'react'

const cache = {}

/** Load public/data/<name>.json once and share it between pages. */
export function useData(name) {
  const [state, setState] = useState(() => cache[name] || { loading: true })
  useEffect(() => {
    if (cache[name]) return
    let alive = true
    fetch(`${import.meta.env.BASE_URL}data/${name}.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`))))
      .then((data) => { cache[name] = { data }; if (alive) setState(cache[name]) })
      .catch((error) => { if (alive) setState({ error }) })
    return () => { alive = false }
  }, [name])
  return state
}

export const fmt = {
  int: (v) => (v == null ? '–' : Math.round(v).toLocaleString('en-IN')),
  pct: (v, d = 1) => (v == null ? '–' : `${Number(v).toFixed(d)}%`),
  num: (v, d = 2) => (v == null ? '–' : Number(v).toFixed(d)),
  share: (v, d = 0) => (v == null ? '–' : `${(v * 100).toFixed(d)}%`),
}
