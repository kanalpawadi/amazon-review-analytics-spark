import { useEffect, useState } from 'react'

// Validated categorical palette (light / dark steps), fixed order: blue, orange, aqua, ...
const LIGHT = {
  series: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4'],
  pos: '#2a78d6', neu: '#8f8e89', neg: '#e34948',
  text: '#0b0b0b', text2: '#52514e', text3: '#7a7974', grid: '#e9e7e1', surface: '#ffffff',
}
const DARK = {
  series: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181'],
  pos: '#3987e5', neu: '#8a8984', neg: '#e66767',
  text: '#f0efec', text2: '#c3c2b7', text3: '#92918a', grid: '#2f2f2c', surface: '#1a1a19',
}

function isDark() {
  const forced = document.documentElement.dataset.theme
  if (forced) return forced === 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** Chart colours for the current theme (SVG attributes cannot use CSS variables). */
export function useColors() {
  const [dark, setDark] = useState(isDark)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => setDark(isDark())
    mq.addEventListener('change', update)
    const obs = new MutationObserver(update)
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => { mq.removeEventListener('change', update); obs.disconnect() }
  }, [])
  const c = dark ? DARK : LIGHT
  return { ...c, sentiment: { positive: c.pos, neutral: c.neu, negative: c.neg }, dark }
}

export function toggleTheme() {
  const root = document.documentElement
  const next = isDark() ? 'light' : 'dark'
  root.dataset.theme = next
  try { localStorage.setItem('theme', next) } catch { /* private mode */ }
}

export function restoreTheme() {
  try {
    const t = localStorage.getItem('theme')
    if (t) document.documentElement.dataset.theme = t
  } catch { /* private mode */ }
}
