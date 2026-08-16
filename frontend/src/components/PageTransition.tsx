import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { AppPage } from '../nav'

type Props = {
  page: AppPage
  children: ReactNode
}

export function PageTransition({ page, children }: Props) {
  const [visible, setVisible] = useState(children)
  const [anim, setAnim] = useState('page-enter')
  const first = useRef(true)
  const childrenRef = useRef(children)
  childrenRef.current = children

  useEffect(() => {
    if (first.current) {
      first.current = false
      setVisible(childrenRef.current)
      return
    }
    setAnim('page-exit')
    const t = window.setTimeout(() => {
      setVisible(childrenRef.current)
      setAnim('page-enter')
    }, 320)
    return () => window.clearTimeout(t)
  }, [page])

  useEffect(() => {
    if (anim !== 'page-exit') {
      setVisible(children)
    }
  }, [children, anim])

  return (
    <div className={`page-frame ${anim}`}>
      <div className="page-scan" aria-hidden />
      <div className="page-burst" aria-hidden />
      {visible}
    </div>
  )
}
