import { useState, useEffect, useCallback, useRef } from 'react'
import yaml from 'js-yaml'
import RobotPreview from './components/RobotPreview'
import SimViewer   from './components/SimViewer'
import PrefsPanel  from './components/PrefsPanel'
import { API_BASE } from './config'
import { checkForAppUpdate } from './updater'
import { usePrefs } from './prefs.jsx'
import './App.css'

// ── Default config ────────────────────────────────────────────────────────────

const DEFAULT_ROBOT = {
  robot: {
    name: 'New Robot',
    body:   { shape: 'circle', radius: 0.11, mass: 1.0, max_speed: 1.5 },
    wheels: { type: 'omnidirectional', count: 4, positions: [45, 135, 225, 315] },
    sensors: {
      ir_ring:      { count: 16, range: 1.5, noise_std: 0.05 },
      compass:      { noise_std: 2.0 },
      ultrasound:   { count: 4, directions: [0, 90, 180, 270], range: 2.0, noise_std: 0.03 },
      line_sensors: { count: 4, positions: [[0.09, 0], [-0.09, 0], [0, 0.09], [0, -0.09]] },
    },
    kicker: { force: 5.0, cooldown: 2.0 },
  },
}

// ── Small UI primitives ───────────────────────────────────────────────────────

function Section({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="section">
      <button className="section-header" onClick={() => setOpen(o => !o)}>
        <span className="chevron">{open ? '▾' : '▸'}</span>
        {title}
      </button>
      {open && <div className="section-body">{children}</div>}
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div className="field">
      <label className="field-label">
        {label}
        {hint && <span className="field-hint">{hint}</span>}
      </label>
      <div className="field-control">{children}</div>
    </div>
  )
}

function Slider({ value, min, max, step = 0.01, unit = '', onChange }) {
  return (
    <div className="slider-row">
      <input type="range" min={min} max={max} step={step}
        value={value} onChange={e => onChange(parseFloat(e.target.value))}
      />
      <span className="slider-value">{Number(value).toFixed(step < 1 ? 2 : 0)}{unit}</span>
    </div>
  )
}

function NumInput({ value, min, max, step = 0.01, onChange }) {
  return (
    <input type="number" className="num-input"
      value={value} min={min} max={max} step={step}
      onChange={e => onChange(parseFloat(e.target.value) || 0)}
    />
  )
}

