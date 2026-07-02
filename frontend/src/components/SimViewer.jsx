import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
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

    function makeRobot(id, team) {
      const isBlue   = team === 'blue'
      const teamClr  = isBlue ? 0x3b82f6 : 0xeab308
      const group    = new THREE.Group()

      // Cylinder body
      const body = new THREE.Mesh(
        new THREE.CylinderGeometry(0.11, 0.11, 0.08, 32),
        new THREE.MeshLambertMaterial({ color: teamClr })
      )
      body.position.y = 0.04
      body.castShadow = true
      group.add(body)

      // White ring on top
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.098, 0.007, 8, 32),
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
      arrow.position.set(0.135, 0.04, 0)
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

    objRef.current = { ballMesh, shadowMesh, robotMeshes, makeRobot }

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
      const ws = new WebSocket('ws://localhost:8000/ws/sim')
      wsRef.current = ws
      ws.onopen  = () => setWsOk(true)
      ws.onclose = () => { setWsOk(false); setTimeout(connect, 2000) }
      ws.onerror = () => setWsOk(false)

      ws.onmessage = ({ data }) => {
        const state = JSON.parse(data)
        setHud({ score: state.score, state: state.state, time: state.timestamp })

        // Ball (sim Y → Three.js -Z)
        const { x, y } = state.ball
        objRef.current.ballMesh.position.set(x, BALL_R, -y)
        objRef.current.shadowMesh.position.set(x, 0.002, -y)

        // Robots
        for (const r of state.robots) {
          const mesh = objRef.current.robotMeshes[r.id]
            ?? objRef.current.makeRobot(r.id, r.team)
          mesh.visible = !r.penalized
          if (!r.penalized) {
            mesh.position.set(r.x, 0, -r.y)
            mesh.rotation.y = r.heading  // heading=0 → +X, π/2 → -Z (matches sim Y→-Z)
          }
        }
      }
    }
    connect()

    // ── Cleanup ───────────────────────────────────────────────────────
    return () => {
      cancelAnimationFrame(animId)
      ro.disconnect()
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

  const fmtTime = t => {
    const m = Math.floor(t / 60)
    const s = Math.floor(t % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  return (
    <div className="sv">
      {/* Three.js canvas */}
      <div ref={mountRef} className="sv-canvas" />

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
