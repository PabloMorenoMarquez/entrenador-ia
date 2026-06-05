import { useState, useRef, useEffect } from 'react'
import { postChat } from '../api/client'
import Markdown from '../components/Markdown'

function TypingDots() {
  const dotStyle = (delay) => ({
    display: 'inline-block',
    width: 6,
    height: 6,
    borderRadius: '50%',
    background: 'var(--text-dim)',
    animation: 'dotBounce 1.3s infinite',
    animationDelay: delay,
    margin: '0 2px',
  })
  return (
    <div style={{ padding: '4px 0' }}>
      <span style={dotStyle('0ms')} />
      <span style={dotStyle('180ms')} />
      <span style={dotStyle('360ms')} />
    </div>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className="fade-up" style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-end',
      gap: 8,
      marginBottom: 16,
    }}>
      {!isUser && (
        <div style={{
          width: 30, height: 30, borderRadius: 6, flexShrink: 0,
          background: 'var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-soft)',
        }}>C</div>
      )}
      <div style={{
        maxWidth: '82%',
        background: isUser ? 'var(--accent)' : 'var(--bg-card)',
        border: isUser ? 'none' : '1px solid var(--border)',
        borderRadius: isUser ? '14px 14px 3px 14px' : '14px 14px 14px 3px',
        padding: '10px 14px',
        fontSize: '0.89rem',
        color: isUser ? '#fff' : 'var(--text-muted)',
        lineHeight: 1.55,
      }}>
        {msg.typing ? <TypingDots /> : (
          isUser ? <span>{msg.content}</span> : <Markdown>{msg.content}</Markdown>
        )}
      </div>
    </div>
  )
}

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const autoResize = () => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 130) + 'px'
  }

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    const userMsg = { role: 'user', content: text, id: Date.now() }
    const typingMsg = { role: 'assistant', content: '', typing: true, id: Date.now() + 1 }
    setMessages(prev => [...prev, userMsg, typingMsg])
    setLoading(true)

    try {
      const res = await postChat(text)
      setMessages(prev => [
        ...prev.filter(m => !m.typing),
        { role: 'assistant', content: res.respuesta, id: Date.now() + 2 },
      ])
    } catch (e) {
      setMessages(prev => [
        ...prev.filter(m => !m.typing),
        { role: 'assistant', content: `Error: ${e.message}`, id: Date.now() + 2 },
      ])
    } finally {
      setLoading(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    }}>
      {/* Header */}
      <div style={{
        background: 'var(--bg-header)',
        borderBottom: '1px solid var(--border)',
        padding: '14px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        flexShrink: 0,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: 'var(--accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L8 7H4l3 5-3 5h4l4 5 4-5h4l-3-5 3-5h-4z"/>
          </svg>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: '0.93rem' }}>Coach IA</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.74rem', color: 'var(--text-dim)' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', display: 'inline-block' }} />
            En línea
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px 16px',
        maxWidth: 760,
        width: '100%',
        margin: '0 auto',
        boxSizing: 'border-box',
      }}>
        {messages.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '60px 20px',
            color: 'var(--text-dim)',
            fontSize: '0.9rem',
          }}>
            <div style={{ fontSize: '2rem', marginBottom: 12 }}>💪</div>
            <div>Cuéntale al coach cómo ha ido el entreno,</div>
            <div>lo que has comido, o haz cualquier pregunta.</div>
          </div>
        )}
        {messages.map(msg => <Message key={msg.id} msg={msg} />)}
        <div ref={bottomRef} />
      </div>

      {/* Input form */}
      <div style={{
        background: 'var(--bg-header)',
        borderTop: '1px solid var(--border)',
        padding: '12px 16px',
        paddingBottom: 'calc(12px + env(safe-area-inset-bottom, 0px))',
        display: 'flex',
        gap: 10,
        alignItems: 'flex-end',
        flexShrink: 0,
        maxWidth: 760,
        width: '100%',
        margin: '0 auto',
        boxSizing: 'border-box',
      }}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => { setInput(e.target.value); autoResize() }}
          onKeyDown={onKeyDown}
          placeholder="Escribe un mensaje..."
          rows={1}
          disabled={loading}
          style={{
            flex: 1,
            resize: 'none',
            padding: '10px 14px',
            borderRadius: 12,
            fontSize: 16,
            lineHeight: 1.4,
            maxHeight: 130,
            overflowY: 'auto',
            border: '1px solid var(--border)',
            background: 'var(--bg-card)',
            color: 'var(--text)',
            outline: 'none',
          }}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            width: 46, height: 46,
            borderRadius: 12,
            background: loading || !input.trim() ? 'var(--border)' : 'var(--accent)',
            border: 'none',
            cursor: loading || !input.trim() ? 'default' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
            transition: 'background 0.15s',
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  )
}
