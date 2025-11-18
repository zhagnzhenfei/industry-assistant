import IconFile from '@/assets/component/file.svg'
import IconRecorder from '@/assets/component/recorder.svg'
import IconSend from '@/assets/component/send.svg'
import { deviceActions, deviceState } from '@/store/device'
import { Button, Input, Space, Switch } from 'antd'
import classNames from 'classnames'
import { PropsWithChildren, useState } from 'react'
import { useSnapshot } from 'valtio'
import './index.scss'

export default function ComSender(
  props: PropsWithChildren<{
    className?: string
    loading?: boolean
    onSend?: (value: string) => void | Promise<void>
    onContract?: () => void
  }>,
) {
  const { className, onSend, onContract, loading, ...rest } = props
  const [value, setValue] = useState('')
  const device = useSnapshot(deviceState)

  async function send() {
    if (loading) return
    if (!value) return
    setValue('')
    await onSend?.(value)
  }

  function handlePressEnter(e: any) {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        return
      } else {
        e.preventDefault()
        send()
      }
    }
  }

  return (
    <div className={classNames('com-sender', className)} {...rest}>
      <Input.TextArea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="按 Enter 发送，Shift + Enter 换行"
        autoSize={{ minRows: 2 }}
        autoFocus
        onPressEnter={handlePressEnter}
      />

      <div className="com-sender__actions">
        <Space className="com-sender__actions-left" size={12}>
          <Button variant="text" color="default">
            <img src={IconFile} />
            附件
          </Button>

          <Space>
            <Switch
              value={device.useDeepsearch}
              onChange={(value) => deviceActions.setUseDeepsearch(value)}
            />
            深度探索
          </Space>
        </Space>

        <Space className="com-sender__actions-right" size={12}>
          <Button color="default" variant="text" shape="circle">
            <img src={IconRecorder} />
          </Button>
          <Button
            color="default"
            variant="text"
            shape="circle"
            onClick={send}
            loading={loading}
          >
            <img src={IconSend} />
          </Button>
        </Space>
      </div>
    </div>
  )
}
