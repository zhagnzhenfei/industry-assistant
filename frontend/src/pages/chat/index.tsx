import * as api from '@/api'
import ComPageLayout from '@/components/page-layout'
import ComSender from '@/components/sender'
import { ChatRole, ChatType } from '@/configs'
import { deviceActions, deviceState } from '@/store/device'
import { usePageTransport } from '@/utils'
import { useMount, useUnmount } from 'ahooks'
import { uniqueId } from 'lodash-es'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { proxy, useSnapshot } from 'valtio'
import ChatMessage from './component/chat-message'
import Drawer from './component/drawer'
import Source from './component/source'
import styles from './index.module.scss'
import { createChatId, createChatIdText, transportToChatEnter } from './shared'

async function scrollToBottom() {
  await new Promise((resolve) => setTimeout(resolve))

  const threshold = 200
  const distanceToBottom =
    document.documentElement.scrollHeight -
    document.documentElement.scrollTop -
    document.documentElement.clientHeight

  if (distanceToBottom <= threshold) {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: 'smooth',
    })
  }
}

export default function Index() {
  const { id } = useParams()
  const { data: ctx } = usePageTransport(transportToChatEnter)

  const [currentChatItem, setCurrentChatItem] = useState<API.ChatItem | null>(
    null,
  )

  const [chat] = useState(() => {
    return proxy({
      list: [] as API.ChatItem[],
    })
  })
  const { list } = useSnapshot(chat) as {
    list: API.ChatItem[]
  }

  const loading = useMemo(() => {
    return list.some((o) => o.loading)
  }, [list])
  const loadingRef = useRef(loading)
  loadingRef.current = loading
  useEffect(() => {
    deviceActions.setChatting(loading)
  }, [loading])
  useUnmount(() => {
    deviceActions.setChatting(false)
  })

  const sendChat = useCallback(
    async (target: API.ChatItem, message: string) => {
      setCurrentChatItem(target)
      target.loading = true
      try {
        const res =
          target.type === ChatType.Deepsearch
            ? await api.session.deepsearch({
                query: message,
              })
            : await api.session.chat({
                session_id: id!,
                question: message,
              })

        const reader = res.data.getReader()
        if (!reader) return

        await read(reader)
      } catch (error) {
        throw error
      } finally {
        target.loading = false
      }

      async function read(reader: ReadableStreamDefaultReader<any>) {
        let temp = ''
        const decoder = new TextDecoder('utf-8')
        while (true) {
          const { value, done } = await reader.read()
          temp += decoder.decode(value)

          while (true) {
            const index = temp.indexOf('\n')
            if (index === -1) break

            const slice = temp.slice(0, index)
            temp = temp.slice(index + 1)

            if (slice.startsWith('data: ')) {
              parseData(slice)
              scrollToBottom()
            }
          }

          if (done) {
            console.debug('数据接受完毕', temp)
            target.loading = false
            break
          }
        }
      }

      function parseData(slice: string) {
        try {
          const str = slice
            .trim()
            .replace(/^data\: /, '')
            .trim()
          if (str === '[DONE]') {
            return
          }

          const json = JSON.parse(str)
          if (target.type === ChatType.Deepsearch) {
            if (['status', 'search_results'].includes(json.type)) {
              if (!target.thinks) {
                target.thinks = []
              }

              const lastThink = target.thinks[target.thinks.length - 1]

              if (lastThink?.type === json.type) {
                lastThink.results!.push({
                  id: uniqueId('think_result'),
                  content: json.subquery || json.content,
                  count: json.count,
                })
              } else {
                target.thinks.push({
                  id: uniqueId('think_result'),
                  type: json.type,
                  results: [
                    {
                      id: uniqueId('think_result'),
                      content: json.subquery || json.content,
                      count: json.count,
                    },
                  ],
                })
              }
            } else if (json.type === 'search_result_item') {
              if (!target.search_results) {
                target.search_results = []
              }

              target.search_results.push({
                ...json.result,
                id: uniqueId('search-results'),
                host: new URL(json.result.url).host,
              })
            } else if (json.type === 'thinking') {
              target.think = `${target.think || ''}${json.content || ''}`
            } else if (['answer', 'final_answer'].includes(json.type)) {
              target.content = `${target.content}${json.content || ''}`
            } else if (json.type === 'reference_materials') {
              target.reference = json.content?.map((o: any) => ({
                id: o.reference_id,
                title: o.name,
                link: o.url,
                content: o.summary,
                source: 'web',
              }))
            }
          } else {
            switch (json?.type) {
              case 'start':
              case 'llm_start':
              case 'llm_response':
              case 'tool_calls_detected':
              case 'tool_execution_start':
              case 'llm_final_start':
                if (json?.message) {
                  target.think = `${target.think || ''}\n${json.message || ''}`
                }
                break
              case 'assistant_content_chunk':
                if (json?.content) {
                  target.content = `${target.content || ''}${json.content || ''}`
                }
                break
              case 'assistant_message':
                if (json?.content) {
                  target.content = `${target.content || ''}\n\n${json.content || ''}\n\n`
                }
                break
            }
          }
        } catch {
          console.debug('解析失败')
          console.debug(slice)
        }
      }
    },
    [chat],
  )

  const send = useCallback(
    async (message: string) => {
      if (loadingRef.current) return
      if (!message) return

      chat.list.push({
        id: createChatId(),
        role: ChatRole.User,
        type: ChatType.Normal,
        content: message,
      })

      chat.list.push({
        id: createChatId(),
        role: ChatRole.Assistant,
        type: deviceState.useDeepsearch ? ChatType.Deepsearch : ChatType.Normal,
        content: '',
      })
      scrollToBottom()

      const target = chat.list[chat.list.length - 1]

      await sendChat(target, message!)
    },
    [chat, sendChat],
  )
  useMount(async () => {
    if (ctx?.data.message) {
      send(ctx.data.message)
    }
  })

  useEffect(() => {
    const handleScroll = () => {
      const anchors: {
        id: string
        top: number
        item: API.ChatItem
      }[] = []

      chat.list
        .filter((o) => o.type === ChatType.Deepsearch)
        .forEach((item, index) => {
          const id = createChatIdText(item.id)
          const dom = document.getElementById(id)
          if (!dom) return

          const top = dom.offsetTop
          if (index === 0 || top < window.scrollY) {
            anchors.push({ id, top, item })
          }
        })

      if (anchors.length) {
        const current = anchors.reduce((prev, curr) =>
          curr.top > prev.top ? curr : prev,
        )

        setCurrentChatItem(current.item)
      }
    }

    window.addEventListener('scroll', handleScroll)

    return () => {
      window.removeEventListener('scroll', handleScroll)
    }
  }, [])

  return (
    <ComPageLayout
      sender={
        <>
          <ComSender loading={loading} onSend={send} />
        </>
      }
      right={
        currentChatItem?.search_results?.length ? (
          <Drawer title="搜索来源">
            <Source list={currentChatItem.search_results} />
          </Drawer>
        ) : null
      }
    >
      <div className={styles['chat-page']}>
        <ChatMessage list={list} onSend={send} />
      </div>
    </ComPageLayout>
  )
}
