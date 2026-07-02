import { useState, useEffect, useCallback } from 'react'
import yaml from 'js-yaml'
import RobotPreview from './components/RobotPreview'
import SimViewer   from './components/SimViewer'
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
  const [tab, setTab]             = useState('builder')  // 'builder' | 'viewer'
  const [config, setConfig]       = useState(DEFAULT_ROBOT)
  const [robotList, setRobotList] = useState([])
  const [status, setStatus]       = useState(null)   // { type: 'ok'|'err', msg }
  const [loading, setLoading]     = useState(false)

  const r = config.robot

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

  // Fetch robot list from server
  useEffect(() => {
    fetch('/api/robots')
      .then(r => r.json())
      .then(setRobotList)
      .catch(() => {})
  }, [])

  function notify(type, msg) {
    setStatus({ type, msg })
    setTimeout(() => setStatus(null), 3000)
  }

  async function loadRobot(name) {
    try {
      const res  = await fetch(`/api/robots/${name}`)
      const data = await res.json()
      setConfig(data)
      notify('ok', `Loaded "${name}"`)
    } catch {
      notify('err', 'Failed to load robot')
    }
  }

  async function saveRobot() {
    const name = r.name.trim().toLowerCase().replace(/\s+/g, '_')
    if (!name) return notify('err', 'Robot name is empty')
    setLoading(true)
    try {
      const res = await fetch(`/api/robots/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (!res.ok) throw new Error()
      notify('ok', `Saved as robots/${name}.yaml`)
      const list = await fetch('/api/robots').then(r => r.json())
      setRobotList(list)
    } catch {
      notify('err', 'Server unavailable — use Download instead')
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
      <Section title="Identity">
        <Field label="Name">
          <input className="text-input" value={r.name}
            onChange={e => set(['name'], e.target.value)}
            placeholder="My Robot"
          />
        </Field>
      </Section>
    )
  }

  function BodySection() {
    const b = r.body
    return (
      <Section title="Body">
        <Field label="Shape">
          <div className="tag-group">
            <Tag active={b.shape === 'circle'}  onClick={() => set(['body', 'shape'], 'circle')}>Circle</Tag>
            <Tag active={b.shape === 'rectangle'} onClick={() => set(['body', 'shape'], 'rectangle')}>Rectangle</Tag>
          </div>
        </Field>

        {b.shape === 'circle' ? (
          <Field label="Radius" hint="max 0.11 m">
            <Slider value={b.radius} min={0.05} max={0.11} step={0.005} unit=" m"
              onChange={v => set(['body', 'radius'], v)} />
          </Field>
        ) : (
          <>
            <Field label="Width">
              <Slider value={b.width ?? 0.20} min={0.10} max={0.22} step={0.01} unit=" m"
                onChange={v => set(['body', 'width'], v)} />
            </Field>
            <Field label="Height">
              <Slider value={b.height ?? 0.18} min={0.10} max={0.22} step={0.01} unit=" m"
                onChange={v => set(['body', 'height'], v)} />
            </Field>
          </>
        )}

        <Field label="Mass">
          <Slider value={b.mass} min={0.5} max={3.0} step={0.05} unit=" kg"
            onChange={v => set(['body', 'mass'], v)} />
        </Field>
        <Field label="Max speed">
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
      <Section title="Drive System">
        <Field label="Type">
          <div className="tag-group">
            <Tag active={isOmni} onClick={() => set(['wheels', 'type'], 'omnidirectional')}>Omnidirectional</Tag>
            <Tag active={!isOmni} onClick={() => set(['wheels', 'type'], 'differential')}>Differential</Tag>
          </div>
        </Field>

        {isOmni && (
          <Field label="Wheels">
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
              <button className="add-btn" onClick={addWheel}>+ Add wheel</button>
            </div>
          </Field>
        )}

        {!isOmni && (
          <Field label="Wheel base" hint="distance between wheels">
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
      <Section title="Sensors">
        {/* IR Ring */}
        <div className="subsection">
          <div className="subsection-title">IR Ring</div>
          <Field label="Sectors">
            <div className="tag-group">
              {[8, 12, 16, 24].map(n => (
                <Tag key={n} active={s.ir_ring?.count === n}
                  onClick={() => set(['sensors', 'ir_ring', 'count'], n)}>
                  {n}
                </Tag>
              ))}
            </div>
          </Field>
          <Field label="Range">
            <Slider value={s.ir_ring?.range ?? 1.5} min={0.5} max={3.0} step={0.1} unit=" m"
              onChange={v => set(['sensors', 'ir_ring', 'range'], v)} />
          </Field>
          <Field label="Noise σ">
            <Slider value={s.ir_ring?.noise_std ?? 0.05} min={0} max={0.3} step={0.01}
              onChange={v => set(['sensors', 'ir_ring', 'noise_std'], v)} />
          </Field>
        </div>

        {/* Compass */}
        <div className="subsection">
          <div className="subsection-title">Compass</div>
          <Field label="Noise σ" hint="degrees">
            <Slider value={s.compass?.noise_std ?? 2.0} min={0} max={15} step={0.5} unit="°"
              onChange={v => set(['sensors', 'compass', 'noise_std'], v)} />
          </Field>
        </div>

        {/* Ultrasound */}
        <div className="subsection">
          <div className="subsection-title">Ultrasound</div>
          <Field label="Range">
            <Slider value={s.ultrasound?.range ?? 2.0} min={0.5} max={4.0} step={0.1} unit=" m"
              onChange={v => set(['sensors', 'ultrasound', 'range'], v)} />
          </Field>
          <Field label="Noise σ">
            <Slider value={s.ultrasound?.noise_std ?? 0.03} min={0} max={0.2} step={0.01}
              onChange={v => set(['sensors', 'ultrasound', 'noise_std'], v)} />
          </Field>
          <Field label="Directions">
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
              <button className="add-btn" onClick={addUltrasound}>+ Add sensor</button>
            </div>
          </Field>
        </div>

        {/* Line sensors */}
        <div className="subsection">
          <div className="subsection-title">Line Sensors</div>
          <Field label="Positions" hint="relative to center (m)">
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
              <button className="add-btn" onClick={addLineSensor}>+ Add sensor</button>
            </div>
          </Field>
        </div>
      </Section>
    )
  }

  function KickerSection() {
    const k = r.kicker
    const hasKicker = !!k
    return (
      <Section title="Kicker" defaultOpen>
        <Field label="Enable">
          <label className="toggle">
            <input type="checkbox" checked={hasKicker}
              onChange={e => set(['kicker'], e.target.checked ? { force: 5.0, cooldown: 2.0 } : null)}
            />
            <span className="toggle-track" />
          </label>
        </Field>
        {hasKicker && (
          <>
            <Field label="Force">
              <Slider value={k.force} min={1} max={15} step={0.5} unit=" N"
                onChange={v => set(['kicker', 'force'], v)} />
            </Field>
            <Field label="Cooldown">
              <Slider value={k.cooldown} min={0.5} max={10} step={0.5} unit=" s"
                onChange={v => set(['kicker', 'cooldown'], v)} />
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
            onClick={() => setTab('builder')}>⚙ Builder</button>
          <button className={`hdr-tab ${tab === 'viewer' ? 'active' : ''}`}
            onClick={() => setTab('viewer')}>▶ Simulation</button>
        </div>
        <div className="header-actions">
          {status && (
            <span className={`status-msg ${status.type}`}>{status.msg}</span>
          )}
          <button className="btn btn-ghost" onClick={downloadYaml}>
            ↓ Download YAML
          </button>
          <button className="btn btn-primary" onClick={saveRobot} disabled={loading}>
            {loading ? 'Saving…' : '✓ Save'}
          </button>
        </div>
      </header>

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
        <div className="sidebar-header">Robots</div>
        <button className="sidebar-new" onClick={newRobot}>+ New robot</button>
        <div className="sidebar-list">
          {robotList.length === 0 && (
            <div className="sidebar-empty">No robots saved yet</div>
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
        </div>
      </main>

      {/* Preview panel */}
      <aside className="preview-panel">
        <div className="preview-title">Live Preview</div>
        <div className="preview-svg">
          <RobotPreview robot={r} />
        </div>
        <div className="preview-info">
          <InfoRow label="Name"    value={r.name || '—'} />
          <InfoRow label="Shape"   value={r.body?.shape ?? '—'} />
          <InfoRow label="Radius"  value={`${r.body?.radius ?? '—'} m`} />
          <InfoRow label="Mass"    value={`${r.body?.mass ?? '—'} kg`} />
          <InfoRow label="Drive"   value={r.wheels?.type ?? '—'} />
          <InfoRow label="IR"      value={`${r.sensors?.ir_ring?.count ?? 0} sectors`} />
          <InfoRow label="US"      value={`${(r.sensors?.ultrasound?.directions ?? []).length} beams`} />
          <InfoRow label="Lines"   value={`${(r.sensors?.line_sensors?.positions ?? []).length} sensors`} />
          <InfoRow label="Kicker"  value={r.kicker ? `${r.kicker.force} N` : 'none'} />
        </div>
      </aside>

      </>}
    </div>
  )
}
