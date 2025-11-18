import * as api from '@/api'
import IconQuestion from '@/assets/chat/question.svg'
import ComSender from '@/components/sender'
import { useQuery } from '@/router/hook'
import { setPageTransport } from '@/utils'
import { useRequest } from 'ahooks'
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import News from './component/news'
import styles from './new.module.scss'
import { transportToChatEnter } from './shared'

export default function NewChat() {
  const query = useQuery()
  const navigate = useNavigate()

  const { data: assistant } = useRequest(async () => {
    const { data } = await api.workspace.detail({
      id: query.get('assistant_id')!,
    })
    return data
  })

  // 问题推荐
  const questions = useMemo(
    () => [
      '介绍一下智慧交通专项',
      '春运人员流动量',
      '《安全生产责任保险实施办法》',
    ],
    [],
  )

  async function send(message: string) {
    const { data } = await api.session.create({
      assistant_id: query.get('assistant_id')!,
      // title: assistant?.name,
    })

    setPageTransport(transportToChatEnter, {
      data: {
        message,
      },
    })
    navigate(`/chat/${data.session_id}`)
  }

  return (
    <div className={styles['newchat-page']}>
      <div className={styles['newchat-page__header']}>{assistant?.name}</div>

      <ComSender className={styles['newchat-page__sender']} onSend={send} />

      <div className={styles['newchat-page__recommend']}>
        <div className={styles['newchat-page__recommend-title']}>
          <div className={styles['icon']}>
            <img src={IconQuestion} />
          </div>
          问题推荐
        </div>

        <div className={styles['newchat-page__questions']}>
          {questions.map((question) => (
            <div
              className={styles['newchat-page__question']}
              key={question}
              onClick={() => send(question)}
            >
              {question}
            </div>
          ))}
        </div>
      </div>

      <div className={styles['newchat-page__news']}>
        <News />
      </div>
    </div>
  )
}
