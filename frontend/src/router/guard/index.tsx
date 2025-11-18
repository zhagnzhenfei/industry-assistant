import { AuthGuard } from './auth'
import { WorkspaceGuard } from './workspace'

export function RouterGuard({ children }: { children?: React.ReactNode }) {
  return (
    <AuthGuard>
      <WorkspaceGuard>{children}</WorkspaceGuard>
    </AuthGuard>
  )
}
