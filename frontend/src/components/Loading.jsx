function Bar({ width, delay }) {
  return (
    <div
      className="pulse"
      style={{
        height: 8,
        width,
        borderRadius: 'var(--r-sm)',
        background: 'var(--bg-card-raised)',
        animationDelay: delay,
      }}
    />
  )
}

export default function Loading({ text = 'Cargando' }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      padding: '40px 20px',
      alignItems: 'center',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%', maxWidth: 220 }}>
        <Bar width="100%" delay="0ms" />
        <Bar width="70%" delay="120ms" />
        <Bar width="85%" delay="240ms" />
      </div>
      {text && (
        <span className="label" style={{ marginTop: 8 }}>{text}</span>
      )}
    </div>
  )
}
