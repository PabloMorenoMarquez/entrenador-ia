export default function Card({ children, style = {}, className = '' }) {
  return (
    <div
      className={`card ${className}`}
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: '16px',
        ...style,
      }}
    >
      {children}
    </div>
  )
}
