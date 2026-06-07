import { useState, useEffect } from 'react'
import { getRutinaPlan, postRutinaPlanDia } from '../api/client'
import Card from '../components/Card'
import Loading from '../components/Loading'
import ErrorState from '../components/ErrorState'

const DIAS = [
  { key: 'lunes', label: 'Lunes' },
  { key: 'martes', label: 'Martes' },
  { key: 'miercoles', label: 'Miércoles' },
  { key: 'jueves', label: 'Jueves' },
  { key: 'viernes', label: 'Viernes' },
  { key: 'sabado', label: 'Sábado' },
  { key: 'domingo', label: 'Domingo' },
]

function filaVacia() {
  return { ejercicio: '', grupo_muscular: '', series_objetivo: '', reps_objetivo: '', notas: '' }
}

function GrupoBadge({ grupo }) {
  if (!grupo) return null
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

const inputSx = {
  width: '100%',
  padding: '8px 10px',
  fontSize: 14,
  background: 'var(--bg)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-sm)',
  color: 'var(--text)',
  boxSizing: 'border-box',
}

function btnSx(variant) {
  const base = {
    padding: '9px 14px',
    fontSize: '0.82rem',
    fontWeight: 600,
    borderRadius: 'var(--r-sm)',
    cursor: 'pointer',
    fontFamily: 'var(--font-mono)',
    border: '1px solid var(--border-strong)',
    background: 'transparent',
    color: 'var(--text-muted)',
  }
  if (variant === 'primary') {
    return { ...base, background: 'var(--accent)', color: 'var(--bg)', border: 'none' }
  }
  return base
}

function FilaEditable({ fila, onChange, onQuitar }) {
  const set = (campo, valor) => onChange({ ...fila, [campo]: valor })
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '10px', background: 'var(--bg-card-raised)', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', gap: 6 }}>
        <input style={inputSx} placeholder="Ejercicio" value={fila.ejercicio} onChange={e => set('ejercicio', e.target.value)} />
        <button onClick={onQuitar} style={{ ...btnSx(), padding: '8px 10px', flexShrink: 0 }}>Quitar</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
        <input style={inputSx} placeholder="Grupo muscular" value={fila.grupo_muscular} onChange={e => set('grupo_muscular', e.target.value)} />
        <input style={inputSx} type="number" min="0" placeholder="Series obj." value={fila.series_objetivo} onChange={e => set('series_objetivo', e.target.value)} />
        <input style={inputSx} placeholder="Reps obj. (ej: 8-10)" value={fila.reps_objetivo} onChange={e => set('reps_objetivo', e.target.value)} />
      </div>
      <input style={inputSx} placeholder="Notas (opcional)" value={fila.notas} onChange={e => set('notas', e.target.value)} />
    </div>
  )
}

function EjercicioPlan({ ej }) {
  const u = ej.ultima_vez
  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 6 }}>
            <span className="num" style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>{ej.orden}.</span>
            <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{ej.ejercicio}</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
            <GrupoBadge grupo={ej.grupo_muscular} />
            {ej.notas && <span className="label" style={{ color: 'var(--text-dim)' }}>{ej.notas}</span>}
          </div>
        </div>
        <div className="num" style={{ textAlign: 'right', flexShrink: 0, fontSize: '0.85rem' }}>
          <div style={{ color: 'var(--text-dim)', fontSize: '0.72rem', marginBottom: 2 }}>OBJETIVO</div>
          <div style={{ color: 'var(--text)' }}>
            {ej.series_objetivo || '—'} × {ej.reps_objetivo || '—'}
          </div>
        </div>
      </div>

      <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
        <div className="label" style={{ color: 'var(--text-dim)', fontSize: '0.72rem', marginBottom: 4 }}>
          ÚLTIMA VEZ
        </div>
        {u ? (
          <div className="num" style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <span>{u.series} × {u.reps_realizadas}{u.peso_kg > 0 ? ` @ ${u.peso_kg} kg` : ''}{(u.rir !== null && u.rir !== undefined) ? ` · RIR ${u.rir}` : ''}</span>
            <span style={{ color: 'var(--text-dim)' }}>{u.fecha}</span>
          </div>
        ) : (
          <div className="num" style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>Sin registros todavía</div>
        )}
      </div>
    </Card>
  )
}

