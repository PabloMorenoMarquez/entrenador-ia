import { useState, useEffect } from 'react'
import { getCheckinHoy, postCheckin, getBiometricosHoy, postBiometricos, postMedidas, postDolor } from '../api/client'
import Card from '../components/Card'

const SLIDER_RAMP = ['var(--data-bad)', 'var(--data-warn)', 'var(--text-muted)', 'var(--accent)', 'var(--data-good)']

function SliderField({ label, name, value, onChange, min = 1, max = 5 }) {
  const pct = ((value - min) / (max - min)) * 100
  const color = SLIDER_RAMP[Math.round((value - min) / (max - min) * (SLIDER_RAMP.length - 1))]
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <label className="label">{label}</label>
        <span className="num" style={{ fontWeight: 600, fontSize: '1rem', color }}>{value}/{max}</span>
      </div>
      <input
        type="range" min={min} max={max} step={1} value={value}
        onChange={e => onChange(name, Number(e.target.value))}
        style={{ width: '100%', accentColor: color }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 2 }}>
        <span>{min === 1 ? 'Muy mal' : '0'}</span>
        <span>{max === 5 ? 'Perfecto' : '10'}</span>
      </div>
    </div>
  )
}

function RecoveryScore({ checkin }) {
  const vals = [checkin.fatiga, checkin.calidad_sueno, checkin.estado_mental].filter(Boolean)
  if (!vals.length) return null
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length
  const dolor_inv = checkin.dolor_muscular ? (6 - checkin.dolor_muscular) : null
  const all = dolor_inv ? [...vals, dolor_inv] : vals
  const score = Math.round((all.reduce((a, b) => a + b, 0) / all.length) * 20)
  const color = score >= 70 ? 'var(--data-good)' : score >= 45 ? 'var(--data-warn)' : 'var(--data-bad)'
  const label = score >= 70 ? 'Bien recuperado' : score >= 45 ? 'Recuperación media' : 'Fatiga alta'
  return (
    <div style={{ textAlign: 'center', padding: '12px 0 4px' }}>
      <div className="num" style={{ fontSize: '2.2rem', fontWeight: 600, color }}>{score}</div>
      <div className="label" style={{ marginTop: 4 }}>{label}</div>
    </div>
  )
}

