import { useState, useEffect } from 'react'
import { getPerfil, postPerfil } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'
import ErrorState from '../components/ErrorState'

const CAMPOS_EDITABLES = [
  { key: 'equipamiento_disponible', label: 'Equipamiento del gym', placeholder: 'Ej: rack, barra olímpica, mancuernas 5-40kg, polea, máquina pec-deck', multiline: true },
  { key: 'horas_sueno_habitual', label: 'Horario de sueño habitual', placeholder: 'Ej: 23:30-07:00' },
  { key: 'nivel_estres_habitual', label: 'Nivel de estrés habitual', placeholder: 'Ej: moderado' },
  { key: 'disponibilidad_cocinar', label: 'Disponibilidad para cocinar', placeholder: 'Ej: 30 min, cocino los domingos' },
]

const CAMPOS_INFO = [
  { key: 'nombre', label: 'Nombre' },
  { key: 'edad', label: 'Edad' },
  { key: 'sexo', label: 'Sexo' },
  { key: 'peso_kg', label: 'Peso (kg)' },
  { key: 'altura_cm', label: 'Altura (cm)' },
  { key: 'nivel_experiencia', label: 'Experiencia' },
  { key: 'lugar_entrenamiento', label: 'Lugar de entreno' },
  { key: 'dieta_tipo', label: 'Tipo de dieta' },
  { key: 'suplementos_actuales', label: 'Suplementos' },
  { key: 'lesiones_actuales', label: 'Lesiones actuales' },
]

export default function Perfil() {
  const [perfil, setPerfil] = useState({})
  const [edits, setEdits] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getPerfil()
      setPerfil(data)
      const inicial = {}
      CAMPOS_EDITABLES.forEach(({ key }) => { inicial[key] = data[key] || '' })
      setEdits(inicial)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const guardar = async () => {
    setSaving(true)
    try {
      const actualizado = await postPerfil(edits)
      setPerfil(actualizado)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Loading text="Cargando perfil..." />
  if (error) return <ErrorState error={error} retry={cargar} />

  return (
    <div style={{ padding: '20px 16px', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.2rem', margin: '0 0 20px', color: 'var(--text)' }}>
        Perfil
      </h1>

      <Card style={{ marginBottom: 12 }}>
        <h2 className="label" style={{ margin: '0 0 14px' }}>
          Datos personales
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 16px' }}>
          {CAMPOS_INFO.map(({ key, label }) => perfil[key] ? (
            <div key={key}>
              <div className="label" style={{ marginBottom: 2 }}>{label}</div>
              <div className="num" style={{ fontSize: '0.9rem' }}>{perfil[key]}</div>
            </div>
          ) : null)}
        </div>
      </Card>

      <Card>
        <h2 className="label" style={{ margin: '0 0 6px' }}>
          Datos para el coach
        </h2>
        <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem', margin: '0 0 16px' }}>
          El coach usa esta información para personalizar tu plan.
        </p>

        {CAMPOS_EDITABLES.map(({ key, label, placeholder, multiline }) => (
          <div key={key} style={{ marginBottom: 16 }}>
            <label className="label" style={{ display: 'block', marginBottom: 6 }}>
              {label}
            </label>
            {multiline ? (
              <textarea
                value={edits[key] || ''}
                onChange={e => setEdits(prev => ({ ...prev, [key]: e.target.value }))}
                placeholder={placeholder}
                rows={3}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  resize: 'vertical',
                  fontSize: 16,
                  minHeight: 70,
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-lg)',
                  color: 'var(--text)',
                  boxSizing: 'border-box',
                }}
              />
            ) : (
              <input
                type="text"
                value={edits[key] || ''}
                onChange={e => setEdits(prev => ({ ...prev, [key]: e.target.value }))}
                placeholder={placeholder}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  fontSize: 16,
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-lg)',
                  color: 'var(--text)',
                  boxSizing: 'border-box',
                }}
              />
            )}
          </div>
        ))}

        <button
          onClick={guardar}
          disabled={saving}
          style={{
            width: '100%',
            padding: '14px 0',
            background: saved ? 'transparent' : 'var(--accent)',
            color: saved ? 'var(--data-good)' : 'var(--bg)',
            border: saved ? '1px solid var(--data-good)' : 'none',
            borderRadius: 'var(--r-lg)',
            fontWeight: 600,
            fontSize: '0.95rem',
            cursor: saving ? 'not-allowed' : 'pointer',
            fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            opacity: saving ? 0.7 : 1,
            transition: 'background var(--t-base), color var(--t-base), border-color var(--t-base)',
          }}
        >
          {saving ? 'Guardando…' : saved ? 'Guardado' : 'Guardar cambios'}
        </button>
      </Card>
    </div>
  )
}
