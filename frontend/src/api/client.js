const BASE = ''

async function apiFetch(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const getPerfil = () => apiFetch('/api/perfil')
export const postPerfil = (campos) => apiFetch('/api/perfil', { method: 'POST', body: JSON.stringify({ campos }) })
export const getRutina = () => apiFetch('/api/rutina')
export const getRutinaPlan = () => apiFetch('/api/rutina/plan')
export const postRutinaPlanDia = (dia_semana, ejercicios) =>
  apiFetch('/api/rutina/plan', { method: 'POST', body: JSON.stringify({ dia_semana, ejercicios }) })
export const getNutricionHoy = () => apiFetch('/api/nutricion/hoy')
export const getNutricionSemana = () => apiFetch('/api/nutricion/semana')
export const getHistorial = () => apiFetch('/api/historial')
export const postChat = (mensaje) => apiFetch('/chat', { method: 'POST', body: JSON.stringify({ mensaje }) })

// Fase 1: recuperación y biométricos
export const getCheckinHoy = () => apiFetch('/api/checkin/hoy')
export const postCheckin = (datos) => apiFetch('/api/checkin', { method: 'POST', body: JSON.stringify(datos) })
export const getBiometricosHoy = () => apiFetch('/api/biometricos/hoy')
export const postBiometricos = (datos) => apiFetch('/api/biometricos', { method: 'POST', body: JSON.stringify(datos) })
export const postMedidas = (datos) => apiFetch('/api/medidas', { method: 'POST', body: JSON.stringify(datos) })
export const getMedidas = () => apiFetch('/api/medidas')
export const postHidratacion = (litros) => apiFetch('/api/hidratacion', { method: 'POST', body: JSON.stringify({ litros }) })
export const postDolor = (datos) => apiFetch('/api/dolor', { method: 'POST', body: JSON.stringify(datos) })
export const getDoloresActivos = () => apiFetch('/api/dolor/activos')

// Fase 5: plan nutricional con timing
export const getNutricionTiming = (recalcular = false) =>
  apiFetch(`/api/nutricion/timing${recalcular ? '?recalcular=true' : ''}`)