function Tag({ children, active, onClick, color }) {
  return (
    <button className={`tag ${active ? 'tag-active' : ''}`}
      style={active && color ? { background: color, borderColor: color } : {}}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const { t } = usePrefs()
  const [tab, setTab]             = useState('builder')  // 'builder' | 'viewer'
  const [config, setConfig]       = useState(DEFAULT_ROBOT)
  const [robotList, setRobotList] = useState([])
  const [status, setStatus]       = useState(null)   // { type: 'ok'|'err', msg }
  const [loading, setLoading]     = useState(false)
  const [prefsOpen, setPrefsOpen] = useState(false)
  const [meshList, setMeshList]   = useState([])
  const fileRef = useRef(null)

  const r = config.robot
  const league = r.league ?? 'infrared'

  // Helper: update any nested path in config.robot
  const set = useCallback((path, value) => {
    setConfig(prev => {
      const robot = structuredClone(prev.robot)
      let obj = robot
      for (let i = 0; i < path.length - 1; i++) {
        if (obj[path[i]] === undefined) obj[path[i]] = {}
        obj = obj[path[i]]
      }
      obj[path[path.length - 1]] = value
      return { robot }
    })
  }, [])

  // Auto-update (só no app desktop Tauri; no-op no navegador)
  useEffect(() => {
    checkForAppUpdate().catch(() => {})
  }, [])

  // Fetch robot + mesh lists from server
  useEffect(() => {
    fetch(`${API_BASE}/api/robots`)
      .then(r => r.json())
      .then(setRobotList)
      .catch(() => {})
    fetch(`${API_BASE}/api/meshes`)
      .then(r => r.json())
      .then(setMeshList)
      .catch(() => {})
  }, [])

  function notify(type, msg) {
    setStatus({ type, msg })
    setTimeout(() => setStatus(null), 3000)
  }

  async function loadRobot(name) {
    try {
      const res  = await fetch(`${API_BASE}/api/robots/${name}`)
      const data = await res.json()
      setConfig(data)
      notify('ok', t('st.loaded', name))
    } catch {
      notify('err', t('st.loadfail'))
    }
  }

  function importYaml(ev) {
    const file = ev.target.files?.[0]
    ev.target.value = ''            // permite re-importar o mesmo arquivo
    if (!file) return
    file.text().then(text => {
      const data = yaml.load(text)
      if (!data || typeof data !== 'object' || !data.robot)
        throw new Error('missing robot key')
      setConfig(data)
      setTab('builder')
      notify('ok', t('st.imported', data.robot.name ?? file.name))
    }).catch(() => notify('err', t('st.importfail')))
  }

  async function saveRobot() {
    const name = r.name.trim().toLowerCase().replace(/\s+/g, '_')
    if (!name) return notify('err', t('st.noname'))
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/robots/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (!res.ok) throw new Error()
      notify('ok', t('st.saved', name))
      const list = await fetch(`${API_BASE}/api/robots`).then(r => r.json())
      setRobotList(list)
    } catch {
      notify('err', t('st.savefail'))
    } finally {
      setLoading(false)
    }
  }

  function downloadYaml() {
    const name = r.name.trim().toLowerCase().replace(/\s+/g, '_') || 'robot'
    const text = yaml.dump(config, { indent: 2, sortKeys: false })
    const blob = new Blob([text], { type: 'text/yaml' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = `${name}.yaml`; a.click()
    URL.revokeObjectURL(url)
  }

  function newRobot() { setConfig(structuredClone(DEFAULT_ROBOT)) }

  // ── Form sections ─────────────────────────────────────────────────────────

  function BasicSection() {
    return (
      <Section title={t('sec.identity')}>
        <Field label={t('f.name')}>
          <input className="text-input" value={r.name}
            onChange={e => set(['name'], e.target.value)}
            placeholder="My Robot"
          />
        </Field>
        <Field label={t('f.league')} hint={t('f.league.hint')}>
          <div className="tag-group">
            <Tag active={league === 'infrared'}
              onClick={() => set(['league'], 'infrared')}>{t('f.infrared')}</Tag>
            <Tag active={league === 'vision'}
              onClick={() => set(['league'], 'vision')}>{t('f.vision')}</Tag>
          </div>
        </Field>
      </Section>
    )
  }

  function BodySection() {
    const b = r.body
    return (
      <Section title={t('sec.body')}>
        <Field label={t('f.shape')}>
          <div className="tag-group">
            <Tag active={b.shape === 'circle'}  onClick={() => set(['body', 'shape'], 'circle')}>{t('f.circle')}</Tag>
            <Tag active={b.shape === 'rectangle'} onClick={() => set(['body', 'shape'], 'rectangle')}>{t('f.rect')}</Tag>
          </div>
        </Field>

        {b.shape === 'circle' ? (
          <Field label={t('f.radius')}
            hint={league === 'vision' ? 'max 0.09 m' : 'max 0.11 m'}>
            <Slider value={b.radius} min={0.05}
              max={league === 'vision' ? 0.09 : 0.11} step={0.005} unit=" m"
              onChange={v => set(['body', 'radius'], v)} />
          </Field>
        ) : (
          <>
            <Field label={t('f.width')}>
              <Slider value={b.width ?? 0.20} min={0.10} max={0.22} step={0.01} unit=" m"
                onChange={v => set(['body', 'width'], v)} />
            </Field>
            <Field label={t('f.height')}>
              <Slider value={b.height ?? 0.18} min={0.10} max={0.22} step={0.01} unit=" m"
                onChange={v => set(['body', 'height'], v)} />
            </Field>
          </>
        )}

        <Field label={t('f.mass')}
          hint={league === 'infrared' ? 'max 1.5 kg' : undefined}>
          <Slider value={b.mass} min={0.5}
            max={league === 'infrared' ? 1.5 : 3.0} step={0.05} unit=" kg"
            onChange={v => set(['body', 'mass'], v)} />
        </Field>
        <Field label={t('f.maxspeed')}>
          <Slider value={b.max_speed} min={0.3} max={2.5} step={0.05} unit=" m/s"
            onChange={v => set(['body', 'max_speed'], v)} />
        </Field>
      </Section>
    )
  }

  function WheelsSection() {
    const w = r.wheels
    const isOmni = w.type === 'omnidirectional'

    function addWheel() {
      const newAngle = ((w.positions?.length ?? 0) * 360 / ((w.count ?? 4) + 1))
      set(['wheels', 'positions'], [...(w.positions ?? []), Math.round(newAngle)])
      set(['wheels', 'count'], (w.count ?? 4) + 1)
    }
    function removeWheel(i) {
      const p = (w.positions ?? []).filter((_, j) => j !== i)
      set(['wheels', 'positions'], p)
      set(['wheels', 'count'], p.length)
    }

    return (
      <Section title={t('sec.drive')}>
        <Field label={t('f.type')}>
          <div className="tag-group">
            <Tag active={isOmni} onClick={() => set(['wheels', 'type'], 'omnidirectional')}>{t('f.omni')}</Tag>
            <Tag active={!isOmni} onClick={() => set(['wheels', 'type'], 'differential')}>{t('f.diff')}</Tag>
          </div>
        </Field>

        {isOmni && (
          <Field label={t('f.wheels')}>
            <div className="list-items">
              {(w.positions ?? []).map((angle, i) => (
                <div key={i} className="list-item">
                  <span className="list-item-label">W{i + 1}</span>
                  <NumInput value={angle} min={0} max={359} step={1}
                    onChange={v => {
                      const p = [...(w.positions ?? [])]
                      p[i] = v
                      set(['wheels', 'positions'], p)
                    }}
                  />
                  <span className="unit">°</span>
                  <button className="icon-btn danger" onClick={() => removeWheel(i)}>×</button>
                </div>
              ))}
              <button className="add-btn" onClick={addWheel}>{t('f.addwheel')}</button>
            </div>
          </Field>
        )}

        {!isOmni && (
          <Field label={t('f.wheelbase')} hint={t('f.wheelbase.hint')}>
            <Slider value={w.wheel_base ?? 0.15} min={0.08} max={0.20} step={0.01} unit=" m"
              onChange={v => set(['wheels', 'wheel_base'], v)} />
          </Field>
        )}
      </Section>
    )
  }

  function SensorsSection() {
    const s = r.sensors

    function addUltrasound() {
      const dirs = [...(s.ultrasound?.directions ?? [])]
      dirs.push(0)
      set(['sensors', 'ultrasound', 'directions'], dirs)
      set(['sensors', 'ultrasound', 'count'], dirs.length)
    }
    function removeUltrasound(i) {
      const dirs = (s.ultrasound?.directions ?? []).filter((_, j) => j !== i)
      set(['sensors', 'ultrasound', 'directions'], dirs)
      set(['sensors', 'ultrasound', 'count'], dirs.length)
    }
    function addLineSensor() {
      const positions = [...(s.line_sensors?.positions ?? []), [0.0, 0.0]]
      set(['sensors', 'line_sensors', 'positions'], positions)
      set(['sensors', 'line_sensors', 'count'], positions.length)
    }
    function removeLineSensor(i) {
      const positions = (s.line_sensors?.positions ?? []).filter((_, j) => j !== i)
      set(['sensors', 'line_sensors', 'positions'], positions)
      set(['sensors', 'line_sensors', 'count'], positions.length)
    }

    return (
      <Section title={t('sec.sensors')}>
        {/* IR Ring */}
        <div className="subsection">
          <div className="subsection-title">{t('sub.ir')}</div>
          <Field label={t('f.sectors')}>
            <div className="tag-group">
              {[8, 12, 16, 24].map(n => (
                <Tag key={n} active={s.ir_ring?.count === n}
                  onClick={() => set(['sensors', 'ir_ring', 'count'], n)}>
                  {n}
                </Tag>
              ))}
            </div>
          </Field>
          <Field label={t('f.range')}>
            <Slider value={s.ir_ring?.range ?? 1.5} min={0.5} max={3.0} step={0.1} unit=" m"
              onChange={v => set(['sensors', 'ir_ring', 'range'], v)} />
          </Field>
          <Field label={t('f.noise')}>
            <Slider value={s.ir_ring?.noise_std ?? 0.05} min={0} max={0.3} step={0.01}
              onChange={v => set(['sensors', 'ir_ring', 'noise_std'], v)} />
          </Field>
        </div>

        {/* Compass */}
        <div className="subsection">
          <div className="subsection-title">{t('sub.compass')}</div>
          <Field label={t('f.noise')} hint={t('f.noise.deg')}>
            <Slider value={s.compass?.noise_std ?? 2.0} min={0} max={15} step={0.5} unit="°"
              onChange={v => set(['sensors', 'compass', 'noise_std'], v)} />
          </Field>
        </div>

        {/* Ultrasound */}
        <div className="subsection">
          <div className="subsection-title">{t('sub.us')}</div>
          <Field label={t('f.range')}>
            <Slider value={s.ultrasound?.range ?? 2.0} min={0.5} max={4.0} step={0.1} unit=" m"
              onChange={v => set(['sensors', 'ultrasound', 'range'], v)} />
          </Field>
          <Field label={t('f.noise')}>
            <Slider value={s.ultrasound?.noise_std ?? 0.03} min={0} max={0.2} step={0.01}
              onChange={v => set(['sensors', 'ultrasound', 'noise_std'], v)} />
          </Field>
          <Field label={t('f.directions')}>
            <div className="list-items">
              {(s.ultrasound?.directions ?? []).map((dir, i) => (
                <div key={i} className="list-item">
                  <span className="list-item-label">US{i + 1}</span>
                  <NumInput value={dir} min={-180} max={180} step={5}
                    onChange={v => {
                      const dirs = [...(s.ultrasound?.directions ?? [])]
                      dirs[i] = v
                      set(['sensors', 'ultrasound', 'directions'], dirs)
                    }}
                  />
                  <span className="unit">°</span>
                  <button className="icon-btn danger" onClick={() => removeUltrasound(i)}>×</button>
                </div>
              ))}
              <button className="add-btn" onClick={addUltrasound}>{t('f.addsensor')}</button>
            </div>
          </Field>
        </div>

        {/* Line sensors */}
        <div className="subsection">
          <div className="subsection-title">{t('sub.lines')}</div>
          <Field label={t('f.positions')} hint={t('f.positions.hint')}>
            <div className="list-items">
              {(s.line_sensors?.positions ?? []).map(([lx, ly], i) => (
                <div key={i} className="list-item">
                  <span className="list-item-label">L{i + 1}</span>
                  <NumInput value={lx} min={-0.11} max={0.11} step={0.01}
                    onChange={v => {
                      const p = (s.line_sensors?.positions ?? []).map((pos, j) =>
                        j === i ? [v, pos[1]] : pos)
                      set(['sensors', 'line_sensors', 'positions'], p)
                    }}
                  />
                  <NumInput value={ly} min={-0.11} max={0.11} step={0.01}
                    onChange={v => {
                      const p = (s.line_sensors?.positions ?? []).map((pos, j) =>
                        j === i ? [pos[0], v] : pos)
                      set(['sensors', 'line_sensors', 'positions'], p)
                    }}
                  />
                  <button className="icon-btn danger" onClick={() => removeLineSensor(i)}>×</button>
                </div>
              ))}
              <button className="add-btn" onClick={addLineSensor}>{t('f.addsensor')}</button>
            </div>
          </Field>
        </div>

        {/* Ball velocity (B5) */}
        <div className="subsection">
          <div className="subsection-title">{t('sub.ballvel')}</div>
          <Field label={t('f.enable')} hint={t('sub.ballvel.hint')}>
            <label className="toggle">
              <input type="checkbox" checked={!!s.ball_velocity}
                onChange={e => set(['sensors', 'ball_velocity'],
                  e.target.checked ? { noise_std: 0.05 } : null)}
              />
              <span className="toggle-track" />
            </label>
          </Field>
          {s.ball_velocity && (
            <Field label={t('f.noise')}>
              <Slider value={s.ball_velocity.noise_std ?? 0.05} min={0} max={0.3}
                step={0.01}
                onChange={v => set(['sensors', 'ball_velocity', 'noise_std'], v)} />
            </Field>
          )}
        </div>

        {/* Opponent lidar (B2) */}
        <div className="subsection">
          <div className="subsection-title">{t('sub.lidar')}</div>
          <Field label={t('f.enable')} hint={t('sub.lidar.hint')}>
            <label className="toggle">
              <input type="checkbox" checked={!!s.opponent_lidar}
                onChange={e => set(['sensors', 'opponent_lidar'],
                  e.target.checked
                    ? { directions: [-40, -20, 0, 20, 40], range: 1.0, noise_std: 0.02 }
                    : null)}
              />
              <span className="toggle-track" />
            </label>
          </Field>
          {s.opponent_lidar && (
            <>
              <Field label={t('f.range')}>
                <Slider value={s.opponent_lidar.range ?? 1.0} min={0.3} max={3.0}
                  step={0.1} unit=" m"
                  onChange={v => set(['sensors', 'opponent_lidar', 'range'], v)} />
              </Field>
              <Field label={t('f.noise')}>
                <Slider value={s.opponent_lidar.noise_std ?? 0.02} min={0} max={0.2}
                  step={0.01}
                  onChange={v => set(['sensors', 'opponent_lidar', 'noise_std'], v)} />
              </Field>
              <Field label={t('f.directions')}>
                <div className="list-items">
                  {(s.opponent_lidar.directions ?? []).map((dir, i) => (
                    <div key={i} className="list-item">
                      <span className="list-item-label">L{i + 1}</span>
                      <NumInput value={dir} min={-180} max={180} step={5}
                        onChange={v => {
                          const dirs = [...(s.opponent_lidar.directions ?? [])]
                          dirs[i] = v
                          set(['sensors', 'opponent_lidar', 'directions'], dirs)
                        }}
                      />
                      <span className="unit">°</span>
                      <button className="icon-btn danger" onClick={() => {
                        const dirs = (s.opponent_lidar.directions ?? [])
                          .filter((_, j) => j !== i)
                        set(['sensors', 'opponent_lidar', 'directions'], dirs)
                      }}>×</button>
                    </div>
                  ))}
                  <button className="add-btn" onClick={() =>
                    set(['sensors', 'opponent_lidar', 'directions'],
                        [...(s.opponent_lidar.directions ?? []), 0])}>
                    {t('f.addsensor')}
                  </button>
                </div>
              </Field>
            </>
          )}
        </div>
      </Section>
    )
  }

  function KickerSection() {
    const k = r.kicker
    const hasKicker = !!k
    return (
      <Section title={t('sec.kicker')} defaultOpen>
        <Field label={t('f.enable')}>
          <label className="toggle">
            <input type="checkbox" checked={hasKicker}
              onChange={e => set(['kicker'], e.target.checked ? { force: 5.0, cooldown: 2.0 } : null)}
            />
            <span className="toggle-track" />
          </label>
        </Field>
        {hasKicker && (
          <>
            <Field label={t('f.force')}>
              <Slider value={k.force} min={1} max={15} step={0.5} unit=" N"
                onChange={v => set(['kicker', 'force'], v)} />
            </Field>
            <Field label={t('f.cooldown')}>
              <Slider value={k.cooldown} min={0.5} max={10} step={0.5} unit=" s"
                onChange={v => set(['kicker', 'cooldown'], v)} />
            </Field>
            <Field label={t('f.aimrange')} hint={t('f.aimrange.hint')}>
              <Slider value={k.aim_range ?? 0} min={0} max={360} step={10} unit="°"
                onChange={v => set(['kicker', 'aim_range'], v)} />
            </Field>
          </>
        )}
      </Section>
    )
  }

  function DribblerSection() {
    const d = r.dribbler
    return (
      <Section title={t('sec.dribbler')} defaultOpen={false}>
        <Field label={t('f.enable')}>
          <label className="toggle">
            <input type="checkbox" checked={!!d}
              onChange={e => set(['dribbler'], e.target.checked
                ? { position: 'front', strength: 1.0, capture_radius: 0.05 }
                : null)}
            />
            <span className="toggle-track" />
          </label>
        </Field>
        {d && (
          <>
            <Field label={t('f.position')}>
              <div className="tag-group">
                <Tag active={d.position === 'front'}
                  onClick={() => set(['dribbler', 'position'], 'front')}>{t('f.front')}</Tag>
                <Tag active={d.position === 'back'}
                  onClick={() => set(['dribbler', 'position'], 'back')}>{t('f.back')}</Tag>
              </div>
            </Field>
            <Field label={t('f.strength')}>
              <Slider value={d.strength ?? 1.0} min={0.2} max={3.0} step={0.1}
                onChange={v => set(['dribbler', 'strength'], v)} />
            </Field>
            <Field label={t('f.capradius')}>
              <Slider value={d.capture_radius ?? 0.05} min={0.02} max={0.08}
                step={0.005} unit=" m"
                onChange={v => set(['dribbler', 'capture_radius'], v)} />
            </Field>
          </>
        )}
      </Section>
    )
  }

  function VisualSection() {
    const v = r.visual
    return (
      <Section title={t('sec.visual')} defaultOpen={false}>
        <Field label={t('f.mesh')} hint={t('f.mesh.hint')}>
          <select className="text-input" value={v?.mesh ?? ''}
            onChange={e => set(['visual'], e.target.value
              ? { mesh: e.target.value, scale: v?.scale ?? 1.0,
                  offset: v?.offset ?? [0, 0, 0],
                  rotation: v?.rotation ?? [0, 0, 0] }
              : null)}>
            <option value="">{t('f.mesh.none')}</option>
            {meshList.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </Field>
        {v && (
          <>
            <Field label={t('f.scale')}>
              <NumInput value={v.scale ?? 1.0} min={0.0001} max={1000} step={0.1}
                onChange={val => set(['visual', 'scale'], val || 1.0)} />
            </Field>
            <Field label={t('f.offsety')}>
              <NumInput value={v.offset?.[1] ?? 0} min={-0.5} max={0.5} step={0.01}
                onChange={val => set(['visual', 'offset'],
                  [v.offset?.[0] ?? 0, val, v.offset?.[2] ?? 0])} />
            </Field>
            <Field label={t('f.roty')}>
              <NumInput value={v.rotation?.[1] ?? 0} min={-180} max={180} step={5}
                onChange={val => set(['visual', 'rotation'],
                  [v.rotation?.[0] ?? 0, val, v.rotation?.[2] ?? 0])} />
            </Field>
          </>
        )}
      </Section>
    )
  }

  // ── Robot info summary for preview panel ──────────────────────────────────

  function InfoRow({ label, value }) {
    return (
      <div className="info-row">
        <span className="info-label">{label}</span>
        <span className="info-value">{value}</span>
      </div>
    )
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-brand">
          <span className="brand-icon">⚽</span>
          <span className="brand-name">RCJ Soccer Simulator</span>
        </div>
        <div className="header-tabs">
          <button className={`hdr-tab ${tab === 'builder' ? 'active' : ''}`}
            onClick={() => setTab('builder')}>{t('tab.builder')}</button>
          <button className={`hdr-tab ${tab === 'viewer' ? 'active' : ''}`}
            onClick={() => setTab('viewer')}>{t('tab.viewer')}</button>
        </div>
        <div className="header-actions">
          {status && (
            <span className={`status-msg ${status.type}`}>{status.msg}</span>
          )}
          <input ref={fileRef} type="file" accept=".yaml,.yml"
            style={{ display: 'none' }} onChange={importYaml} />
          <button className="btn btn-ghost" onClick={() => fileRef.current?.click()}>
            {t('btn.import')}
          </button>
          <button className="btn btn-ghost" onClick={downloadYaml}>
            {t('btn.export')}
          </button>
          <button className="btn btn-primary" onClick={saveRobot} disabled={loading}>
            {loading ? t('btn.saving') : t('btn.save')}
          </button>
          <button className={`btn btn-ghost btn-icon ${prefsOpen ? 'active' : ''}`}
            title={t('btn.prefs')} onClick={() => setPrefsOpen(o => !o)}>
            ⚙
          </button>
        </div>
      </header>

      {prefsOpen && <PrefsPanel onClose={() => setPrefsOpen(false)} />}

      {/* ── Simulation viewer ── */}
      {tab === 'viewer' && (
        <div style={{ gridColumn: '1 / -1', minHeight: 0 }}>
          <SimViewer />
        </div>
      )}

      {/* ── Builder (hidden when viewer active) ── */}
      {tab === 'builder' && <>

      {/* Sidebar — robot list */}
      <aside className="sidebar">
        <div className="sidebar-header">{t('sidebar.robots')}</div>
        <button className="sidebar-new" onClick={newRobot}>{t('sidebar.new')}</button>
        <div className="sidebar-list">
          {robotList.length === 0 && (
            <div className="sidebar-empty">{t('sidebar.empty')}</div>
          )}
          {robotList.map(name => (
            <button key={name} className="sidebar-item" onClick={() => loadRobot(name)}>
              <span className="sidebar-dot" />
              {name}
            </button>
          ))}
        </div>
      </aside>

      {/* Builder form */}
      <main className="builder">
        <div className="builder-inner">
          <BasicSection />
          <BodySection />
          <WheelsSection />
          <SensorsSection />
          <KickerSection />
          <DribblerSection />
          <VisualSection />
        </div>
      </main>

      {/* Preview panel */}
      <aside className="preview-panel">
        <div className="preview-title">{t('pv.title')}</div>
        <div className="preview-svg">
          <RobotPreview robot={r} />
        </div>
        <div className="preview-info">
          <InfoRow label={t('pv.name')}   value={r.name || '—'} />
          <InfoRow label={t('pv.shape')}  value={r.body?.shape ?? '—'} />
          <InfoRow label={t('pv.radius')} value={`${r.body?.radius ?? '—'} m`} />
          <InfoRow label={t('pv.mass')}   value={`${r.body?.mass ?? '—'} kg`} />
          <InfoRow label={t('pv.drive')}  value={r.wheels?.type ?? '—'} />
          <InfoRow label={t('pv.ir')}     value={`${r.sensors?.ir_ring?.count ?? 0} ${t('pv.sectors')}`} />
          <InfoRow label={t('pv.us')}     value={`${(r.sensors?.ultrasound?.directions ?? []).length} ${t('pv.beams')}`} />
          <InfoRow label={t('pv.lines')}  value={`${(r.sensors?.line_sensors?.positions ?? []).length} ${t('pv.sensors')}`} />
          <InfoRow label={t('pv.kicker')} value={r.kicker ? `${r.kicker.force} N` : t('pv.none')} />
        </div>
      </aside>

      </>}
    </div>
  )
}
