import * as api from '@/api'
import IconBg from '@/assets/index/bg.png'
import IconSearch from '@/assets/index/search.svg'
import { useComFilter } from '@/components/filter'
import { useRequest } from 'ahooks'
import { Empty, Input, Pagination, Row } from 'antd'
import { WorkspaceCard } from '../workspace/components/card'
import styles from './index.module.scss'

export default function Index() {
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

  return (
    <div className={styles['index-page']}>
      <div className={styles.header}>
        <img className={styles.bg} src={IconBg} />
        <div className={styles.title}>Hi～欢迎来到行业咨询助手</div>
        <div className={styles.desc}>
          大模型驱动的行业资讯助手，为不同类型用户提供更便捷的AI应用开发平台
        </div>
      </div>

      <div className={styles['search-bar']}>
        <div className={styles['switch']}>
          <div className={styles.active}>我的</div>
          <div>市场</div>
        </div>

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
      </div>

      <div className={styles['card-list']}>
        {data?.list?.length ? (
          data?.list?.map((item) => (
            <WorkspaceCard
              key={item.assistant_id}
              item={item}
              to={`/chat?assistant_id=${item.assistant_id}`}
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
    </div>
  )
}
