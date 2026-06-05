import ReactMarkdown from 'react-markdown'

const inlineCodeStyle = {
  background: 'rgba(129,140,248,0.15)',
  color: 'var(--accent-soft)',
  borderRadius: 4,
  padding: '1px 5px',
  fontSize: '0.85em',
  fontFamily: 'Menlo, Consolas, monospace',
}

const blockCodeStyle = {
  background: 'rgba(15,15,30,0.8)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  padding: '10px 14px',
  overflowX: 'auto',
  margin: '6px 0',
}

export default function Markdown({ children }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p style={{ margin: '0 0 8px', lineHeight: 1.6 }}>{children}</p>,
        strong: ({ children }) => <strong style={{ color: 'var(--text)', fontWeight: 600 }}>{children}</strong>,
        ul: ({ children }) => <ul style={{ margin: '4px 0 8px', paddingLeft: 20 }}>{children}</ul>,
        ol: ({ children }) => <ol style={{ margin: '4px 0 8px', paddingLeft: 20 }}>{children}</ol>,
        li: ({ children }) => <li style={{ margin: '2px 0', lineHeight: 1.5 }}>{children}</li>,
        h1: ({ children }) => <h1 style={{ fontSize: '1.1rem', fontWeight: 600, margin: '8px 0 4px', color: 'var(--text)' }}>{children}</h1>,
        h2: ({ children }) => <h2 style={{ fontSize: '1rem', fontWeight: 600, margin: '8px 0 4px', color: 'var(--text)' }}>{children}</h2>,
        h3: ({ children }) => <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: '6px 0 3px', color: 'var(--text)' }}>{children}</h3>,
        // v10: use `pre` for block code, `code` only for inline
        pre: ({ children }) => <pre style={blockCodeStyle}>{children}</pre>,
        code: ({ children }) => <code style={inlineCodeStyle}>{children}</code>,
        blockquote: ({ children }) => <blockquote style={{ borderLeft: '3px solid var(--accent)', margin: '6px 0', paddingLeft: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>{children}</blockquote>,
      }}
    >
      {children}
    </ReactMarkdown>
  )
}
