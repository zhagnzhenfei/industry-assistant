import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(params?: {}, options?: AxiosRequestConfig) {
  return request.get<
    API.Result<{
      servers: API.Mcp[]
    }>
  >('/mcp/servers', {
    params,
    ...options,
  })
}
