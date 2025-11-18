import { BaseLayout } from '@/layout/base'
import NotFound from '@/pages/404'
import Chat from '@/pages/chat'
import NewChat from '@/pages/chat/newchat'
import Index from '@/pages/index'
import Login from '@/pages/login'
import Repository from '@/pages/repository'
import Workspace from '@/pages/workspace'
import WorkspaceDetail from '@/pages/workspace/detail'
import {
  Navigate,
  Outlet,
  RouteObject,
  createBrowserRouter,
} from 'react-router-dom'
import { RouterGuard } from './guard'

export type IRouteObject = {
  children?: IRouteObject[]
  name?: string
  auth?: boolean
  pure?: boolean
  meta?: any
} & Omit<RouteObject, 'children'>

export const routes: IRouteObject[] = [
  {
    path: '/',
    Component: Index,
  },
  {
    path: '/chat',
    children: [
      {
        path: '',
        Component: NewChat,
      },
      {
        path: ':id',
        Component: Chat,
      },
    ],
  },
  {
    path: '/workspace',
    children: [
      {
        path: '',
        Component: Workspace,
      },
      {
        path: ':id',
        Component: WorkspaceDetail,
      },
    ],
  },
  {
    path: '/repository',
    Component: Repository,
  },
  {
    path: '/404',
    Component: NotFound,
    pure: true,
  },
]

export const router = createBrowserRouter(
  [
    helper({
      path: '/',
      element: (
        <BaseLayout>
          <RouterGuard>
            <Outlet />
          </RouterGuard>
        </BaseLayout>
      ),
      children: routes,
    }),
    helper({
      path: '/login',
      Component: Login,
      auth: false,
    }),
    helper({
      path: '*',
      element: <Navigate to="/404" />,
      pure: true,
    }),
  ] as RouteObject[],
  {
    basename: import.meta.env.BASE_URL,
  },
)

function helper(route: IRouteObject) {
  const _route = {
    ...route,
  }

  if (_route.children) {
    _route.children = _route.children.map((child: any) => helper(child))
  }

  if (_route.auth === undefined) {
    _route.auth = true
  }

  return _route as RouteObject
}
