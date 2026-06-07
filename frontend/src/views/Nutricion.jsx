import { useState, useEffect } from 'react'
import { getNutricionHoy, getNutricionSemana, getNutricionTiming } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'
import ErrorState from '../components/ErrorState'

const MACRO_COLOR = {
  'Proteína': 'var(--accent)',
  'Carbohidratos': 'var(--text-muted)',
  'Grasas': 'var(--accent-dim)',
}

function MacroBar({ label, consumido, objetivo }) {
  const pct = objetivo > 0 ? Math.min((consumido / objetivo) * 100, 100) : 0
  const over = objetivo > 0 && consumido > objetivo
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{label}</span>
        <span className="num" style={{ fontSize: '0.82rem', color: over ? 'var(--data-bad)' : 'var(--text-muted)' }}>
          {consumido}g <span style={{ color: 'var(--text-dim)' }}>/ {objetivo}g</span>
        </span>
      </div>
      <div style={{
        height: 5,
        background: 'var(--border)',
        borderRadius: 'var(--r-sm)',
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: over ? 'var(--data-bad)' : MACRO_COLOR[label] || 'var(--accent)',
          borderRadius: 'var(--r-sm)',
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

function KcalRing({ consumido, objetivo }) {
  const over = consumido > objetivo
  const delta = consumido - objetivo
  return (
    <div style={{ textAlign: 'center', padding: '8px 0 16px' }}>
      <div className="num" style={{ fontSize: '2.2rem', fontWeight: 600, color: 'var(--text)' }}>
        {consumido}
      </div>
      <div className="label" style={{ marginBottom: 6 }}>
        kcal de {objetivo}
      </div>
      <div className="num" style={{
        fontSize: '0.85rem',
        color: over ? 'var(--data-bad)' : 'var(--text-muted)',
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
              <span className="num" style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>{d.kcal > 0 ? d.kcal : ''}</span>
              <div style={{
                width: '100%',
                height: h,
                background: isToday ? 'var(--accent)' : over ? 'var(--data-bad)' : 'var(--bg-card-raised)',
                opacity: isToday ? 1 : over ? 0.55 : 1,
                borderRadius: 'var(--r-sm) var(--r-sm) 0 0',
                border: isToday ? 'none' : '1px solid var(--border)',
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
            <div key={d.fecha} className="num" style={{
              flex: 1,
              textAlign: 'center',
              fontSize: '0.65rem',
              color: isToday ? 'var(--accent)' : 'var(--text-dim)',
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

const PROPOSITO_LABEL = {
  inicio_dia: 'Inicio del día',
  pre_entreno: 'Pre-entreno',
  post_entreno: 'Post-entreno',
  media_manana: 'Media mañana',
  almuerzo: 'Almuerzo',
  merienda: 'Merienda',
  cena: 'Cena',
}

function TomaPlan({ toma }) {
  const label = PROPOSITO_LABEL[toma.proposito] || toma.nombre
  return (
    <Card style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
            <span className="num" style={{ fontWeight: 600, fontSize: '0.92rem' }}>{toma.hora}</span>
            <span className="label">{label}</span>
          </div>
          {toma.ejemplos?.length > 0 && (
            <div style={{ color: 'var(--text-dim)', fontSize: '0.78rem', marginTop: 3 }}>
              {toma.ejemplos.slice(0, 2).join(' · ')}
            </div>
          )}
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 12 }}>
          <div className="num" style={{ fontWeight: 600, fontSize: '0.9rem' }}>{toma.kcal} kcal</div>
          <div className="num" style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>
            P{toma.proteinas_g} C{toma.carbos_g} G{toma.grasas_g}
          </div>
        </div>
      </div>
    </Card>
  )
}

export default function Nutricion() {
  const [hoy, setHoy] = useState(null)
  const [semana, setSemana] = useState(null)
  const [timing, setTiming] = useState(null)
  const [timingLoading, setTimingLoading] = useState(false)
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
    // Timing carga en paralelo sin bloquear el resto
    try {
      const t = await getNutricionTiming()
      if (t?.tomas?.length > 0) setTiming(t)
    } catch {
      // No crítico — se omite sin error visible
    }
  }

  const generarPlan = async () => {
    setTimingLoading(true)
    try {
      const t = await getNutricionTiming(true)
      if (t?.tomas?.length > 0) setTiming(t)
    } catch (e) {
      console.error('Error generando plan:', e)
    } finally {
      setTimingLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  if (loading) return <Loading text="Calculando macros..." />
  if (error) return <ErrorState error={error} retry={cargar} />

  const { objetivo, consumido, comidas } = hoy

  return (
    <div style={{ padding: '20px 16px', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.2rem', margin: '0 0 4px', color: 'var(--text)' }}>
        Nutrición
      </h1>
      <p className="num" style={{ color: 'var(--text-dim)', fontSize: '0.82rem', margin: '0 0 20px' }}>
        Hoy · {hoy.fecha}
      </p>

      {/* Plan nutricional con timing */}
      {timing ? (
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h2 className="label" style={{ margin: 0 }}>
              Plan de comidas de hoy
              {timing.hora_entreno && (
                <span className="num" style={{ color: 'var(--text-dim)', fontWeight: 400, marginLeft: 8, textTransform: 'none', letterSpacing: 0 }}>
                  · entreno {timing.hora_entreno}
                </span>
              )}
            </h2>
            <button
              onClick={generarPlan}
              disabled={timingLoading}
              style={{
                background: 'none', border: '1px solid var(--border-strong)',
                color: 'var(--text-dim)', borderRadius: 'var(--r-sm)', padding: '3px 10px',
                fontSize: '0.7rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em',
                cursor: 'pointer', opacity: timingLoading ? 0.5 : 1,
              }}
            >
              {timingLoading ? '...' : 'Regenerar'}
            </button>
          </div>
          {timing.tomas.map((t, i) => <TomaPlan key={i} toma={t} />)}
          {timing.notas && (
            <p style={{ color: 'var(--text-dim)', fontSize: '0.78rem', margin: '8px 4px 0' }}>
              {timing.notas}
            </p>
          )}
        </div>
      ) : (
        <Card style={{ marginBottom: 16, textAlign: 'center', padding: '16px' }}>
          <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: '0 0 10px' }}>
            Sin plan de comidas generado para hoy
          </p>
          <button
            onClick={generarPlan}
            disabled={timingLoading}
            style={{
              background: 'transparent', color: 'var(--accent)', border: '1px solid var(--border-strong)',
              borderRadius: 'var(--r-sm)', padding: '8px 18px', fontSize: '0.8rem',
              fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em',
              cursor: 'pointer', opacity: timingLoading ? 0.6 : 1,
            }}
          >
            {timingLoading ? 'Generando...' : 'Generar plan de hoy'}
          </button>
        </Card>
      )}

      <Card style={{ marginBottom: 12 }}>
        <KcalRing consumido={consumido.kcal} objetivo={objetivo.kcal} />
        <MacroBar label="Proteína" consumido={consumido.proteinas_g} objetivo={objetivo.proteinas_g} />
        <MacroBar label="Carbohidratos" consumido={consumido.carbos_g} objetivo={objetivo.carbos_g} />
        <MacroBar label="Grasas" consumido={consumido.grasas_g} objetivo={objetivo.grasas_g} />
        {objetivo.fecha_calculo && (
          <p className="num" style={{ color: 'var(--text-dim)', fontSize: '0.72rem', margin: '8px 0 0', textAlign: 'right' }}>
            Objetivo calculado por IA · {objetivo.fecha_calculo}
          </p>
        )}
      </Card>

      {semana && (
        <Card style={{ marginBottom: 12 }}>
          <h2 className="label" style={{ margin: '0 0 14px' }}>
            Última semana
          </h2>
          <SemanaChart dias={semana.dias} objetivo={semana.objetivo} />
        </Card>
      )}

      {comidas.length > 0 && (
        <div>
          <h2 className="label" style={{ margin: '16px 0 10px' }}>
            Comidas de hoy
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {comidas.map((c, i) => (
              <Card key={i}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{c.alimento}</div>
                    <div className="num" style={{ color: 'var(--text-dim)', fontSize: '0.78rem', marginTop: 2 }}>
                      {c.hora} · {c.tipo_comida}
                      {c.cantidad_g_ml > 0 && ` · ${c.cantidad_g_ml}g`}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div className="num" style={{ fontWeight: 600, fontSize: '0.9rem' }}>{c.calorias} kcal</div>
                    <div className="num" style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>
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
