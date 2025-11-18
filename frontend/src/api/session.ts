import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function create(
  params?: {
    assistant_id: string
    title?: string
  },
  options?: AxiosRequestConfig,
) {
  return request.post<
    API.Result<{
      session_id: string
    }>
  >(`/assistant-chat/sessions`, params, options)
}

export function chat(
  params: {
    session_id: string
    question: string
  },
  options?: AxiosRequestConfig,
) {
  return request.post<ReadableStream>(
    '/assistant-chat/completion/stream',
    {
      session_id: params.session_id,
      message: params.question,
    },
    {
      headers: {
        Accept: 'text/event-stream',
      },
      responseType: 'stream',
      adapter: 'fetch',
      loading: false,
      ...options,
    },
  )
}

export function deepsearch(
  params: {
    query: string
  },
  options?: AxiosRequestConfig,
) {
  return request.post<ReadableStream>('/research/stream', params, {
    headers: {
      Accept: 'text/event-stream',
    },
    responseType: 'stream',
    adapter: 'fetch',
    loading: false,
    ...options,
  })
}
