import { useState, useEffect } from 'react'
import { getHistorial } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'
import ErrorState from '../components/ErrorState'

function EnergyBars({ value, max, color }) {
  return (
    <div style={{ display: 'flex', gap: 2 }}>
      {Array.from({ length: max }).map((_, i) => (
        <div key={i} style={{
          width: 5, height: 10, borderRadius: 1,
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
      <h1 style={{ fontSize: '1.2rem', margin: '0 0 4px', color: 'var(--text)' }}>
        Historial
      </h1>
      <p className="num" style={{ color: 'var(--text-dim)', fontSize: '0.82rem', margin: '0 0 20px' }}>
        {sesiones.length} sesiones registradas
      </p>

      {sesiones.length === 0 && (
        <p style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '40px 0' }}>
          Sin sesiones todavía. Registra tu primer entreno por chat.
        </p>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {sesiones.map((s) => (
          <Card key={s.sesion_id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="num" style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: 6 }}>
                  {s.fecha}
                  {s.hora_inicio && (
                    <span style={{ color: 'var(--text-dim)', fontWeight: 400, fontSize: '0.8rem', marginLeft: 8 }}>
                      {s.hora_inicio}
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', marginBottom: 8 }}>
                  {s.tipo_sesion && (
                    <span className="label" style={{
                      border: '1px solid var(--border-strong)',
                      borderRadius: 'var(--r-sm)',
                      padding: '1px 8px',
                    }}>{s.tipo_sesion}</span>
                  )}
                  {s.grupo_muscular_principal && (
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                      {s.grupo_muscular_principal}
                    </span>
                  )}
                </div>
                <div className="num" style={{ display: 'flex', gap: 16, flexWrap: 'wrap', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                  {s.duracion_min > 0 && <span>{s.duracion_min} min</span>}
                  {s.volumen_total_kg > 0 && <span>{s.volumen_total_kg} kg vol.</span>}
                </div>
                {s.notas && (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: '8px 0 0' }}>
                    {s.notas}
                  </p>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end', flexShrink: 0 }}>
                {s.nivel_energia > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span className="label">Energía</span>
                    <EnergyBars value={s.nivel_energia} max={5} color="var(--data-good)" />
                  </div>
                )}
                {s.nivel_esfuerzo > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span className="label">RPE</span>
                    <EnergyBars value={Math.round(s.nivel_esfuerzo / 2)} max={5} color="var(--data-warn)" />
                  </div>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
