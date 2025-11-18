import ComFormModal, { type IFormModalProps } from '@/components/com-form/modal'
import { ProFormText, ProFormTextArea } from '@ant-design/pro-components'

type Detail = API.WorkspaceDetail

const convertValue: IFormModalProps<Detail>['convertValue'] = (form) => ({
  ...form,
})

const transform: IFormModalProps<Detail>['transform'] = (form: any) => ({
  ...form,
})

export default function ProductModal(props: IFormModalProps<Detail>) {
  const { ...modalProps } = props

  return (
    <ComFormModal<Detail>
      {...modalProps}
      convertValue={convertValue}
      transform={transform}
      width={472}
    >
      <ProFormText
        label="工作空间名称"
        name="name"
        style={{ width: '100%' }}
        rules={[
          {
            required: true,
            message: '输入工作空间名称',
          },
        ]}
      />

      <ProFormTextArea
        label="工作空间介绍"
        name="description"
        style={{ width: '100%' }}
      />
    </ComFormModal>
  )
}
