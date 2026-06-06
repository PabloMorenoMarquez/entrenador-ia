import { Routes, Route, Navigate } from 'react-router-dom'
import BottomNav from './components/BottomNav'
import Dashboard from './views/Dashboard'
import Rutina from './views/Rutina'
import Nutricion from './views/Nutricion'
import Historial from './views/Historial'
import Perfil from './views/Perfil'
import Chat from './views/Chat'
import Checkin from './views/Checkin'

export default function App() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--bg)',
    }}>
      <main style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/rutina" element={<Rutina />} />
          <Route path="/nutricion" element={<Nutricion />} />
          <Route path="/historial" element={<Historial />} />
          <Route path="/perfil" element={<Perfil />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/checkin" element={<Checkin />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </main>
      <BottomNav />
    </div>
  )
}
