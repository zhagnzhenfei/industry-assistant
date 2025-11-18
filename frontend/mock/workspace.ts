import { MockMethod } from 'vite-plugin-mock'

export default [
  {
    url: '/api/workspace',
    method: 'get',
    timeout: 500,
    statusCode: 200,
    response: {
      status: 'success',
      message: 'Session created successfully',
      data: [
        {
          id: 1,
          title: '安责行业助手',
          description: '安责行业助手安,责行业助手',
          color: '#543D21',
        },
        {
          id: 2,
          title: '餐饮行业助手',
          description: '安责行业助手安,责行业助手',
          color: '#335519',
        },
        {
          id: 3,
          title: '交通运输行业助手',
          description: '安责行业助手安,责行业助手',
          color: '#055588',
        },
        {
          id: 4,
          title: '交通运输行业助手',
          description: '安责行业助手安,责行业助手',
          color: '#1144BA',
        },
      ],
    },
  },
  {
    url: '/api/workspace/:id',
    method: 'get',
    timeout: 500,
    statusCode: 200,
    response: {
      status: 'success',
      message: 'Session created successfully',
      data: {
        id: 1,
        title: '安责行业助手',
        description: '安责行业助手安,责行业助手',
        color: '#543D21',
      },
    },
  },
] as MockMethod[]
