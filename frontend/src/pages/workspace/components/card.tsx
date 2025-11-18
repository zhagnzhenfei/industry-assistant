import IconSearch from '@/assets/index/search.svg'
import Color from 'color'
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import styles from './card.module.scss'
import WorkspaceIcon from './icon'

export function WorkspaceCard(props: { item: API.Workspace; to: string }) {
  const { item, to } = props

  const color = useMemo(() => item.color || '#000', [item])
  const bgColor = useMemo(() => {
    return new Color(color).lightness(95).rgb().toString()
  }, [color])

  return (
    <Link
      className={styles['workspace-card']}
      style={{
        backgroundColor: bgColor,
        color: color,
      }}
      to={to}
    >
      <WorkspaceIcon icon={IconSearch} color={item.color} />

      <div className={styles['workspace-card__title']}>{item.name}</div>
      <div className={styles['workspace-card__desc']}>{item.description}</div>
    </Link>
  )
}
