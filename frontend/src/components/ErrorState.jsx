export default function ErrorState({ error, retry }) {
  return (
    <div style={{
      padding: '40px 20px',
      textAlign: 'center',
      color: 'var(--text-muted)',
    }}>
      <p style={{ marginBottom: 16, color: 'var(--data-bad)', fontSize: '0.9rem' }}>{error}</p>
      {retry && (
        <button
          onClick={retry}
          style={{
            background: 'transparent',
            color: 'var(--accent)',
            border: '1px solid var(--border-strong)',
            borderRadius: 'var(--r-sm)',
            padding: '8px 20px',
            cursor: 'pointer',
            fontSize: '0.85rem',
            fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            transition: 'border-color var(--t-base), color var(--t-base)',
          }}
        >
          Reintentar
        </button>
      )}
    </div>
  )
}
