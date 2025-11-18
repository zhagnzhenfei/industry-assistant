import {
  ProForm,
  type ProFormInstance,
  type ProFormProps,
} from '@ant-design/pro-components'
import { Form, Modal, type ModalProps } from 'antd'
import { type NamePath } from 'antd/es/form/interface'
import classNames from 'classnames'
import { useEffect, useRef, useState } from 'react'
import './modal.scss'

export type IFormModalProps<T> = Omit<ModalProps, 'onOk'> & {
  formValue?: Partial<T>
  formRef?:
    | React.MutableRefObject<ProFormInstance<T> | undefined>
    | React.RefObject<ProFormInstance<T> | undefined>
  formProps?: ProFormProps<T>
  readonly?: boolean
  onOk?: (form: T) => Promise<void> | void
  convertValue?: (value?: Partial<T>) => any
  transform?: (value: any) => Partial<T>
  nameList?: true | NamePath
}

export const ComFormModal = function <T>(props: IFormModalProps<T>) {
  const {
    formValue,
    readonly,
    onOk,
    convertValue,
    transform,
    nameList,
    formRef = useRef<ProFormInstance>(null),
    width = 780,
    className,
    children,
    formProps,
    maskClosable = false,
    ...modalProps
  } = props

  const [form] = Form.useForm<T>()
  useEffect(() => {
    form.resetFields()
    form.setFieldsValue(convertValue ? convertValue(formValue) : formValue)
  }, [formValue, form, convertValue])

  const [loading, setLoading] = useState(false)

  async function _onOk() {
    await formRef.current?.validateFields()
    const values = formRef.current?.getFieldsFormatValue?.(nameList)

    try {
      setLoading(true)
      await onOk?.(transform ? transform(values) : values)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      {...modalProps}
      className={classNames('com-form-modal', className)}
      width={width}
      onOk={_onOk}
      confirmLoading={loading}
      maskClosable={maskClosable}
    >
      <ProForm<T>
        form={form}
        formRef={formRef}
        submitter={false}
        readonly={readonly}
        {...formProps}
      >
        {children}
      </ProForm>
    </Modal>
  )
}

export default ComFormModal
