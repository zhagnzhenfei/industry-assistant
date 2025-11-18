import { MockMethod } from 'vite-plugin-mock'

export default [
  {
    url: '/api/repository',
    method: 'get',
    timeout: 500,
    statusCode: 200,
    response: {
      status: 'success',
      message: 'Session created successfully',
      data: [
        {
          id: 1,
          file_name: '文件.pdf',
          created_at: '2025-08-19 16:29:10',
          updated_at: '2025-08-19 16:29:10',
        },
        {
          id: 2,
          file_name: '文件.pdf',
          created_at: '2025-08-19 16:29:10',
          updated_at: '2025-08-19 16:29:10',
        },
        {
          id: 3,
          file_name: '文件.pdf',
          created_at: '2025-08-19 16:29:10',
          updated_at: '2025-08-19 16:29:10',
        },
      ],
    },
  },
] as MockMethod[]
