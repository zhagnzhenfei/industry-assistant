import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(
  params?: {
    page: number
  },
  options?: AxiosRequestConfig,
) {
  return request.get<
    API.Result<{
      documents: API.Repository[]
      page: number
      page_size: number
      total: number
    }>
  >('/documents/list', {
    ...options,
    params,
  })
}

export function upload(params: { file: File }, options?: AxiosRequestConfig) {
  const form = new FormData()
  form.append('file', params.file)
  return request.post<API.Result<{ file_id: string }>>(
    `/documents/upload`,
    form,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      ...options,
    },
  )
}

export function remove(
  params: { document_id: string },
  options?: AxiosRequestConfig,
) {
  const { document_id, ..._params } = params
  return request.post(
    `/documents/delete`,
    {
      ..._params,
      document_ids: [document_id],
    },
    options,
  )
}
