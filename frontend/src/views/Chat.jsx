import { useState, useRef, useEffect } from 'react'
import { postChat, getChatHistorial, getConversaciones } from '../api/client'
import Markdown from '../components/Markdown'

const CHAT_ID_KEY = 'entrenador_chat_id_activo'

function nuevoChatId() {
  const id = (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`)
  localStorage.setItem(CHAT_ID_KEY, id)
  return id
}

function chatIdActivo() {
  return localStorage.getItem(CHAT_ID_KEY) || nuevoChatId()
}

function formatearFecha(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const hoy = new Date()
  const mismodia = d.toDateString() === hoy.toDateString()
  return mismodia
    ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString([], { day: '2-digit', month: '2-digit' })
}

function TypingDots() {
  const dotStyle = (delay) => ({
    display: 'inline-block',
    width: 6,
    height: 6,
    borderRadius: '50%',
    background: 'var(--text-dim)',
    animation: 'pulse 1.2s ease-in-out infinite',
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
        <div className="num" style={{
          width: 28, height: 28, borderRadius: 'var(--r-sm)', flexShrink: 0,
          background: 'var(--bg-card-raised)',
          border: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '0.72rem', fontWeight: 600, color: 'var(--accent)',
        }}>C</div>
      )}
      <div style={{
        maxWidth: '82%',
        background: isUser ? 'var(--bg-card-raised)' : 'var(--bg-card)',
        border: '1px solid ' + (isUser ? 'var(--border-strong)' : 'var(--border)'),
        borderRadius: isUser ? '6px 6px 2px 6px' : '6px 6px 6px 2px',
        padding: '10px 14px',
        fontSize: '0.89rem',
        color: 'var(--text-muted)',
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
  const [chatId, setChatId] = useState(() => chatIdActivo())
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [cargandoHistorial, setCargandoHistorial] = useState(true)
  const [conversaciones, setConversaciones] = useState([])
  const [panelAbierto, setPanelAbierto] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  const cargarHistorial = (id) => {
    setCargandoHistorial(true)
    let cancelado = false
    getChatHistorial(30, id)
      .then(historial => {
        if (cancelado || !Array.isArray(historial)) return
        setMessages(historial.map((m, i) => ({
          role: m.rol === 'assistant' ? 'assistant' : 'user',
          content: m.contenido,
          id: `hist-${i}`,
        })))
      })
      .catch(() => {})
      .finally(() => { if (!cancelado) setCargandoHistorial(false) })
    return () => { cancelado = true }
  }

  useEffect(() => cargarHistorial(chatId), [chatId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: cargandoHistorial ? 'auto' : 'smooth' })
  }, [messages, cargandoHistorial])

  const cargarConversaciones = () => {
    getConversaciones()
      .then(lista => { if (Array.isArray(lista)) setConversaciones(lista) })
      .catch(() => {})
  }

  const abrirPanel = () => {
    setPanelAbierto(true)
    cargarConversaciones()
  }

  const iniciarNuevaConversacion = () => {
    if (loading) return
    const id = nuevoChatId()
    setChatId(id)
    setMessages([])
    setPanelAbierto(false)
  }

  const cambiarConversacion = (id) => {
    if (id === chatId) { setPanelAbierto(false); return }
    localStorage.setItem(CHAT_ID_KEY, id)
    setChatId(id)
    setPanelAbierto(false)
  }

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
      const res = await postChat(text, chatId)
      if (res.chat_id && res.chat_id !== chatId) {
        localStorage.setItem(CHAT_ID_KEY, res.chat_id)
        setChatId(res.chat_id)
      }
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
          width: 32, height: 32, borderRadius: 'var(--r-sm)',
          border: '1px solid var(--border-strong)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: '0.93rem' }}>Coach IA</div>
          <div className="label" style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--data-good)', display: 'inline-block' }} />
            En línea
          </div>
        </div>
        <button
          onClick={iniciarNuevaConversacion}
          title="Nueva conversación"
          style={{
            border: '1px solid var(--border-strong)',
            background: 'transparent',
            color: 'var(--text-muted)',
            borderRadius: 'var(--r-sm)',
            padding: '6px 10px',
            fontSize: '0.78rem',
            cursor: 'pointer',
          }}
        >
          + Nueva
        </button>
        <button
          onClick={abrirPanel}
          title="Conversaciones"
          style={{
            width: 32, height: 32, borderRadius: 'var(--r-sm)',
            border: '1px solid var(--border-strong)',
            background: 'transparent',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
      </div>

      {/* Panel de conversaciones */}
      {panelAbierto && (
        <div
          onClick={() => setPanelAbierto(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 50,
            display: 'flex', justifyContent: 'flex-end',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 'min(320px, 86vw)', height: '100%',
              background: 'var(--bg-card)', borderLeft: '1px solid var(--border)',
              display: 'flex', flexDirection: 'column', overflow: 'hidden',
            }}
          >
            <div style={{
              padding: '14px 16px', borderBottom: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Conversaciones</div>
              <button
                onClick={iniciarNuevaConversacion}
                style={{
                  border: '1px solid var(--border-strong)', background: 'transparent',
                  color: 'var(--accent)', borderRadius: 'var(--r-sm)',
                  padding: '5px 10px', fontSize: '0.76rem', cursor: 'pointer',
                }}
              >
                + Nueva
              </button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
              {conversaciones.length === 0 && (
                <div style={{ padding: '20px 12px', color: 'var(--text-dim)', fontSize: '0.82rem', textAlign: 'center' }}>
                  Sin conversaciones guardadas
                </div>
              )}
              {conversaciones.map(c => (
                <div
                  key={c.chat_id}
                  onClick={() => cambiarConversacion(c.chat_id)}
                  style={{
                    padding: '10px 12px',
                    marginBottom: 4,
                    borderRadius: 'var(--r-sm)',
                    border: '1px solid ' + (c.chat_id === chatId ? 'var(--border-strong)' : 'transparent'),
                    background: c.chat_id === chatId ? 'var(--bg-card-raised)' : 'transparent',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{
                    fontSize: '0.84rem', color: 'var(--text-muted)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {c.preview || '(sin mensajes)'}
                  </div>
                  <div className="label" style={{ marginTop: 3 }}>
                    {formatearFecha(c.ultima_fecha)} · {c.num_mensajes} mensaje{c.num_mensajes === 1 ? '' : 's'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

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
            <div className="label" style={{ marginBottom: 10 }}>Sin mensajes</div>
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
            borderRadius: 'var(--r-lg)',
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
            borderRadius: 'var(--r-lg)',
            background: loading || !input.trim() ? 'var(--border)' : 'var(--accent)',
            border: 'none',
            cursor: loading || !input.trim() ? 'default' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
            transition: 'background var(--t-base)',
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--bg)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  )
}
