// Preferências do app (idioma, tema, cores do viewer) — persistidas em
// localStorage e distribuídas por contexto. `t()` traduz pela língua ativa.
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { translate } from './i18n'

export const DEFAULT_PREFS = {
  lang: 'pt',              // 'pt' | 'en'
  theme: 'dark',           // 'dark' | 'light'
  fieldColor: '#236b23',   // verde do gramado (viewer 3D)
  blueColor: '#3b82f6',    // cor do time azul
  yellowColor: '#eab308',  // cor do time amarelo
}

const KEY = 'rcj_prefs'

function load() {
  try {
    return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(KEY) || '{}') }
  } catch {
    return { ...DEFAULT_PREFS }
  }
}

const PrefsContext = createContext(null)

export function PrefsProvider({ children }) {
  const [prefs, setPrefs] = useState(load)

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(prefs))
    document.documentElement.dataset.theme = prefs.theme
    document.documentElement.lang = prefs.lang === 'pt' ? 'pt-BR' : 'en'
  }, [prefs])

  const setPref = useCallback((key, value) =>
    setPrefs(p => ({ ...p, [key]: value })), [])

  const t = useCallback((key, ...args) =>
    translate(prefs.lang, key, ...args), [prefs.lang])

  return (
    <PrefsContext.Provider value={{ prefs, setPref, t }}>
      {children}
    </PrefsContext.Provider>
  )
}

export function usePrefs() {
  return useContext(PrefsContext)
}
