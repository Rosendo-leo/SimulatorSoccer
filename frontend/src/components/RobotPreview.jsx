const SCALE = 750   // SVG units per meter
const V     = 185   // half-side of viewBox (±185)
const MAX_US = 130  // max display length of ultrasound beam (SVG units)

function deg2rad(d) { return (d * Math.PI) / 180 }

function arcPath(cx, cy, r, startDeg, endDeg) {
  const s = deg2rad(startDeg)
  const e = deg2rad(endDeg)
  const x1 = cx + r * Math.cos(s)
  const y1 = cy + r * Math.sin(s)
  const x2 = cx + r * Math.cos(e)
  const y2 = cy + r * Math.sin(e)
  const large = endDeg - startDeg > 180 ? 1 : 0
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`
}

export default function RobotPreview({ robot }) {
  const body    = robot?.body    ?? {}
  const sensors = robot?.sensors ?? {}
  const kicker  = robot?.kicker  ?? null
  const wheels  = robot?.wheels  ?? {}

  const isCircle = (body.shape ?? 'circle') === 'circle'
  const radius   = (body.radius ?? 0.11) * SCALE
  const width    = (body.width  ?? 0.22) * SCALE
  const height   = (body.height ?? 0.22) * SCALE

  // IR ring
  const irCount    = sensors.ir_ring?.count ?? 16
  const sectorDeg  = 360 / irCount

  // Ultrasound
  const usDirs  = sensors.ultrasound?.directions ?? []

  // Line sensors
  const lineSensors = sensors.line_sensors?.positions ?? []

  // Wheel dots for differential
  const isDiff  = wheels.type === 'differential'
  const wheelR  = radius + 10
  const wDots   = isDiff
    ? [{ x: 0, y: -wheelR }, { x: 0, y: wheelR }]
    : (wheels.positions ?? []).map(a => ({
        x:  Math.cos(deg2rad(a)) * wheelR,
        y: -Math.sin(deg2rad(a)) * wheelR,
      }))

  return (
    <svg
      viewBox={`${-V} ${-V} ${V * 2} ${V * 2}`}
      width="100%"
      height="100%"
      style={{ display: 'block' }}
    >
      {/* Faint grid */}
      {[-120, -60, 0, 60, 120].map(v => (
        <g key={v}>
          <line x1={-V} y1={v} x2={V} y2={v} stroke="#2a2f45" strokeWidth={0.5} />
          <line x1={v} y1={-V} x2={v} y2={V} stroke="#2a2f45" strokeWidth={0.5} />
        </g>
      ))}

      {/* IR ring sector dividers */}
      {Array.from({ length: irCount }, (_, i) => {
        const a = deg2rad(i * sectorDeg)
        return (
          <line key={i}
            x1={Math.cos(a) * (radius + 2)}
            y1={-Math.sin(a) * (radius + 2)}
            x2={Math.cos(a) * (radius + 18)}
            y2={-Math.sin(a) * (radius + 18)}
            stroke="#3d4466" strokeWidth={0.8}
          />
        )
      })}

      {/* IR ring outer arc */}
      <circle cx={0} cy={0} r={radius + 18}
        fill="none" stroke="#3d4466" strokeWidth={0.8}
        strokeDasharray="2 2"
      />

      {/* Ultrasound beams */}
      {usDirs.map((dir, i) => {
        const a  = deg2rad(dir)
        const sx = Math.cos(a) * radius
        const sy = -Math.sin(a) * radius
        const ex = Math.cos(a) * (radius + MAX_US)
        const ey = -Math.sin(a) * (radius + MAX_US)
        return (
          <g key={i}>
            <line x1={sx} y1={sy} x2={ex} y2={ey}
              stroke="#7dcfff" strokeWidth={1.2}
              strokeDasharray="6 4" opacity={0.55}
            />
            <circle cx={ex} cy={ey} r={2.5} fill="#7dcfff" opacity={0.4} />
          </g>
        )
      })}

      {/* Kicker arc */}
      {kicker && (
        <path
          d={arcPath(0, 0, radius + 6, -20, 20)}
          fill="none" stroke="#ff9e64" strokeWidth={3.5}
          strokeLinecap="round"
        />
      )}

      {/* Robot body */}
      {isCircle ? (
        <>
          <defs>
            <radialGradient id="bodyGrad" cx="35%" cy="35%">
              <stop offset="0%" stopColor="#2a3f6f" />
              <stop offset="100%" stopColor="#1a2540" />
            </radialGradient>
          </defs>
          <circle cx={0} cy={0} r={radius}
            fill="url(#bodyGrad)" stroke="#7aa2f7" strokeWidth={2}
          />
        </>
      ) : (
        <rect
          x={-width / 2} y={-height / 2}
          width={width} height={height}
          rx={4}
          fill="#1a2540" stroke="#7aa2f7" strokeWidth={2}
        />
      )}

      {/* Wheel indicators */}
      {wDots.map((w, i) => (
        <rect key={i}
          x={w.x - 5} y={w.y - 3}
          width={10} height={6}
          rx={1}
          fill="#565f89" stroke="#7aa2f7" strokeWidth={1}
          transform={isDiff ? `rotate(${i === 0 ? 0 : 0}, ${w.x}, ${w.y})` : ''}
        />
      ))}

      {/* Line sensors */}
      {lineSensors.map(([lx, ly], i) => (
        <circle key={i}
          cx={lx * SCALE}
          cy={-ly * SCALE}
          r={4}
          fill="#9ece6a"
          stroke="#1a1b26"
          strokeWidth={1}
        />
      ))}

      {/* Heading arrow */}
      <line x1={0} y1={0} x2={radius - 4} y2={0}
        stroke="#f7768e" strokeWidth={2.5} strokeLinecap="round"
      />
      <polygon
        points={`${radius + 2},0 ${radius - 6},-4 ${radius - 6},4`}
        fill="#f7768e"
      />

      {/* Center dot */}
      <circle cx={0} cy={0} r={3} fill="#e2e8f0" />

      {/* Legend */}
      {[
        { color: '#f7768e', label: 'Heading' },
        { color: '#9ece6a', label: 'Line sensors' },
        { color: '#7dcfff', label: 'Ultrasound' },
        { color: '#ff9e64', label: 'Kicker' },
        { color: '#3d4466', label: `IR ring (${irCount}×)` },
      ].map(({ color, label }, i) => (
        <g key={i} transform={`translate(${-V + 8}, ${V - 14 - i * 16})`}>
          <rect x={0} y={-7} width={10} height={8} rx={1} fill={color} />
          <text x={14} y={0} fill="#565f89" fontSize={9}>{label}</text>
        </g>
      ))}
    </svg>
  )
}
