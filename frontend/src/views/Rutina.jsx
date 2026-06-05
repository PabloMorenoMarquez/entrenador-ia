import { useState, useEffect } from 'react'
import { getRutina } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'
import ErrorState from '../components/ErrorState'

const GRUPO_COLOR = {
  pecho: '#ef4444',
  espalda: '#3b82f6',
  hombros: '#a855f7',
  biceps: '#22c55e',
  triceps: '#f59e0b',
  piernas: '#f97316',
  gluteos: '#ec4899',
  core: '#06b6d4',
  cardio: '#84cc16',
}

function GrupoBadge({ grupo }) {
  const color = GRUPO_COLOR[grupo?.toLowerCase()] || 'var(--text-dim)'
  return (
    <span style={{
      display: 'inline-block',
      background: color + '22',
      color,
      border: `1px solid ${color}44`,
      borderRadius: 6,
      padding: '1px 8px',
      fontSize: '0.72rem',
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    }}>
      {grupo}
    </span>
  )
}

export default function Rutina() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await getRutina())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  if (loading) return <Loading text="Cargando rutina..." />
  if (error) return <ErrorState error={error} retry={cargar} />

  const { sesion_id, fecha, ejercicios } = data

  return (
    <div style={{ padding: '20px 16px', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.2rem', fontWeight: 600, margin: '0 0 4px', color: 'var(--text)' }}>
        Última rutina
      </h1>
      <p style={{ color: 'var(--text-dim)', fontSize: '0.82rem', margin: '0 0 20px' }}>
        {fecha} · {ejercicios.length} ejercicios
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {ejercicios.map((ej) => (
          <Card key={ej.orden} className="fade-up">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: 6 }}>
                  <span style={{ color: 'var(--text-dim)', marginRight: 6, fontSize: '0.8rem' }}>
                    {ej.orden}.
                  </span>
                  {ej.ejercicio}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {ej.grupo_muscular && <GrupoBadge grupo={ej.grupo_muscular} />}
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    {ej.series} series × {ej.reps_objetivo} reps
                  </span>
                  {ej.peso_kg > 0 && (
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      · {ej.peso_kg} kg
                    </span>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
                {ej.rir !== null && ej.rir !== undefined && ej.rir !== '' && (
                  <span style={{
                    background: 'var(--accent)22',
                    color: 'var(--accent-soft)',
                    border: '1px solid var(--accent)44',
                    borderRadius: 6,
                    padding: '1px 8px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                  }}>
                    RIR {ej.rir}
                  </span>
                )}
                {ej.tipo_peso && (
                  <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>{ej.tipo_peso}</span>
                )}
              </div>
            </div>
            {ej.notas && (
              <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem', margin: '8px 0 0', fontStyle: 'italic' }}>
                {ej.notas}
              </p>
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}
