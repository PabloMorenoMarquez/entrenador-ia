export default function ErrorState({ error, retry }) {
  return (
    <div style={{
      padding: '40px 20px',
      textAlign: 'center',
      color: 'var(--text-muted)',
    }}>
      <p style={{ marginBottom: 16, color: '#f87171', fontSize: '0.9rem' }}>{error}</p>
      {retry && (
        <button
          onClick={retry}
          style={{
            background: 'var(--accent)',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            padding: '8px 20px',
            cursor: 'pointer',
            fontSize: '0.9rem',
          }}
        >
          Reintentar
        </button>
      )}
    </div>
  )
}
