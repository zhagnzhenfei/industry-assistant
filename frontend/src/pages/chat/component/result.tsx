import IconImage from '@/assets/chat/image.svg'
import IconSource from '@/assets/chat/source.svg'
import IconThink from '@/assets/chat/think.svg'
import Markdown from '@/components/markdown'
import host from '@/configs/data/host'
import { CheckOutlined } from '@ant-design/icons'
import classNames from 'classnames'
import { TokenizerAndRendererExtension } from 'marked'
import { useMemo } from 'react'
import styles from './result.module.scss'
import Section from './section'

function findHost(url: string) {
  return host.find((o) => {
    try {
      const _url = new URL(url)
      const hostname = _url.hostname
      if (hostname === o.url) return true
      if (hostname.replace(/^www\./, '') === o.url.replace(/^www\./, ''))
        return true
      if (
        hostname.split('.').length >= 2 &&
        hostname.replace(/^.+?\.(.+)$/, '$1') === o.url.replace(/^www\./, '')
      )
        return true

      return false
    } catch (err) {
      console.error(err)
      return false
    }
  })
}

const 来源 = (props: { item: API.ChatItem }) => {
  const { item } = props

  const source = useMemo(() => {
    return {
      web: item.reference
        ?.filter((item) => item.source === 'web')
        .map((item) => ({
          ...item,
          hostname: findHost(item.link)?.name,
        })),
      knowledge: item.reference
        ?.filter((item) => item.source === 'knowledge')
        .map((item) => ({
          ...item,
          hostname: findHost(item.link)?.name,
        })),
    }
  }, [item])

  return (
    <>
      {source.knowledge?.length ? (
        <Section title="相关知识库来源" icon={IconSource} defaultOpen>
          <div className={styles['chat-message-result__source']}>
            {source.knowledge?.map((item) => (
              <div
                key={item.id}
                className={styles.item}
                onClick={() => window.open(item.link, '_blank')}
              >
                <div className={styles.header}>
                  <div className={styles.id}>[{item.id}]</div>
                  {/* <img className={styles.icon} src={IconShare} /> */}
                  <div className={styles.url}>{item.hostname || item.link}</div>
                </div>
                <div className={styles.title}>{item.title}</div>
                <div className={styles.content}>{item.content}</div>
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      {source.web?.length ? (
        <Section title="相关网络来源" icon={IconSource} defaultOpen>
          <div className={styles['chat-message-result__source']}>
            {source.web?.map((item) => (
              <div
                key={item.id}
                className={styles.item}
                onClick={() => window.open(item.link, '_blank')}
              >
                <div className={styles.header}>
                  <div className={styles.id}>[{item.id}]</div>
                  {/* <img className={styles.icon} src={IconShare} /> */}
                  <div className={styles.url}>{item.hostname || item.link}</div>
                </div>
                <div className={styles.title}>{item.title}</div>
                <div className={styles.content}>{item.content}</div>
              </div>
            ))}
          </div>
        </Section>
      ) : null}
    </>
  )
}

const 图像 = (props: { item: API.ChatItem }) => {
  const { item } = props

  return (
    <Section title="图像" icon={IconImage} defaultOpen>
      <div className={styles['chat-message-result__images']}>
        {item.image_results?.images?.map((item, index) => (
          <div
            className={styles.item}
            key={index}
            onClick={() => window.open(item.link, '_blank')}
          >
            <div className={styles.box}>
              <img className={styles.cover} src={item.thumbnailUrl} />
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

const 思考过程 = (props: { item: API.ChatItem }) => {
  const { item } = props

  return (
    <div className={styles['chat-message-result__thinks']}>
      {item.thinks?.map((o, index) => (
        <div key={o.id} className={styles['chat-message-result__thinks-item']}>
          <div className={styles['header']}>
            <div
              className={classNames(styles['header-icon'], {
                [styles['thinking']]:
                  index === item.thinks!.length - 1 && !item.think,
              })}
            >
              {item.thinks!.length - 1 && !item.think ? (
                <div
                  style={{
                    width: 6,
                    height: 6,
                    backgroundColor: '#fff',
                    borderRadius: 1,
                  }}
                ></div>
              ) : (
                <CheckOutlined />
              )}
            </div>
            {
              {
                status: '思考',
                search_results: '执行',
              }[o.type]
            }
          </div>

          <div className={styles['thinks-results']}>
            {o.results?.map((item) => (
              <div className={styles['thinks-results__item']} key={item.id}>
                <div className={styles.content}>{item.content}</div>
                {/* {item.count ? (
                  <div className={styles.count}>找到{item.count}个来源</div>
                ) : null} */}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export function Result(props: {
  item: API.ChatItem
  isEnd?: boolean
  onSend?: (text: string) => void
}) {
  const { item } = props

  /* markdown */
  const extensions = useMemo<TokenizerAndRendererExtension[]>(
    () => [
      {
        name: 'reference',
        level: 'inline',
        start(src) {
          return src.match(/##\d+\$\$/)?.index
        },
        tokenizer(src) {
          const match = /^##(\d+?)\$\$/.exec(src)
          if (match) {
            const [raw, index] = match
            return {
              type: 'reference',
              raw,
              index: this.lexer.inlineTokens(index),
              tokens: [],
            }
          }
        },
        renderer(token) {
          const index = this.parser.parseInline(token.index)
          const id = Number(index) + 1
          const target = item.reference?.find((item) => item.id === id)
          return `<a class="refrence-token" href="${target?.link || 'javascript: void 0'}" target="${target?.link ? '_blank' : '_self'}">[${Number(index) + 1}]</a>`
        },
      },
    ],
    [item, item.reference],
  )

  return (
    <div className={styles['chat-message-result']}>
      <Section title="智能回答" icon={IconThink} defaultOpen>
        {item.thinks ? <思考过程 item={item} /> : null}

        {item.think ? (
          <Markdown
            className={classNames(
              styles['chat-message-result__think'],
              styles['chat-message-result__md'],
            )}
            value={item.think}
            extensions={extensions}
          />
        ) : null}

        <Markdown
          className={styles['chat-message-result__md']}
          value={item.content}
          extensions={extensions}
        />
      </Section>

      {item.reference?.length && !item.loading ? <来源 item={item} /> : null}

      {item.image_results?.images?.length && !item.loading ? (
        <图像 item={item} />
      ) : null}
    </div>
  )
}
