export default function Card({ children, style = {}, className = '' }) {
  return (
    <div
      className={`card ${className}`}
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-md)',
        padding: 'var(--sp-4)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}
