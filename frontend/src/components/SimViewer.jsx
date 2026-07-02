import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { API_BASE, WS_URL } from '../config'
import './SimViewer.css'

// Field constants (meters) — must match field.py
const HL  = 1.095, HW  = 0.790
const HTL = 1.215, HTW = 0.910
const HG  = 0.300, GD  = 0.074
const PD  = 0.25,  PHY = 0.40

export default function SimViewer() {
  const mountRef = useRef(null)
  const objRef   = useRef({})   // { ballMesh, shadowMesh, robotMeshes, makeRobot }
  const wsRef    = useRef(null)
  const [hud,   setHud]   = useState({ score: { blue: 0, yellow: 0 }, state: 'playing', time: 0 })
  const [wsOk,  setWsOk]  = useState(false)
  const [speed, setSpeed] = useState(1.0)

  // ── Match setup state ─────────────────────────────────────────────
  const [setupOpen,  setSetupOpen]  = useState(false)
  const [robots,     setRobots]     = useState([])
  const [strategies, setStrategies] = useState([])
  const [match, setMatch] = useState({
    blue: ['striker_v3', ''], yellow: ['goalkeeper_v2', ''],
    blue_strategy: 'examples.attacker_strategy',
    yellow_strategy: 'examples.defender_strategy',
  })
  const [setupMsg, setSetupMsg] = useState(null)

  // ── Recording / replay state ──────────────────────────────────────
  const [recording,  setRecording]  = useState(null)   // nome da gravação ativa
  const [recList,    setRecList]    = useState(null)   // null = painel fechado
  const [replay,     setReplay]     = useState(null)   // { name, frames }
  const [rIdx,       setRIdx]       = useState(0)
  const [rPlaying,   setRPlaying]   = useState(false)
  const [rSpeed,     setRSpeed]     = useState(1)
  const replayRef = useRef(false)                       // gate p/ frames ao vivo
  replayRef.current = !!replay

  // ── Scenario editor state ─────────────────────────────────────────
  const [editMode,  setEditMode]  = useState(false)
  const [scenarios, setScenarios] = useState([])
  const [scnName,   setScnName]   = useState('')
  const editRef = useRef(false)                         // lido pelos handlers 3D

  function refreshScenarios() {
    fetch(`${API_BASE}/api/scenarios`).then(r => r.json()).then(setScenarios).catch(() => {})
  }

  function toggleEdit() {
    const next = !editMode
    if (next && replay) exitReplay()
    setEditMode(next)
    editRef.current = next
    sendCmd(next ? 'pause' : 'resume')
    if (next) refreshScenarios()
  }

  async function deleteScenario(name) {
    try {
      await fetch(`${API_BASE}/api/scenarios/${name}`, { method: 'DELETE' })
      refreshScenarios()
    } catch { /* server offline */ }
  }

  // Aplica o frame corrente do replay na cena
  useEffect(() => {
    if (!replay) return
    const f = replay.frames[Math.min(rIdx, replay.frames.length - 1)]
    if (f && objRef.current.applyFrame) {
      setHud({ score: f.score, state: f.state, time: f.timestamp })
      objRef.current.applyFrame(f)
    }
  }, [replay, rIdx])

  // Playback: avança rIdx a 60 fps × velocidade
  useEffect(() => {
    if (!replay || !rPlaying) return
    let acc = 0
    const id = setInterval(() => {
      acc += rSpeed
      const step = Math.floor(acc)
      if (step > 0) {
        acc -= step
        setRIdx(i => {
          const next = i + step
          if (next >= replay.frames.length - 1) {
            setRPlaying(false)
            return replay.frames.length - 1
          }
          return next
        })
      }
    }, 1000 / 60)
    return () => clearInterval(id)
  }, [replay, rPlaying, rSpeed])

  async function openReplayPanel() {
    if (recList !== null) { setRecList(null); return }
    try {
      const list = await fetch(`${API_BASE}/api/recordings`).then(r => r.json())
      setRecList(list)
    } catch { setRecList([]) }
  }

  async function loadReplay(name) {
    try {
      const data = await fetch(`${API_BASE}/api/recordings/${name}`).then(r => r.json())
      objRef.current.clearRobots?.()
      setEditMode(false)
      editRef.current = false
      setReplay({ name, frames: data.frames })
      setRIdx(0)
      setRPlaying(true)
      setRecList(null)
    } catch {
      setSetupMsg({ type: 'err', msg: `Failed to load ${name}` })
      setTimeout(() => setSetupMsg(null), 4000)
    }
  }

  function exitReplay() {
    setReplay(null)
    setRPlaying(false)
    objRef.current.clearRobots?.()   // volta a receber frames ao vivo
  }

  useEffect(() => {
    fetch(`${API_BASE}/api/robots`).then(r => r.json()).then(setRobots).catch(() => {})
    fetch(`${API_BASE}/api/strategies`).then(r => r.json()).then(setStrategies).catch(() => {})
    fetch(`${API_BASE}/api/match`).then(r => r.json()).then(m => setMatch({
      blue:   [m.blue?.[0] ?? '',   m.blue?.[1] ?? ''],
      yellow: [m.yellow?.[0] ?? '', m.yellow?.[1] ?? ''],
      blue_strategy:   m.blue_strategy,
      yellow_strategy: m.yellow_strategy,
    })).catch(() => {})
  }, [])

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    // ── Renderer ──────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type    = THREE.PCFSoftShadowMap
    mount.appendChild(renderer.domElement)

    // ── Scene ─────────────────────────────────────────────────────────
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0d1117)
    scene.fog = new THREE.FogExp2(0x0d1117, 0.10)

    // ── Camera ────────────────────────────────────────────────────────
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 30)
    camera.position.set(0, 3.8, 2.5)
    camera.lookAt(0, 0, 0)

    // ── Orbit controls ────────────────────────────────────────────────
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.07
    controls.minDistance   = 1.5
    controls.maxDistance   = 9
    controls.maxPolarAngle = Math.PI / 2.05

    // ── Lights ────────────────────────────────────────────────────────
    scene.add(new THREE.AmbientLight(0xffffff, 0.55))
    const sun = new THREE.DirectionalLight(0xfffcf0, 0.9)
    sun.position.set(3, 7, 4)
    sun.castShadow = true
    sun.shadow.mapSize.set(2048, 2048)
    sun.shadow.camera.left = -3; sun.shadow.camera.right  =  3
    sun.shadow.camera.top  =  2; sun.shadow.camera.bottom = -2
    scene.add(sun)
    const fill = new THREE.DirectionalLight(0xc0d8ff, 0.3)
    fill.position.set(-2, 4, -3)
    scene.add(fill)

    // ── Field (zebra stripes) ──────────────────────────────────────────
    const outArea = new THREE.Mesh(
      new THREE.PlaneGeometry(HTL * 2, HTW * 2),
      new THREE.MeshLambertMaterial({ color: 0x1a4e1a })
    )
    outArea.rotation.x = -Math.PI / 2
    outArea.receiveShadow = true
    scene.add(outArea)

    const N_STRIPES = 7, stripeW = (HL * 2) / N_STRIPES
    for (let i = 0; i < N_STRIPES; i++) {
      const stripe = new THREE.Mesh(
        new THREE.PlaneGeometry(stripeW - 0.001, HW * 2),
        new THREE.MeshLambertMaterial({ color: i % 2 === 0 ? 0x236b23 : 0x1f5f1f })
      )
      stripe.rotation.x = -Math.PI / 2
      stripe.position.set(-HL + stripeW * (i + 0.5), 0.001, 0)
      stripe.receiveShadow = true
      scene.add(stripe)
    }

    // ── Field lines ───────────────────────────────────────────────────
    const lineMat = new THREE.LineBasicMaterial({ color: 0xffffff })
    const LH = 0.003   // line height above field

    function addLines(pts) {
      const geo = new THREE.BufferGeometry()
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pts), 3))
      scene.add(new THREE.LineSegments(geo, lineMat))
    }

    const PFX = HL - PD   // penalty area front line x (0.845)

    addLines([
      // Playing-area boundary
      -HL, LH,  HW,   HL, LH,  HW,
       HL, LH,  HW,   HL, LH, -HW,
       HL, LH, -HW,  -HL, LH, -HW,
      -HL, LH, -HW,  -HL, LH,  HW,
      // Center line
       0, LH,  HW,    0, LH, -HW,
      // Right (yellow) penalty area
       HL, LH, -PHY,   PFX, LH, -PHY,
      PFX, LH, -PHY,  PFX, LH,  PHY,
      PFX, LH,  PHY,   HL, LH,  PHY,
      // Left (blue) penalty area
      -HL, LH, -PHY,  -PFX, LH, -PHY,
     -PFX, LH, -PHY, -PFX, LH,  PHY,
     -PFX, LH,  PHY,  -HL, LH,  PHY,
    ])

    // Center circle
    const circlePts = []
    for (let i = 0; i < 64; i++) {
      const a1 = (i / 64) * Math.PI * 2, a2 = ((i + 1) / 64) * Math.PI * 2
      circlePts.push(
        Math.cos(a1) * 0.30, LH, Math.sin(a1) * 0.30,
        Math.cos(a2) * 0.30, LH, Math.sin(a2) * 0.30
      )
    }
    addLines(circlePts)

    // ── Goals ─────────────────────────────────────────────────────────
    function buildGoal(sign, color) {
      const mat = new THREE.MeshLambertMaterial({
        color, transparent: true, opacity: 0.40, side: THREE.DoubleSide,
      })
      const GH = 0.15
      // Back wall
      const back = new THREE.Mesh(new THREE.BoxGeometry(0.012, GH, HG * 2), mat)
      back.position.set(sign * (HL + GD), GH / 2, 0)
      scene.add(back)
      // Side walls
      for (const zs of [-1, 1]) {
        const wall = new THREE.Mesh(new THREE.BoxGeometry(GD, GH, 0.012), mat)
        wall.position.set(sign * (HL + GD / 2), GH / 2, zs * HG)
        scene.add(wall)
      }
      // Top frame lines
      const gx = sign * HL, bx = sign * (HL + GD)
      addLines([
        gx, GH, -HG,  bx, GH, -HG,
        bx, GH, -HG,  bx, GH,  HG,
        bx, GH,  HG,  gx, GH,  HG,
        gx, GH, -HG,  gx, GH,  HG,
        // Vertical corner posts
        gx,  0, -HG,  gx, GH, -HG,
        gx,  0,  HG,  gx, GH,  HG,
      ])
    }
    buildGoal(-1, 0x3b82f6)
    buildGoal( 1, 0xeab308)

    // ── Ball ──────────────────────────────────────────────────────────
    const BALL_R = 0.043
    const ballMesh = new THREE.Mesh(
      new THREE.SphereGeometry(BALL_R, 20, 16),
      new THREE.MeshLambertMaterial({ color: 0xff5500 })
    )
    ballMesh.castShadow = true
    ballMesh.position.set(0, BALL_R, 0)
    scene.add(ballMesh)

    const shadowMesh = new THREE.Mesh(
      new THREE.CircleGeometry(BALL_R * 0.85, 20),
      new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.28 })
    )
    shadowMesh.rotation.x = -Math.PI / 2
    shadowMesh.position.y = 0.002
    scene.add(shadowMesh)

    // ── Robot factory ──────────────────────────────────────────────────
    const robotMeshes = {}

    function makeRobot(id, team, radius = 0.11) {
      const isBlue   = team === 'blue'
      const teamClr  = isBlue ? 0x3b82f6 : 0xeab308
      const group    = new THREE.Group()

      // Cylinder body
      const body = new THREE.Mesh(
        new THREE.CylinderGeometry(radius, radius, 0.08, 32),
        new THREE.MeshLambertMaterial({ color: teamClr })
      )
      body.position.y = 0.04
      body.castShadow = true
      group.add(body)

      // White ring on top
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(radius * 0.89, 0.007, 8, 32),
        new THREE.MeshLambertMaterial({ color: 0xffffff, transparent: true, opacity: 0.75 })
      )
      ring.rotation.x = Math.PI / 2
      ring.position.y = 0.083
      group.add(ring)

      // Heading cone (points along local +X)
      const arrow = new THREE.Mesh(
        new THREE.ConeGeometry(0.022, 0.055, 8),
        new THREE.MeshLambertMaterial({ color: 0xffffff })
      )
      arrow.rotation.z = -Math.PI / 2
      arrow.position.set(radius + 0.025, 0.04, 0)
      group.add(arrow)

      // Team dot
      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(0.022, 10, 10),
        new THREE.MeshLambertMaterial({ color: isBlue ? 0xbfdbfe : 0xfef9c3 })
      )
      dot.position.y = 0.092
      group.add(dot)

      scene.add(group)
      robotMeshes[id] = group
      return group
    }

    function clearRobots() {
      for (const id of Object.keys(robotMeshes)) {
        scene.remove(robotMeshes[id])
        delete robotMeshes[id]
      }
    }

    function applyFrame(state) {
      // Ball (sim Y → Three.js -Z)
      const { x, y } = state.ball
      ballMesh.position.set(x, BALL_R, -y)
      shadowMesh.position.set(x, 0.002, -y)
      // Robots
      for (const r of state.robots) {
        const mesh = robotMeshes[r.id] ?? makeRobot(r.id, r.team, r.radius)
        mesh.visible = !r.penalized
        if (!r.penalized) {
          mesh.position.set(r.x, 0, -r.y)
          mesh.rotation.y = r.heading  // heading=0 → +X, π/2 → -Z (matches sim Y→-Z)
        }
      }
    }

    objRef.current = { ballMesh, shadowMesh, robotMeshes, makeRobot, clearRobots, applyFrame }

    // ── Scenario editor: drag ball/robots (ativo só em edit mode) ─────
    const raycaster   = new THREE.Raycaster()
    const pointerNdc  = new THREE.Vector2()
    const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
    const hitPoint    = new THREE.Vector3()
    let dragTarget = null   // { kind: 'ball' | 'robot', id?, obj }

    function setPointer(ev) {
      const rect = renderer.domElement.getBoundingClientRect()
      pointerNdc.x =  ((ev.clientX - rect.left) / rect.width)  * 2 - 1
      pointerNdc.y = -((ev.clientY - rect.top)  / rect.height) * 2 + 1
      raycaster.setFromCamera(pointerNdc, camera)
    }

    function pickObject(ev) {
      setPointer(ev)
      const groups = Object.values(robotMeshes)
      const hits = raycaster.intersectObjects([ballMesh, ...groups], true)
      if (!hits.length) return null
      let obj = hits[0].object
      if (obj === ballMesh) return { kind: 'ball', obj: ballMesh }
      while (obj.parent && !groups.includes(obj)) obj = obj.parent
      const id = Object.keys(robotMeshes).find(k => robotMeshes[k] === obj)
      return id ? { kind: 'robot', id, obj } : null
    }

    function onPointerDown(ev) {
      if (!editRef.current || ev.button !== 0) return
      const t = pickObject(ev)
      if (t) {
        dragTarget = t
        controls.enabled = false
      }
    }

    function onPointerMove(ev) {
      if (!dragTarget) return
      setPointer(ev)
      if (raycaster.ray.intersectPlane(groundPlane, hitPoint)) {
        dragTarget.obj.position.x = Math.max(-HTL + 0.06, Math.min(HTL - 0.06, hitPoint.x))
        dragTarget.obj.position.z = Math.max(-HTW + 0.06, Math.min(HTW - 0.06, hitPoint.z))
        if (dragTarget.kind === 'ball')
          shadowMesh.position.set(dragTarget.obj.position.x, 0.002, dragTarget.obj.position.z)
      }
    }

    function onPointerUp() {
      if (!dragTarget) return
      const { x, z } = dragTarget.obj.position
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          cmd: 'place',
          object: dragTarget.kind === 'ball' ? 'ball' : dragTarget.id,
          x, y: -z,   // Three.js -Z → sim Y
        }))
      }
      dragTarget = null
      controls.enabled = true
    }

    renderer.domElement.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup',   onPointerUp)

    // ── Resize ────────────────────────────────────────────────────────
    function resize() {
      const w = mount.clientWidth, h = mount.clientHeight
      renderer.setSize(w, h)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    const ro = new ResizeObserver(resize)
    ro.observe(mount)
    resize()

    // ── Animation loop ────────────────────────────────────────────────
    let animId
    function animate() {
      animId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // ── WebSocket ─────────────────────────────────────────────────────
    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onopen  = () => setWsOk(true)
      ws.onclose = () => { setWsOk(false); setTimeout(connect, 2000) }
      ws.onerror = () => setWsOk(false)

      ws.onmessage = ({ data }) => {
        const state = JSON.parse(data)

        // Server events (restart ack / error) — not sim frames
        if (state.event) {
          if (state.event === 'restarted') {
            objRef.current.clearRobots()
            setRecording(null)
            setSetupMsg({ type: 'ok', msg: 'Match restarted' })
            setTimeout(() => setSetupMsg(null), 4000)
          } else if (state.event === 'error') {
            setSetupMsg({ type: 'err', msg: state.detail })
            setTimeout(() => setSetupMsg(null), 4000)
          } else if (state.event === 'recording_started') {
            setRecording(state.name)
          } else if (state.event === 'recording_stopped') {
            setRecording(null)
          } else if (state.event === 'scenario_saved') {
            refreshScenarios()
            setSetupMsg({ type: 'ok', msg: `Scenario "${state.name}" saved` })
            setTimeout(() => setSetupMsg(null), 4000)
          } else if (state.event === 'scenario_loaded') {
            setSetupMsg({ type: 'ok', msg: `Scenario "${state.name}" loaded` })
            setTimeout(() => setSetupMsg(null), 4000)
          }
          return
        }

        if (editRef.current && !dragTarget) {
          // Em edit mode o sim está pausado; broadcasts pós-place sincronizam
          objRef.current.applyFrame(state)
          return
        }

        if (replayRef.current) return   // replay mode: ignore live frames

        setHud({ score: state.score, state: state.state, time: state.timestamp })
        objRef.current.applyFrame(state)
      }
    }
    connect()

    // ── Cleanup ───────────────────────────────────────────────────────
    return () => {
      cancelAnimationFrame(animId)
      ro.disconnect()
      renderer.domElement.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerup',   onPointerUp)
      if (wsRef.current) wsRef.current.onclose = null
      wsRef.current?.close()
      renderer.dispose()
      if (renderer.domElement.parentNode === mount)
        mount.removeChild(renderer.domElement)
    }
  }, [])

  function sendCmd(cmd, extra = {}) {
    if (wsRef.current?.readyState === WebSocket.OPEN)
      wsRef.current.send(JSON.stringify({ cmd, ...extra }))
  }

  function changeSpeed(v) {
    setSpeed(v)
    sendCmd('speed', { value: v })
  }

  function restartMatch() {
    sendCmd('restart', {
      blue:   match.blue.filter(Boolean),
      yellow: match.yellow.filter(Boolean),
      blue_strategy:   match.blue_strategy,
      yellow_strategy: match.yellow_strategy,
    })
  }

  function setSlot(team, i, value) {
    setMatch(m => {
      const slots = [...m[team]]
      slots[i] = value
      return { ...m, [team]: slots }
    })
  }

  function TeamSetup({ team, label }) {
    return (
      <div className={`sv-setup-team ${team}`}>
        <div className="sv-setup-team-name">{label}</div>
        {[0, 1].map(i => (
          <select key={i} className="sv-select" value={match[team][i]}
            onChange={e => setSlot(team, i, e.target.value)}>
            {i === 1 && <option value="">— (no 2nd robot)</option>}
            {i === 0 && !match[team][0] && <option value="">select robot…</option>}
            {robots.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        ))}
        <select className="sv-select" value={match[`${team}_strategy`] ?? ''}
          onChange={e => setMatch(m => ({ ...m, [`${team}_strategy`]: e.target.value }))}>
          {strategies.map(s => (
            <option key={s} value={s}>{s.replace(/^(examples|bridge)\./, '$1: ')}</option>
          ))}
        </select>
      </div>
    )
  }

  const fmtTime = t => {
    const m = Math.floor(t / 60)
    const s = Math.floor(t % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  return (
    <div className="sv">
      {/* Three.js canvas */}
      <div ref={mountRef} className={`sv-canvas ${editMode ? 'edit' : ''}`} />

      {/* Score HUD */}
      <div className="sv-hud">
        <div className={`sv-team blue ${hud.state === 'goal_blue' ? 'flash' : ''}`}>
          <span className="sv-name">BLUE</span>
          <span className="sv-pts">{hud.score?.blue ?? 0}</span>
        </div>
        <div className="sv-mid">
          <div className="sv-time">{fmtTime(hud.time)}</div>
          {hud.state !== 'playing' && (
            <div className="sv-event">{hud.state.replace(/_/g, ' ').toUpperCase()}</div>
          )}
        </div>
        <div className={`sv-team yellow ${hud.state === 'goal_yellow' ? 'flash' : ''}`}>
          <span className="sv-pts">{hud.score?.yellow ?? 0}</span>
          <span className="sv-name">YELLOW</span>
        </div>
      </div>

      {/* Controls bar */}
      <div className="sv-bar">
        <span className={`sv-led ${wsOk ? 'ok' : 'off'}`} title={wsOk ? 'Connected' : 'Disconnected'} />
        <button className="sv-btn" onClick={() => sendCmd('pause')}>⏸</button>
        <button className="sv-btn" onClick={() => sendCmd('resume')}>▶</button>
        <button className="sv-btn" onClick={() => sendCmd('reset')} title="Reset match">↺</button>
        <button className={`sv-btn ${setupOpen ? 'active' : ''}`}
          onClick={() => setSetupOpen(o => !o)} title="Match setup">⚙</button>
        <button className={`sv-btn ${recording ? 'rec' : ''}`}
          onClick={() => sendCmd(recording ? 'record_stop' : 'record_start')}
          title={recording ? `Recording ${recording}…` : 'Record match'}>⏺</button>
        <button className={`sv-btn ${recList !== null || replay ? 'active' : ''}`}
          onClick={openReplayPanel} title="Replays">🎞</button>
        <button className={`sv-btn ${editMode ? 'active' : ''}`}
          onClick={toggleEdit} title="Scenario editor (drag ball/robots)">✋</button>
        <div className="sv-speed-group">
          <span>Speed</span>
          {[0.5, 1, 2, 4].map(s => (
            <button key={s}
              className={`sv-spd ${speed === s ? 'active' : ''}`}
              onClick={() => changeSpeed(s)}>
              {s}×
            </button>
          ))}
        </div>
        <span className="sv-tip">Drag to orbit · Scroll to zoom</span>
      </div>

      {/* Match setup panel */}
      {setupOpen && (
        <div className="sv-setup">
          <div className="sv-setup-title">Match Setup</div>
          <div className="sv-setup-teams">
            <TeamSetup team="blue"   label="BLUE" />
            <TeamSetup team="yellow" label="YELLOW" />
          </div>
          <div className="sv-setup-actions">
            {setupMsg && (
              <span className={`sv-setup-msg ${setupMsg.type}`}>{setupMsg.msg}</span>
            )}
            <button className="sv-setup-restart" onClick={restartMatch}
              disabled={!wsOk || !match.blue[0] || !match.yellow[0]}>
              ⟳ Restart match
            </button>
          </div>
        </div>
      )}

      {/* Scenario editor panel */}
      {editMode && (
        <div className="sv-setup sv-editor">
          <div className="sv-setup-title">Scenario Editor</div>
          <div className="sv-editor-hint">
            Sim paused — drag the ball or any robot to reposition it.
          </div>
          <div className="sv-editor-save">
            <input className="sv-text" placeholder="scenario name"
              value={scnName} onChange={e => setScnName(e.target.value)} />
            <button className="sv-setup-restart" disabled={!scnName.trim() || !wsOk}
              onClick={() => sendCmd('scenario_save',
                { name: scnName.trim().toLowerCase().replace(/\s+/g, '_') })}>
              Save
            </button>
          </div>
          {scenarios.length > 0 && (
            <div className="sv-replays-list">
              {scenarios.map(s => (
                <div key={s} className="sv-replays-item">
                  <span className="sv-replays-name">{s}</span>
                  <button className="sv-btn" title="Load"
                    onClick={() => sendCmd('scenario_load', { name: s })}>⤓</button>
                  <button className="sv-btn" title="Delete"
                    onClick={() => deleteScenario(s)}>🗑</button>
                </div>
              ))}
            </div>
          )}
          {setupMsg && (
            <div className={`sv-setup-msg ${setupMsg.type}`}>{setupMsg.msg}</div>
          )}
        </div>
      )}

      {/* Replay list panel */}
      {recList !== null && (
        <div className="sv-setup sv-replays">
          <div className="sv-setup-title">Replays</div>
          {recList.length === 0 && (
            <div className="sv-replays-empty">
              No recordings yet — press ⏺ to record a match.
            </div>
          )}
          <div className="sv-replays-list">
            {recList.map(rec => (
              <div key={rec.name} className="sv-replays-item">
                <span className="sv-replays-name">{rec.name}</span>
                <span className="sv-replays-size">{rec.size_kb} kB</span>
                <button className="sv-btn" onClick={() => loadReplay(rec.name)}>▶</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Replay timeline */}
      {replay && (
        <div className="sv-timeline">
          <div className="sv-timeline-head">
            <span className="sv-timeline-badge">REPLAY</span>
            <span className="sv-timeline-name">{replay.name}</span>
            <span className="sv-timeline-time">
              {fmtTime((replay.frames[rIdx]?.timestamp) ?? 0)} / {fmtTime(replay.frames.at(-1)?.timestamp ?? 0)}
            </span>
            <button className="sv-btn" onClick={exitReplay} title="Exit replay">✕</button>
          </div>
          <div className="sv-timeline-row">
            <button className="sv-btn" onClick={() => setRPlaying(p => !p)}>
              {rPlaying ? '⏸' : '▶'}
            </button>
            <input type="range" className="sv-timeline-slider"
              min={0} max={replay.frames.length - 1} value={rIdx}
              onChange={e => { setRPlaying(false); setRIdx(+e.target.value) }}
            />
            {[0.5, 1, 2, 4].map(s => (
              <button key={s}
                className={`sv-spd ${rSpeed === s ? 'active' : ''}`}
                onClick={() => setRSpeed(s)}>
                {s}×
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Offline banner */}
      {!wsOk && (
        <div className="sv-offline">
          <div className="sv-offline-box">
            <div className="sv-offline-title">Server offline</div>
            <code className="sv-offline-cmd">uvicorn server.main:app --reload</code>
            <div className="sv-offline-sub">Reconnecting automatically…</div>
          </div>
        </div>
      )}
    </div>
  )
}
