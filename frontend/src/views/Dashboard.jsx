import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getNutricionHoy, getRutina, getHistorial, getCheckinHoy } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'

function StatRow({ label, value, unit }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
      <span className="label">{label}</span>
      <span className="num" style={{ fontWeight: 600, fontSize: '0.95rem' }}>
        {value} {unit && <span style={{ color: 'var(--text-dim)', fontWeight: 400, fontSize: '0.78rem' }}>{unit}</span>}
      </span>
    </div>
  )
}

function RecoveryDot({ val, max = 5 }) {
  const pct = val / max
  const color = pct >= 0.7 ? 'var(--data-good)' : pct >= 0.45 ? 'var(--data-warn)' : 'var(--data-bad)'
  return <span className="num" style={{ color, fontWeight: 600 }}>{val}/{max}</span>
}

export default function Dashboard() {
  const [nutricion, setNutricion] = useState(null)
  const [rutina, setRutina] = useState(null)
  const [historial, setHistorial] = useState(null)
  const [checkin, setCheckin] = useState(null)
  const [loadingNut, setLoadingNut] = useState(true)
  const [loadingRut, setLoadingRut] = useState(true)
  const [loadingHist, setLoadingHist] = useState(true)

  useEffect(() => {
    getNutricionHoy().then(setNutricion).catch(() => {}).finally(() => setLoadingNut(false))
    getRutina().then(setRutina).catch(() => {}).finally(() => setLoadingRut(false))
    getHistorial().then(setHistorial).catch(() => {}).finally(() => setLoadingHist(false))
    getCheckinHoy().then(d => { if (d && d.fatiga) setCheckin(d) }).catch(() => {})
  }, [])

  const ultimaSesion = historial?.sesiones?.[0]

  return (
    <div style={{ padding: '20px 16px', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.2rem', margin: '0 0 20px', color: 'var(--text)' }}>
        Dashboard
      </h1>

      {/* Recuperación hoy */}
      <Link to="/checkin" style={{ textDecoration: 'none' }}>
        <Card style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, paddingBottom: 8, borderBottom: '1px solid var(--border)' }}>
            <h2 className="label" style={{ margin: 0 }}>
              Recuperación hoy
            </h2>
            <span className="label" style={{ color: 'var(--accent)' }}>
              {checkin ? 'Registrado' : 'Registrar →'}
            </span>
          </div>
          {checkin ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, textAlign: 'center' }}>
              {[
                { label: 'Fatiga', val: checkin.fatiga },
                { label: 'Sueño', val: checkin.calidad_sueno },
                { label: 'Dolor', val: checkin.dolor_muscular },
                { label: 'Mental', val: checkin.estado_mental },
              ].map(({ label, val }) => (
                <div key={label} style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '8px 4px' }}>
                  <div style={{ fontSize: '0.95rem' }}>
                    {val ? <RecoveryDot val={val} /> : <span className="num" style={{ color: 'var(--text-dim)' }}>—</span>}
                  </div>
                  <div className="label" style={{ marginTop: 2 }}>{label}</div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
              Sin check-in de hoy — toca para registrar
            </p>
          )}
        </Card>
      </Link>

      {/* Macros hoy */}
      <Link to="/nutricion" style={{ textDecoration: 'none' }}>
        <Card style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid var(--border)' }}>
            <h2 className="label" style={{ margin: 0 }}>
              Hoy · Nutrición
            </h2>
            <span className="label" style={{ color: 'var(--accent)' }}>Ver más →</span>
          </div>
          {loadingNut ? <Loading text="" /> : nutricion ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, textAlign: 'center' }}>
              {[
                { label: 'Kcal', v: nutricion.consumido.kcal, t: nutricion.objetivo.kcal, unit: '' },
                { label: 'Prot', v: nutricion.consumido.proteinas_g, t: nutricion.objetivo.proteinas_g, unit: 'g' },
                { label: 'Carbos', v: nutricion.consumido.carbos_g, t: nutricion.objetivo.carbos_g, unit: 'g' },
                { label: 'Grasas', v: nutricion.consumido.grasas_g, t: nutricion.objetivo.grasas_g, unit: 'g' },
              ].map(({ label, v, t, unit }) => (
                <div key={label} style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '8px 4px' }}>
                  <div className="num" style={{ fontSize: '1rem', fontWeight: 600 }}>{v}{unit}</div>
                  <div className="label" style={{ marginTop: 2 }}>{label}</div>
                  <div className="num" style={{ color: 'var(--text-dim)', fontSize: '0.65rem' }}>/ {t}{unit}</div>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid var(--border)' }}>
            <h2 className="label" style={{ margin: 0 }}>
              Última rutina
            </h2>
            <span className="label" style={{ color: 'var(--accent)' }}>Ver más →</span>
          </div>
          {loadingRut ? <Loading text="" /> : rutina ? (
            <div>
              <p className="num" style={{ margin: '0 0 6px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {rutina.fecha} · {rutina.ejercicios.length} ejercicios
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {rutina.ejercicios.slice(0, 4).map((ej, i) => (
                  <span key={i} style={{
                    background: 'transparent',
                    color: 'var(--text-muted)',
                    border: '1px solid var(--border-strong)',
                    borderRadius: 'var(--r-sm)',
                    padding: '2px 8px',
                    fontSize: '0.75rem',
                  }}>{ej.ejercicio}</span>
                ))}
                {rutina.ejercicios.length > 4 && (
                  <span className="num" style={{ color: 'var(--text-dim)', fontSize: '0.75rem', padding: '2px 4px' }}>
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid var(--border)' }}>
              <h2 className="label" style={{ margin: 0 }}>
                Última sesión
              </h2>
              <span className="label" style={{ color: 'var(--accent)' }}>Ver historial →</span>
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