function DiaSeccion({ diaKey, label, ejercicios, onGuardado }) {
  const [editando, setEditando] = useState(false)
  const [filas, setFilas] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const empezarEdicion = () => {
    setFilas(ejercicios.length
      ? ejercicios.map(ej => ({
          ejercicio: ej.ejercicio,
          grupo_muscular: ej.grupo_muscular || '',
          series_objetivo: ej.series_objetivo ?? '',
          reps_objetivo: ej.reps_objetivo || '',
          notas: ej.notas || '',
        }))
      : [filaVacia()])
    setError(null)
    setEditando(true)
  }

  const guardar = async () => {
    setSaving(true)
    setError(null)
    try {
      const limpio = filas
        .filter(f => f.ejercicio.trim())
        .map(f => ({
          ejercicio: f.ejercicio.trim(),
          grupo_muscular: f.grupo_muscular.trim() || null,
          series_objetivo: f.series_objetivo === '' ? null : Number(f.series_objetivo),
          reps_objetivo: f.reps_objetivo.trim() || null,
          notas: f.notas.trim() || null,
        }))
      await postRutinaPlanDia(diaKey, limpio)
      setEditando(false)
      await onGuardado()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <h2 style={{ fontSize: '1rem', margin: 0, color: 'var(--text)' }}>{label}</h2>
        {!editando && (
          <button onClick={empezarEdicion} style={btnSx()}>
            {ejercicios.length ? 'Editar' : 'Añadir'}
          </button>
        )}
      </div>

      {editando ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filas.map((fila, i) => (
            <FilaEditable
              key={i}
              fila={fila}
              onChange={nueva => setFilas(prev => prev.map((f, j) => j === i ? nueva : f))}
              onQuitar={() => setFilas(prev => prev.filter((_, j) => j !== i))}
            />
          ))}
          <button onClick={() => setFilas(prev => [...prev, filaVacia()])} style={btnSx()}>+ Añadir ejercicio</button>
          {error && <p style={{ color: 'var(--data-bad)', fontSize: '0.82rem', margin: 0 }}>{error}</p>}
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={guardar} disabled={saving} style={btnSx('primary')}>
              {saving ? 'Guardando...' : 'Guardar día'}
            </button>
            <button onClick={() => setEditando(false)} disabled={saving} style={btnSx()}>Cancelar</button>
          </div>
        </div>
      ) : ejercicios.length ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {ejercicios.map(ej => <EjercicioPlan key={ej.orden} ej={ej} />)}
        </div>
      ) : (
        <p className="num" style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
          Sin plan para este día.
        </p>
      )}
    </div>
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
      setData(await getRutinaPlan())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const recargarSilencioso = async () => {
    try {
      setData(await getRutinaPlan())
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => { cargar() }, [])

  if (loading) return <Loading text="Cargando rutina..." />
  if (error) return <ErrorState error={error} retry={cargar} />

  const dias = data?.dias || {}

  return (
    <div style={{ padding: '20px 16px', maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.2rem', margin: '0 0 4px', color: 'var(--text)' }}>
        Rutina semanal
      </h1>
      <p className="num" style={{ color: 'var(--text-dim)', fontSize: '0.82rem', margin: '0 0 20px' }}>
        Objetivo planificado por día, comparado con tu última ejecución registrada.
      </p>

      {DIAS.map(({ key, label }) => (
        <DiaSeccion
          key={key}
          diaKey={key}
          label={label}
          ejercicios={dias[key] || []}
          onGuardado={recargarSilencioso}
        />
      ))}
    </div>
  )
}
