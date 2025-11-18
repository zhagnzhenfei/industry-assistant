import * as api from '@/api'
import IconSearch from '@/assets/index/search.svg'
import IconRepository from '@/assets/workspace/repository.svg'
import { IFormModalProps } from '@/components/com-form/modal'
import { EditOutlined, LeftOutlined } from '@ant-design/icons'
import { useRequest } from 'ahooks'
import { Button, Checkbox, Col, Input, Row, Space, Switch } from 'antd'
import dayjs from 'dayjs'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import WorkspaceIcon from './components/icon'
import WorkspaceModal from './components/modal'
import styles from './detail.module.scss'

export default function Index() {
  const query = useParams()

  const [modalState, setModalState] =
    useState<IFormModalProps<API.WorkspaceDetail>>()

  const { data, mutate } = useRequest(async () => {
    const { data } = await api.workspace.detail({ id: query.id! })
    return data
  })

  return (
    <div className={styles['workspace-detail']}>
      <Header
        data={data}
        onEdit={() =>
          setModalState({
            open: true,
            title: '修改工作空间',
            formValue: data,
            onOk: async (form) => {
              mutate({
                ...data!,
                ...form,
              })
              setModalState((state) => ({ ...state, open: false }))
            },
          })
        }
        onSubmit={async () => {
          await api.workspace.update(data!)
          window.$app.message.success('发布成功')
        }}
      />

      <div className={styles['workspace-detail__body']}>
        <div className={styles['left']}>
          <div className={styles['header']}>人设与回复逻辑</div>
          <Prompts
            value={data?.prompt ?? ''}
            onChange={(value) =>
              mutate({
                ...data!,
                prompt: value,
              })
            }
          />
        </div>
        <div className={styles['right']}>
          <div className={styles['header']}>
            <Row>
              <Col className={styles['title']} flex="auto">
                编排
              </Col>
              <Col flex="none">
                <Space
                  align="center"
                  style={{
                    lineHeight: 1,
                  }}
                >
                  <img src={IconRepository} />
                  <span>知识库配置</span>
                  <Switch
                    size="small"
                    checked={data?.enable_knowledge_base}
                    onChange={(e) => mutate({ ...data!, enable_knowledge_base: e })}
                  />
                </Space>
              </Col>
            </Row>
          </div>

          {data ? (
            <Plugins
              value={data.mcp_services ?? []}
              onChange={(value) => mutate({ ...data!, mcp_services: value })}
            />
          ) : null}
        </div>
      </div>

      {modalState && (
        <WorkspaceModal
          {...modalState}
          onCancel={() => setModalState({ open: false })}
        />
      )}
    </div>
  )
}

function Header(props: {
  data?: API.WorkspaceDetail
  onEdit?: () => void
  onSubmit?: () => void
}) {
  const { data, onEdit, onSubmit } = props

  const navigate = useNavigate()

  return (
    <div className={styles['workspace-detail__header']}>
      <div className={styles['left']}>
        <Button
          variant="text"
          color="default"
          shape="circle"
          onClick={() => navigate(-1)}
        >
          <LeftOutlined />
        </Button>

        <WorkspaceIcon icon={IconSearch} color={data?.color} size={40} />

        <div
          className={styles['title-container']}
          style={{
            color: data?.color,
          }}
        >
          <div className={styles['title']}>{data?.name}</div>
          <Button
            variant="text"
            color="default"
            shape="circle"
            onClick={onEdit}
          >
            <EditOutlined style={{ fontSize: 18 }} />
          </Button>
        </div>
      </div>
      <div className={styles['right']}>
        <Button type="primary" onClick={onSubmit}>
          发布
        </Button>
      </div>
    </div>
  )
}

function Prompts(props: { value: string; onChange: (value: string) => void }) {
  const { value, onChange } = props

  return (
    <Input.TextArea
      className={styles['prompts']}
      placeholder="输入/自动编写提示词或输入插入已配置的技能"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

function Plugins(props: {
  value: API.WorkspaceDetail['mcp_services']
  onChange: (value: API.WorkspaceDetail['mcp_services']) => void
}) {
  const { data } = useRequest(async () => {
    const { data } = await api.mcp.list()
    return data.servers
  })

  const defaultValue = useMemo(
    () => props.value?.map((item) => item.mcp_server_id),
    [props.value],
  )

  return (
    <Checkbox.Group
      className={styles['plugins']}
      defaultValue={defaultValue}
      onChange={(e) => {
        props.onChange?.(e.map((item) => ({ mcp_server_id: item })))
      }}
    >
      {data?.map((item) => (
        <Checkbox
          className={styles['plugins__item']}
          value={item.id}
          key={item.id}
        >
          <WorkspaceIcon
            className={styles['icon']}
            icon={IconSearch}
            size={40}
          />

          <div className={styles['info']}>
            <div className={styles['title']}>{item.name}</div>
            <div className={styles['desc']}>{item.description}</div>
            <div className={styles['time']}>
              发布于 {dayjs(item.created_at).format('YYYY-MM-DD HH:mm')}
            </div>
          </div>
        </Checkbox>
      ))}
    </Checkbox.Group>
  )
}
