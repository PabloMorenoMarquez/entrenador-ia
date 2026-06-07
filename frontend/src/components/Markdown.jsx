import ReactMarkdown from 'react-markdown'

const inlineCodeStyle = {
  background: 'var(--bg-card-raised)',
  color: 'var(--accent)',
  borderRadius: 'var(--r-sm)',
  padding: '1px 5px',
  fontSize: '0.85em',
  fontFamily: 'var(--font-mono)',
}

const blockCodeStyle = {
  background: 'var(--bg-card-raised)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-md)',
  padding: '10px 14px',
  overflowX: 'auto',
  margin: '6px 0',
  fontFamily: 'var(--font-mono)',
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
        blockquote: ({ children }) => <blockquote style={{ borderLeft: '2px solid var(--accent-dim)', margin: '6px 0', paddingLeft: 12, color: 'var(--text-muted)' }}>{children}</blockquote>,
      }}
    >
      {children}
    </ReactMarkdown>
  )
}
