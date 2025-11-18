import IconBid from '@/assets/layout/bid.svg'
import IconCareer from '@/assets/layout/career.svg'
import IconHistory from '@/assets/layout/history.svg'
import IconHome from '@/assets/layout/home.svg'
import IconNewChat from '@/assets/layout/newchat.svg'
import IconNews from '@/assets/layout/news.svg'
import IconPolicy from '@/assets/layout/policy.svg'
import IconWorkspace from '@/assets/layout/workspace.svg'
import { useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { NavItem } from './nav-item'
import './nav.scss'

export function Nav() {
  const { pathname } = useLocation()

  const items = useMemo(
    () => [
      {
        key: 'home',
        label: '首页',
        icon: IconHome,
        href: '/',
      },
      {
        key: 'workspace',
        label: '工作空间',
        icon: IconWorkspace,
        href: '/workspace',
      },
      {
        key: 'newchat',
        label: '新的聊天',
        icon: IconNewChat,
        href: '/chat',
      },
      {
        key: 'history',
        label: '对话历史',
        icon: IconHistory,
        href: '#',
      },
      {
        key: 'repository',
        label: '知识库',
        icon: IconWorkspace,
        href: '/repository',
      },
      {
        key: 'news',
        label: '行业资讯',
        icon: IconNews,
        href: '#',
      },
      {
        key: 'policy',
        label: '政策法规',
        icon: IconPolicy,
        href: '#',
      },
      {
        key: 'bid',
        label: '招投标信息',
        icon: IconBid,
        href: '#',
      },
      {
        key: 'career',
        label: '职业规划',
        icon: IconCareer,
        href: '#',
      },
    ],
    [],
  )

  return (
    <div className="base-layout-nav">
      {items.map(({ key, ...item }) => (
        <NavItem key={key} {...item} active={pathname === item.href} />
      ))}
    </div>
  )
}
