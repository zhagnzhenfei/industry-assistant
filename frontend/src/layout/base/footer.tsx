import IconMessage from '@/assets/layout/message.svg'
import { Popconfirm } from 'antd'
import './footer.scss'
import { NavItem } from './nav-item'

export function Footer() {
  return (
    <div className="base-layout-footer">
      <Popconfirm
        title="翔达物流有限公司 - 企业概览"
        description={
          <>
            <blockquote
              style={{
                backgroundColor: '#f5f5f5',
                borderLeft: '2px solid #e5e5e5',
                paddingLeft: '10px',
                margin: 0,
              }}
            >
              <p>
                基本信息
                <br />
                　成立时间：2018年
                <br />
                　地点：苏州市工业园区
                <br />
                　员工人数：38人
              </p>

              <p>
                业务与资源
                <br />
                　业务范围：城市配送、区域货运、仓储服务
                <br />
                　企业结构：管理层, 运营团队, 行政支持
                <br />
                　车队资源：5重型, 12中型, 8轻型货车
                <br />
                　自有仓库：1500平方米
                <br />
                　业务特点：专注长三角, 稳定客户群, 发展冷链
              </p>

              <p>
                经营状况
                <br />
                　年营业额：约980万元
                <br />
                　主要成本：燃油、车辆维护、人工
                <br />
                　近两年增长率：15-20%
              </p>
            </blockquote>

            <p>
              监测到新出台《有效降低全社会物流成本行动方案》可以帮助你节约成本，是否查看？
            </p>
          </>
        }
        icon={null}
        placement="right"
        style={{ maxWidth: 200 }}
        onConfirm={() => {
          window.open(
            'https://www.gov.cn/zhengce/202411/content_6989622.htm',
            '_blank',
          )
        }}
      >
        <NavItem icon={IconMessage} label="我的消息" href="#" dot />
      </Popconfirm>
    </div>
  )
}