export default function Checkin() {
  const hoy = new Date().toISOString().split('T')[0]

  const [checkin, setCheckin] = useState({ fatiga: 3, dolor_muscular: 2, calidad_sueno: 3, estado_mental: 3 })
  const [sueno, setSueno] = useState({ sueno_horas: '', hora_acostarse: '', hora_despertar: '' })
  const [medidas, setMedidas] = useState({ peso_kg: '', cintura_cm: '', brazo_cm: '' })
  const [dolor, setDolor] = useState({ zona: '', intensidad: 5 })
  const [agua, setAgua] = useState('')

  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [yaRegistrado, setYaRegistrado] = useState(false)
  const [seccion, setSeccion] = useState('checkin') // checkin | extras

  useEffect(() => {
    getCheckinHoy().then(d => {
      if (d && d.fatiga) {
        setCheckin({
          fatiga: d.fatiga ?? 3,
          dolor_muscular: d.dolor_muscular ?? 2,
          calidad_sueno: d.calidad_sueno ?? 3,
          estado_mental: d.estado_mental ?? 3,
        })
        setYaRegistrado(true)
      }
    }).catch(() => {})

    getBiometricosHoy().then(d => {
      if (d && d.sueno_horas) {
        setSueno({
          sueno_horas: d.sueno_horas ?? '',
          hora_acostarse: d.hora_acostarse ?? '',
          hora_despertar: d.hora_despertar ?? '',
        })
      }
    }).catch(() => {})
  }, [])

  const handleSlider = (name, val) => setCheckin(prev => ({ ...prev, [name]: val }))

  const handleGuardar = async () => {
    setSaving(true)
    try {
      await postCheckin({ ...checkin, fecha: hoy })

      const bioPayload = { fecha: hoy, fuente: 'manual' }
      if (sueno.sueno_horas) bioPayload.sueno_horas = parseFloat(sueno.sueno_horas)
      if (sueno.hora_acostarse) bioPayload.hora_acostarse = sueno.hora_acostarse
      if (sueno.hora_despertar) bioPayload.hora_despertar = sueno.hora_despertar
      if (Object.keys(bioPayload).length > 2) await postBiometricos(bioPayload)

      if (medidas.peso_kg || medidas.cintura_cm || medidas.brazo_cm) {
        const m = { fecha: hoy }
        if (medidas.peso_kg) m.peso_kg = parseFloat(medidas.peso_kg)
        if (medidas.cintura_cm) m.cintura_cm = parseFloat(medidas.cintura_cm)
        if (medidas.brazo_cm) m.brazo_cm = parseFloat(medidas.brazo_cm)
        await postMedidas(m)
      }

      if (dolor.zona && dolor.zona.trim()) {
        await postDolor({ zona: dolor.zona.trim(), intensidad: dolor.intensidad, fecha: hoy })
      }

      setSaved(true)
      setYaRegistrado(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      alert('Error al guardar: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ padding: '20px 16px', maxWidth: 500, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 4 }}>
        <h1 style={{ fontSize: '1.2rem', margin: 0, color: 'var(--text)' }}>
          Check-in matutino
        </h1>
        {yaRegistrado && (
          <span className="label" style={{ color: 'var(--data-good)', border: '1px solid var(--border-strong)', borderRadius: 'var(--r-sm)', padding: '2px 8px' }}>
            Registrado hoy
          </span>
        )}
      </div>
      <p className="num" style={{ fontSize: '0.8rem', color: 'var(--text-dim)', margin: '0 0 20px' }}>
        {new Date().toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })}
      </p>

      {/* Selector de sección */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid var(--border)' }}>
        {[['checkin', 'Recuperación'], ['extras', 'Sueño & Medidas']].map(([id, label]) => (
          <button key={id} onClick={() => setSeccion(id)} className="label" style={{
            flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
            background: 'transparent',
            color: seccion === id ? 'var(--accent)' : 'var(--text-dim)',
            borderBottom: seccion === id ? '2px solid var(--accent)' : '2px solid transparent',
            marginBottom: -1,
            transition: 'color var(--t-base), border-color var(--t-base)',
          }}>{label}</button>
        ))}
      </div>

      {seccion === 'checkin' && (
        <Card>
          <RecoveryScore checkin={checkin} />
          <div style={{ height: 1, background: 'var(--border)', margin: '12px 0 18px' }} />
          <SliderField label="Fatiga general" name="fatiga" value={checkin.fatiga} onChange={handleSlider} />
          <SliderField label="Dolor muscular" name="dolor_muscular" value={checkin.dolor_muscular} onChange={handleSlider} />
          <SliderField label="Calidad del sueño" name="calidad_sueno" value={checkin.calidad_sueno} onChange={handleSlider} />
          <SliderField label="Estado mental" name="estado_mental" value={checkin.estado_mental} onChange={handleSlider} />
        </Card>
      )}

      {seccion === 'extras' && (
        <div>
          <Card style={{ marginBottom: 12 }}>
            <h3 className="label" style={{ margin: '0 0 14px' }}>
              Sueño
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
              <div>
                <label className="label">Horas dormidas</label>
                <input type="number" step="0.5" min="0" max="16" value={sueno.sueno_horas}
                  onChange={e => setSueno(p => ({ ...p, sueno_horas: e.target.value }))}
                  placeholder="7.5"
                  style={{ width: '100%', padding: '8px 10px', marginTop: 4, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', color: 'var(--text)', fontSize: '0.9rem' }} />
              </div>
              <div>
                <label className="label">Acostarse</label>
                <input type="time" value={sueno.hora_acostarse}
                  onChange={e => setSueno(p => ({ ...p, hora_acostarse: e.target.value }))}
                  style={{ width: '100%', padding: '8px 10px', marginTop: 4, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', color: 'var(--text)', fontSize: '0.9rem' }} />
              </div>
            </div>
          </Card>

          <Card style={{ marginBottom: 12 }}>
            <h3 className="label" style={{ margin: '0 0 14px' }}>
              Medidas (opcional)
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
              {[
                { key: 'peso_kg', label: 'Peso (kg)', placeholder: '75.5' },
                { key: 'cintura_cm', label: 'Cintura (cm)', placeholder: '82' },
                { key: 'brazo_cm', label: 'Brazo (cm)', placeholder: '36' },
              ].map(({ key, label, placeholder }) => (
                <div key={key}>
                  <label className="label">{label}</label>
                  <input type="number" step="0.1" value={medidas[key]}
                    onChange={e => setMedidas(p => ({ ...p, [key]: e.target.value }))}
                    placeholder={placeholder}
                    style={{ width: '100%', padding: '8px 8px', marginTop: 4, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', color: 'var(--text)', fontSize: '0.9rem' }} />
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <h3 className="label" style={{ margin: '0 0 14px' }}>
              Dolor / lesión activa
            </h3>
            <input type="text" value={dolor.zona}
              onChange={e => setDolor(p => ({ ...p, zona: e.target.value }))}
              placeholder="p.ej. hombro derecho, rodilla izquierda"
              style={{ width: '100%', padding: '9px 12px', marginBottom: 10, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', color: 'var(--text)', fontSize: '0.88rem', boxSizing: 'border-box' }} />
            {dolor.zona.trim() && (
              <SliderField label={`Intensidad: ${dolor.zona}`} name="intensidad"
                value={dolor.intensidad} onChange={(_, v) => setDolor(p => ({ ...p, intensidad: v }))}
                min={0} max={10} />
            )}
          </Card>
        </div>
      )}

      <button
        onClick={handleGuardar}
        disabled={saving}
        style={{
          width: '100%', marginTop: 20, padding: '14px 0',
          background: saved ? 'transparent' : 'var(--accent)',
          color: saved ? 'var(--data-good)' : 'var(--bg)',
          border: saved ? '1px solid var(--data-good)' : 'none',
          borderRadius: 'var(--r-lg)',
          fontWeight: 600, fontSize: '0.95rem', cursor: saving ? 'not-allowed' : 'pointer',
          fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em',
          opacity: saving ? 0.7 : 1, transition: 'background var(--t-base), color var(--t-base), border-color var(--t-base)',
        }}
      >
        {saving ? 'Guardando…' : saved ? 'Guardado' : 'Registrar check-in'}
      </button>
    </div>
  )
}
