import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getNutricionHoy, getRutina, getHistorial } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'

function StatRow({ label, value, unit }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>{label}</span>
      <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
        {value} {unit && <span style={{ color: 'var(--text-dim)', fontWeight: 400, fontSize: '0.78rem' }}>{unit}</span>}
      </span>
    </div>
  )
}

export default function Dashboard() {
  const [nutricion, setNutricion] = useState(null)
  const [rutina, setRutina] = useState(null)
  const [historial, setHistorial] = useState(null)
  const [loadingNut, setLoadingNut] = useState(true)
  const [loadingRut, setLoadingRut] = useState(true)
  const [loadingHist, setLoadingHist] = useState(true)

  useEffect(() => {
    getNutricionHoy().then(setNutricion).catch(() => {}).finally(() => setLoadingNut(false))
    getRutina().then(setRutina).catch(() => {}).finally(() => setLoadingRut(false))
    getHistorial().then(setHistorial).catch(() => {}).finally(() => setLoadingHist(false))
  }, [])

  const ultimaSesion = historial?.sesiones?.[0]

  return (
    <div style={{ padding: '20px 16px', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.2rem', fontWeight: 600, margin: '0 0 20px', color: 'var(--text)' }}>
        Dashboard
      </h1>

      {/* Macros hoy */}
      <Link to="/nutricion" style={{ textDecoration: 'none' }}>
        <Card style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h2 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Hoy · Nutrición
            </h2>
            <span style={{ color: 'var(--accent-soft)', fontSize: '0.75rem' }}>Ver más →</span>
          </div>
          {loadingNut ? <Loading text="" /> : nutricion ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, textAlign: 'center' }}>
              {[
                { label: 'Kcal', v: nutricion.consumido.kcal, t: nutricion.objetivo.kcal, unit: '' },
                { label: 'Prot', v: nutricion.consumido.proteinas_g, t: nutricion.objetivo.proteinas_g, unit: 'g' },
                { label: 'Carbos', v: nutricion.consumido.carbos_g, t: nutricion.objetivo.carbos_g, unit: 'g' },
                { label: 'Grasas', v: nutricion.consumido.grasas_g, t: nutricion.objetivo.grasas_g, unit: 'g' },
              ].map(({ label, v, t, unit }) => (
                <div key={label} style={{ background: 'var(--bg)', borderRadius: 8, padding: '8px 4px' }}>
                  <div style={{ fontSize: '1rem', fontWeight: 700 }}>{v}{unit}</div>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.68rem' }}>{label}</div>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.65rem' }}>/ {t}{unit}</div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>Sin datos de nutrición</p>
          )}
        </Card>
      </Link>

      {/* Última rutina */}
      <Link to="/rutina" style={{ textDecoration: 'none' }}>
        <Card style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h2 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Última rutina
            </h2>
            <span style={{ color: 'var(--accent-soft)', fontSize: '0.75rem' }}>Ver más →</span>
          </div>
          {loadingRut ? <Loading text="" /> : rutina ? (
            <div>
              <p style={{ margin: '0 0 6px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {rutina.fecha} · {rutina.ejercicios.length} ejercicios
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {rutina.ejercicios.slice(0, 4).map((ej, i) => (
                  <span key={i} style={{
                    background: 'var(--accent)22',
                    color: 'var(--accent-soft)',
                    border: '1px solid var(--accent)33',
                    borderRadius: 6,
                    padding: '2px 8px',
                    fontSize: '0.75rem',
                  }}>{ej.ejercicio}</span>
                ))}
                {rutina.ejercicios.length > 4 && (
                  <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem', padding: '2px 4px' }}>
                    +{rutina.ejercicios.length - 4} más
                  </span>
                )}
              </div>
            </div>
          ) : (
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>Sin sesiones registradas</p>
          )}
        </Card>
      </Link>

      {/* Última sesión stats */}
      {!loadingHist && ultimaSesion && (
        <Link to="/historial" style={{ textDecoration: 'none' }}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <h2 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Última sesión
              </h2>
              <span style={{ color: 'var(--accent-soft)', fontSize: '0.75rem' }}>Ver historial →</span>
            </div>
            <StatRow label="Fecha" value={ultimaSesion.fecha} />
            <StatRow label="Tipo" value={ultimaSesion.tipo_sesion || '—'} />
            {ultimaSesion.duracion_min > 0 && <StatRow label="Duración" value={ultimaSesion.duracion_min} unit="min" />}
            {ultimaSesion.nivel_energia > 0 && <StatRow label="Energía" value={`${ultimaSesion.nivel_energia}/5`} />}
            {ultimaSesion.nivel_esfuerzo > 0 && <StatRow label="Esfuerzo" value={`${ultimaSesion.nivel_esfuerzo}/10`} />}
            {ultimaSesion.volumen_total_kg > 0 && <StatRow label="Volumen total" value={ultimaSesion.volumen_total_kg} unit="kg" />}
          </Card>
        </Link>
      )}
    </div>
  )
}
