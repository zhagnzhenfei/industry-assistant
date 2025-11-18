import classNames from 'classnames'
import styles from './icon.module.scss'

export default function WorkspaceIcon(props: {
  className?: string
  style?: React.CSSProperties

  icon: string
  color?: string
  size?: number
}) {
  const { className, style, icon, color = '#000', size = 48 } = props

  return (
    <div
      className={classNames(styles['workspace-icon'], className)}
      style={{
        borderColor: color,
        width: size,
        height: size,
        borderRadius: size / 4,
        ...style,
      }}
    >
      <img src={icon} />
    </div>
  )
}
