import { useState, useEffect } from 'react'
import { getHistorial } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'
import ErrorState from '../components/ErrorState'

function EnergyDots({ value, max, color }) {
  return (
    <div style={{ display: 'flex', gap: 3 }}>
      {Array.from({ length: max }).map((_, i) => (
        <div key={i} style={{
          width: 6, height: 6, borderRadius: '50%',
          background: i < value ? color : 'var(--border)',
        }} />
      ))}
    </div>
  )
}

export default function Historial() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await getHistorial())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  if (loading) return <Loading text="Cargando historial..." />
  if (error) return <ErrorState error={error} retry={cargar} />

  const { sesiones } = data

  return (
    <div style={{ padding: '20px 16px', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.2rem', fontWeight: 600, margin: '0 0 4px', color: 'var(--text)' }}>
        Historial
      </h1>
      <p style={{ color: 'var(--text-dim)', fontSize: '0.82rem', margin: '0 0 20px' }}>
        {sesiones.length} sesiones registradas
      </p>

      {sesiones.length === 0 && (
        <p style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '40px 0' }}>
          Sin sesiones todavía. Registra tu primer entreno por chat.
        </p>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {sesiones.map((s) => (
          <Card key={s.sesion_id} className="fade-up">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: 4 }}>
                  {s.fecha}
                  {s.hora_inicio && (
                    <span style={{ color: 'var(--text-dim)', fontWeight: 400, fontSize: '0.8rem', marginLeft: 8 }}>
                      {s.hora_inicio}
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 6 }}>
                  {s.tipo_sesion && (
                    <span style={{
                      background: 'var(--accent)22',
                      color: 'var(--accent-soft)',
                      border: '1px solid var(--accent)33',
                      borderRadius: 6,
                      padding: '1px 8px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                    }}>{s.tipo_sesion}</span>
                  )}
                  {s.grupo_muscular_principal && (
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                      {s.grupo_muscular_principal}
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  {s.duracion_min > 0 && (
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                      </svg>
                      {s.duracion_min} min
                    </span>
                  )}
                  {s.volumen_total_kg > 0 && (
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M6 4v16M18 4v16M3 8h18M3 16h18"/>
                      </svg>
                      {s.volumen_total_kg} kg
                    </span>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end', flexShrink: 0 }}>
                {s.nivel_energia > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>E</span>
                    <EnergyDots value={s.nivel_energia} max={5} color="#22c55e" />
                  </div>
                )}
                {s.nivel_esfuerzo > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>RPE</span>
                    <EnergyDots value={Math.round(s.nivel_esfuerzo / 2)} max={5} color="#f59e0b" />
                  </div>
                )}
              </div>
            </div>
            {s.notas && (
              <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem', margin: '8px 0 0', fontStyle: 'italic' }}>
                {s.notas}
              </p>
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}
