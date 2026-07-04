// Painel de preferências (dropdown do header): idioma, tema, cores do
// viewer 3D e tela cheia.
import { useEffect, useState } from 'react'
import { usePrefs, DEFAULT_PREFS } from '../prefs.jsx'

function Row({ label, children }) {
  return (
    <div className="pf-row">
      <span className="pf-label">{label}</span>
      <div className="pf-control">{children}</div>
    </div>
  )
}

function Seg({ options, value, onChange }) {
  return (
    <div className="pf-seg">
      {options.map(([val, label]) => (
        <button key={val}
          className={`pf-seg-btn ${value === val ? 'active' : ''}`}
          onClick={() => onChange(val)}>
          {label}
        </button>
      ))}
    </div>
  )
}

export default function PrefsPanel({ onClose }) {
  const { prefs, setPref, t } = usePrefs()
  const [fs, setFs] = useState(!!document.fullscreenElement)

  useEffect(() => {
    const sync = () => setFs(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', sync)
    return () => document.removeEventListener('fullscreenchange', sync)
  }, [])

  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen()
    else document.documentElement.requestFullscreen().catch(() => {})
  }

  function resetColors() {
    setPref('fieldColor', DEFAULT_PREFS.fieldColor)
    setPref('blueColor', DEFAULT_PREFS.blueColor)
    setPref('yellowColor', DEFAULT_PREFS.yellowColor)
  }

  return (
    <div className="pf-panel">
      <div className="pf-title">
        {t('pf.title')}
        <button className="pf-close" onClick={onClose}>✕</button>
      </div>

      <Row label={t('pf.lang')}>
        <Seg value={prefs.lang} onChange={v => setPref('lang', v)}
          options={[['pt', 'Português'], ['en', 'English']]} />
      </Row>

      <Row label={t('pf.theme')}>
        <Seg value={prefs.theme} onChange={v => setPref('theme', v)}
          options={[['dark', t('pf.dark')], ['light', t('pf.light')]]} />
      </Row>

      <Row label={t('pf.field')}>
        <input type="color" className="pf-color" value={prefs.fieldColor}
          onChange={e => setPref('fieldColor', e.target.value)} />
      </Row>
      <Row label={t('pf.blue')}>
        <input type="color" className="pf-color" value={prefs.blueColor}
          onChange={e => setPref('blueColor', e.target.value)} />
      </Row>
      <Row label={t('pf.yellow')}>
        <input type="color" className="pf-color" value={prefs.yellowColor}
          onChange={e => setPref('yellowColor', e.target.value)} />
      </Row>

      <div className="pf-actions">
        <button className="pf-btn" onClick={resetColors}>
          {t('pf.resetcolors')}
        </button>
        <button className="pf-btn" onClick={toggleFullscreen}>
          {fs ? t('pf.fullscreen.exit') : t('pf.fullscreen.enter')}
        </button>
      </div>
    </div>
  )
}
