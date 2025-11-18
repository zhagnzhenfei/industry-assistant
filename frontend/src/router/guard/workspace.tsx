import { Navigate, useLocation } from 'react-router-dom'

export function WorkspaceGuard({ children }: { children?: React.ReactNode }) {
  const location = useLocation()

  if (location.pathname === '/chat') {
    const query = new URLSearchParams(location.search)
    const assistant_id = query.get('assistant_id')
    if (!assistant_id) {
      window.$app.message.error('请先选择工作空间')
      return <Navigate to="/" />
    }
  }

  return children
}
