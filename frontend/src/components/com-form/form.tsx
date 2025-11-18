import {
  ProForm,
  type ProFormInstance,
  type ProFormProps,
} from '@ant-design/pro-components'
import { Form } from 'antd'
import { type NamePath } from 'antd/es/form/interface'
import classNames from 'classnames'
import { useEffect, useRef } from 'react'

export type IFormProps<T = Record<string, any>> = Omit<
  ProFormProps<T>,
  'onFinish' | 'form'
> & {
  formValue?: Partial<T>
  formRef?:
    | React.MutableRefObject<ProFormInstance<T> | undefined>
    | React.RefObject<ProFormInstance<T> | undefined>
  readonly?: boolean
  onFinish?: (form: T) => Promise<void> | void
  convertValue?: (value?: Partial<T>) => any
  transform?: (value: any) => Partial<T>
  nameList?: true | NamePath
}

export const ComForm = function <T = Record<string, any>>(
  props: IFormProps<T>,
) {
  const {
    formValue,
    readonly,
    onFinish,
    convertValue,
    transform,
    nameList,
    formRef = useRef<ProFormInstance>(null),
    className,
    children,
    ...formProps
  } = props

  const [form] = Form.useForm<T>()
  useEffect(() => {
    form.resetFields()
    form.setFieldsValue(convertValue ? convertValue(formValue) : formValue)
  }, [formValue, form, convertValue])

  async function _onFinish() {
    await formRef.current?.validateFields()
    const values = formRef.current?.getFieldsFormatValue?.(nameList)

    await onFinish?.(transform ? transform(values) : values)
  }

  return (
    <ProForm<T>
      className={classNames('com-form', className)}
      form={form}
      formRef={formRef}
      readonly={readonly}
      onFinish={_onFinish}
      children={children as any}
      {...formProps}
    />
  )
}

export default ComForm
