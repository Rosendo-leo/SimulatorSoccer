// URL do backend (FastAPI). Em produção (Vercel), defina a env var
// VITE_SERVER_URL no projeto, ex.: https://rcj-sim.onrender.com
// Em dev deixe vazia: REST usa o proxy do Vite e o WS vai para localhost:8000.
const SERVER_URL = (import.meta.env.VITE_SERVER_URL ?? '').replace(/\/+$/, '')

export const API_BASE = SERVER_URL

export const WS_URL = SERVER_URL
  ? SERVER_URL.replace(/^http/, 'ws') + '/ws/sim'   // https → wss, http → ws
  : 'ws://localhost:8000/ws/sim'
