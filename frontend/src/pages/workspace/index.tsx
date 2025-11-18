import * as api from '@/api'
import IconSearch from '@/assets/index/search.svg'
import { IFormModalProps } from '@/components/com-form/modal'
import { useComFilter } from '@/components/filter'
import { useRequest } from 'ahooks'
import { Button, Empty, Input, Pagination, Row, Space } from 'antd'
import { useState } from 'react'
import { WorkspaceCard } from './components/card'
import WorkspaceModal from './components/modal'
import styles from './index.module.scss'

export default function Index() {
  const [modalState, setModalState] =
    useState<IFormModalProps<API.WorkspaceDetail>>()

  const filter = useComFilter({
    initialValue: {
      keywords: '',
      page: 1,
    },
  })

  const { data } = useRequest(
    async () => {
      const { data } = await api.workspace.list({
        search: filter.form.keywords,
        page: filter.form.page,
        page_size: 8,
      })
      return {
        list: data.assistants,
        total: data.total,
      }
    },
    {
      refreshDeps: [filter.form],
    },
  )

  function reload() {
    filter.setForm((state) => ({ ...state, page: 1 }))
  }

  return (
    <div className={styles['index-page']}>
      <div className={styles['search-bar']}>
        <div className={styles['search-bar__input']}>
          <Input
            prefix={<img src={IconSearch} />}
            placeholder="搜索工作空间"
            size="large"
            value={filter.keywords}
            onChange={(e) => filter.setKeywords(e.target.value)}
            onPressEnter={() => {
              filter.setForm((state) => ({
                ...state,
                page: 1,
                keywords: filter.keywords,
              }))
            }}
            onBlur={() => {
              if (filter.keywords === filter.form.keywords) return
              filter.setForm((state) => ({
                ...state,
                page: 1,
                keywords: filter.keywords,
              }))
            }}
          />
        </div>

        <Space>
          <Button
            type="primary"
            size="large"
            onClick={() =>
              setModalState({
                open: true,
                title: '新建工作空间',
                formValue: {},
                onOk: async (form) => {
                  await api.workspace.create({
                    ...form,
                    prompt: '',
                    mcp_services: [],
                  })
                  setModalState((state) => ({ ...state, open: false }))
                  window.$app.message.success('新建成功')
                  reload()
                },
              })
            }
          >
            新建
          </Button>
        </Space>
      </div>

      <div className={styles['card-list']}>
        {data?.list?.length ? (
          data?.list?.map((item) => (
            <WorkspaceCard
              key={item.assistant_id}
              item={item}
              to={`/workspace/${item.assistant_id}`}
            />
          ))
        ) : data ? (
          <Empty style={{ width: '100%' }} />
        ) : null}
      </div>

      {data ? (
        <Row justify="center" style={{ marginTop: 20 }}>
          <Pagination
            current={filter.form.page}
            total={data?.total}
            pageSize={8}
            showSizeChanger={false}
            onChange={(page) => filter.setForm((state) => ({ ...state, page }))}
          />
        </Row>
      ) : null}

      {modalState && (
        <WorkspaceModal
          {...modalState}
          onCancel={() => setModalState({ open: false })}
        />
      )}
    </div>
  )
}
