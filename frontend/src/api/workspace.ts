import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(
  params?: {
    search?: string
    page?: number
    page_size?: number
  },
  options?: AxiosRequestConfig,
) {
  return request.get<
    API.Result<{
      assistants: API.Workspace[]
      page: number
      page_size: number
      total: number
    }>
  >('/assistants', {
    params,
    ...options,
  })
}

export function detail(
  params: {
    id: string | number
  },
  options?: AxiosRequestConfig,
) {
  const { id, ..._params } = params

  return request.get<API.Result<API.WorkspaceDetail>>(`/assistants/${id}`, {
    params: _params,
    ...options,
  })
}

export function create(
  params: {
    name: string
    prompt?: string
    description?: string
    mcp_services?: {
      mcp_server_id: string
    }[]
  },
  options?: AxiosRequestConfig,
) {
  return request.post<{}>(`/assistants`, params, options)
}

export function update(
  params: API.WorkspaceDetail,
  options?: AxiosRequestConfig,
) {
  const { assistant_id, ..._params } = params

  return request.put<{}>(`/assistants/${assistant_id}`, _params, options)
}
