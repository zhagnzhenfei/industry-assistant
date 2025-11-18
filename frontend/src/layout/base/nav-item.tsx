import classNames from 'classnames'
import { Link } from 'react-router-dom'
import './nav-item.scss'

export function NavItem(props: {
  icon: string
  label: string
  href: string
  active?: boolean
  dot?: boolean
  className?: string
}) {
  const { icon, label, href, active, dot, className, ...rest } = props

  return (
    <Link
      className={classNames('base-layout-nav__item', className, { active })}
      to={href}
      {...rest}
    >
      <img className="base-layout-nav__item-icon" src={icon} />
      <span className="base-layout-nav__item-label">{label}</span>

      {dot && <div className="base-layout-nav__item-dot" />}
    </Link>
  )
}
