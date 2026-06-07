import { NavLink } from 'react-router-dom'
import { Gauge, ClipboardCheck, Dumbbell, Utensils, MessageSquare, User } from 'lucide-react'

const tabs = [
  { to: '/dashboard', label: 'Inicio', Icon: Gauge },
  { to: '/checkin', label: 'Check-in', Icon: ClipboardCheck },
  { to: '/rutina', label: 'Rutina', Icon: Dumbbell },
  { to: '/nutricion', label: 'Nutrición', Icon: Utensils },
  { to: '/chat', label: 'Chat', Icon: MessageSquare },
  { to: '/perfil', label: 'Perfil', Icon: User },
]

export default function BottomNav() {
  return (
    <nav style={{
      background: 'var(--bg-header)',
      borderTop: '1px solid var(--border)',
      display: 'flex',
      justifyContent: 'space-around',
      alignItems: 'stretch',
      paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      flexShrink: 0,
    }}>
      {tabs.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          style={({ isActive }) => ({
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
            paddingTop: 10,
            paddingBottom: 10,
            flex: 1,
            textDecoration: 'none',
            color: isActive ? 'var(--accent)' : 'var(--text-dim)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.62rem',
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            transition: `color ${'var(--t-base)'}`,
            borderTop: isActive ? '1px solid var(--accent)' : '1px solid transparent',
            cursor: 'pointer',
            minHeight: 52,
          })}
        >
          <Icon size={20} strokeWidth={1.5} />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
