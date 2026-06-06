import { NavLink } from 'react-router-dom'

const tabs = [
  { to: '/dashboard', label: 'Inicio', icon: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
      <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>
  )},
  { to: '/rutina', label: 'Rutina', icon: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 4v16M18 4v16M3 8h18M3 16h18"/>
    </svg>
  )},
  { to: '/nutricion', label: 'Nutrición', icon: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2z"/>
      <path d="M12 6v6l4 2"/>
    </svg>
  )},
  { to: '/chat', label: 'Chat', icon: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  )},
  { to: '/perfil', label: 'Perfil', icon: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  )},
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
      {tabs.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          style={({ isActive }) => ({
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 3,
            paddingTop: 10,
            paddingBottom: 10,
            flex: 1,
            textDecoration: 'none',
            color: isActive ? 'var(--accent)' : 'var(--text-dim)',
            fontSize: '0.68rem',
            fontWeight: isActive ? 600 : 500,
            letterSpacing: '0.02em',
            transition: 'color 0.15s',
            borderTop: isActive ? '2px solid var(--accent)' : '2px solid transparent',
            cursor: 'pointer',
            minHeight: 52,
          })}
        >
          {icon}
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
