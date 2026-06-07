export default function Loading({ text = 'Cargando...' }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      padding: '40px 20px',
      color: 'var(--text-dim)',
      fontSize: '0.9rem',
    }}>
      <span style={{ animation: 'pulse 1.2s ease-in-out infinite', animationDelay: '0ms' }}>●</span>
      <span style={{ animation: 'pulse 1.2s ease-in-out infinite', animationDelay: '0.15s' }}>●</span>
      <span style={{ animation: 'pulse 1.2s ease-in-out infinite', animationDelay: '0.3s' }}>●</span>
      {text && <span style={{ marginLeft: 8 }}>{text}</span>}
    </div>
  )
}
