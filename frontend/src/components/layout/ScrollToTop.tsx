'use client'

import { usePathname } from 'next/navigation'
import { useEffect, useRef } from 'react'

export default function ScrollToTop() {
  const pathname = usePathname()
  const prev = useRef(pathname)

  useEffect(() => {
    if (prev.current !== pathname) {
      window.scrollTo(0, 0)
      prev.current = pathname
    }
  }, [pathname])

  return null
}
