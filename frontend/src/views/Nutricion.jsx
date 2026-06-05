import { useState, useEffect } from 'react'
import { getNutricionHoy, getNutricionSemana } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'
import ErrorState from '../components/ErrorState'

function MacroBar({ label, consumido, objetivo, color }) {
  const pct = objetivo > 0 ? Math.min((consumido / objetivo) * 100, 100) : 0
  const over = objetivo > 0 && consumido > objetivo
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: '0.82rem', color: over ? '#f87171' : 'var(--text-muted)' }}>
          {consumido}g <span style={{ color: 'var(--text-dim)' }}>/ {objetivo}g</span>
        </span>
      </div>
      <div style={{
        height: 6,
        background: 'var(--border)',
        borderRadius: 3,
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: over ? '#f87171' : color,
          borderRadius: 3,
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

function KcalRing({ consumido, objetivo }) {
  const pct = objetivo > 0 ? Math.min((consumido / objetivo) * 100, 100) : 0
  const over = consumido > objetivo
  const delta = consumido - objetivo
  return (
    <div style={{ textAlign: 'center', padding: '8px 0 16px' }}>
      <div style={{ fontSize: '2.2rem', fontWeight: 700, color: over ? '#f87171' : 'var(--text)' }}>
        {consumido}
      </div>
      <div style={{ color: 'var(--text-dim)', fontSize: '0.82rem', marginBottom: 6 }}>
        kcal de {objetivo}
      </div>
      <div style={{
        fontSize: '0.85rem',
        color: delta < 0 ? 'var(--text-muted)' : '#f87171',
        fontWeight: 500,
      }}>
        {delta >= 0 ? `+${delta}` : delta} kcal vs objetivo
      </div>
    </div>
  )
}

function SemanaChart({ dias, objetivo }) {
  const maxKcal = Math.max(objetivo?.kcal || 1, ...dias.map(d => d.kcal))
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 80, marginBottom: 8 }}>
        {dias.map((d) => {
          const h = maxKcal > 0 ? Math.max((d.kcal / maxKcal) * 80, 2) : 2
          const over = d.kcal > (objetivo?.kcal || 0)
          const isToday = d.fecha === new Date().toISOString().split('T')[0]
          return (
            <div key={d.fecha} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>{d.kcal > 0 ? d.kcal : ''}</span>
              <div style={{
                width: '100%',
                height: h,
                background: isToday ? 'var(--accent)' : over ? '#ef444466' : 'var(--accent)55',
                borderRadius: '3px 3px 0 0',
                border: isToday ? '1px solid var(--accent-light)' : 'none',
              }} />
            </div>
          )
        })}
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        {dias.map((d) => {
          const isToday = d.fecha === new Date().toISOString().split('T')[0]
          const label = new Date(d.fecha + 'T12:00').toLocaleDateString('es', { weekday: 'short' })
          return (
            <div key={d.fecha} style={{
              flex: 1,
              textAlign: 'center',
              fontSize: '0.65rem',
              color: isToday ? 'var(--accent-soft)' : 'var(--text-dim)',
              fontWeight: isToday ? 600 : 400,
            }}>
              {label}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function Nutricion() {
  const [hoy, setHoy] = useState(null)
  const [semana, setSemana] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      const [h, s] = await Promise.all([getNutricionHoy(), getNutricionSemana()])
      setHoy(h)
      setSemana(s)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  if (loading) return <Loading text="Calculando macros..." />
  if (error) return <ErrorState error={error} retry={cargar} />

  const { objetivo, consumido, comidas } = hoy

  return (
    <div style={{ padding: '20px 16px', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.2rem', fontWeight: 600, margin: '0 0 4px', color: 'var(--text)' }}>
        Nutrición
      </h1>
      <p style={{ color: 'var(--text-dim)', fontSize: '0.82rem', margin: '0 0 20px' }}>
        Hoy · {hoy.fecha}
      </p>

      <Card style={{ marginBottom: 12 }}>
        <KcalRing consumido={consumido.kcal} objetivo={objetivo.kcal} />
        <MacroBar label="Proteína" consumido={consumido.proteinas_g} objetivo={objetivo.proteinas_g} color="#818cf8" />
        <MacroBar label="Carbohidratos" consumido={consumido.carbos_g} objetivo={objetivo.carbos_g} color="#34d399" />
        <MacroBar label="Grasas" consumido={consumido.grasas_g} objetivo={objetivo.grasas_g} color="#fb923c" />
        {objetivo.fecha_calculo && (
          <p style={{ color: 'var(--text-dim)', fontSize: '0.72rem', margin: '8px 0 0', textAlign: 'right' }}>
            Objetivo calculado por IA · {objetivo.fecha_calculo}
          </p>
        )}
      </Card>

      {semana && (
        <Card style={{ marginBottom: 12 }}>
          <h2 style={{ fontSize: '0.9rem', fontWeight: 600, margin: '0 0 14px', color: 'var(--text-muted)' }}>
            Última semana
          </h2>
          <SemanaChart dias={semana.dias} objetivo={semana.objetivo} />
        </Card>
      )}

      {comidas.length > 0 && (
        <div>
          <h2 style={{ fontSize: '0.9rem', fontWeight: 600, margin: '16px 0 10px', color: 'var(--text-muted)' }}>
            Comidas de hoy
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {comidas.map((c, i) => (
              <Card key={i}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{c.alimento}</div>
                    <div style={{ color: 'var(--text-dim)', fontSize: '0.78rem', marginTop: 2 }}>
                      {c.hora} · {c.tipo_comida}
                      {c.cantidad_g_ml > 0 && ` · ${c.cantidad_g_ml}g`}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{c.calorias} kcal</div>
                    <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                      P{c.proteinas_g} C{c.carbos_g} G{c.grasas_g}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {comidas.length === 0 && (
        <p style={{ color: 'var(--text-dim)', fontSize: '0.88rem', textAlign: 'center', padding: '20px 0' }}>
          Sin comidas registradas hoy. Cuéntale al coach lo que has comido.
        </p>
      )}
    </div>
  )
}
