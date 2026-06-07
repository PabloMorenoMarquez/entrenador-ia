import { useState, useEffect } from 'react'
import { getRutina } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'
import ErrorState from '../components/ErrorState'

function GrupoBadge({ grupo }) {
  return (
    <span className="label" style={{
      display: 'inline-block',
      border: '1px solid var(--border-strong)',
      borderRadius: 'var(--r-sm)',
      padding: '1px 8px',
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
      <h1 style={{ fontSize: '1.2rem', margin: '0 0 4px', color: 'var(--text)' }}>
        Última rutina
      </h1>
      <p className="num" style={{ color: 'var(--text-dim)', fontSize: '0.82rem', margin: '0 0 20px' }}>
        {fecha} · {ejercicios.length} ejercicios
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {ejercicios.map((ej) => (
          <Card key={ej.orden}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 6 }}>
                  <span className="num" style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                    {ej.orden}.
                  </span>
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{ej.ejercicio}</span>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
                  {ej.grupo_muscular && <GrupoBadge grupo={ej.grupo_muscular} />}
                  {ej.tipo_peso && (
                    <span className="label">{ej.tipo_peso}</span>
                  )}
                </div>
                {ej.notas && (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: '8px 0 0' }}>
                    {ej.notas}
                  </p>
                )}
              </div>
              <div className="num" style={{ textAlign: 'right', flexShrink: 0, fontSize: '0.85rem', color: 'var(--text)' }}>
                <div>{ej.series} × {ej.reps_objetivo}</div>
                {ej.peso_kg > 0 && (
                  <div style={{ color: 'var(--text-muted)', marginTop: 2 }}>{ej.peso_kg} kg</div>
                )}
                {ej.rir !== null && ej.rir !== undefined && ej.rir !== '' && (
                  <div style={{ color: 'var(--accent)', marginTop: 2, fontSize: '0.78rem' }}>RIR {ej.rir}</div>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
