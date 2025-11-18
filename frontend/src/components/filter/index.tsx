import { useEffect, useState } from 'react'

export function useComFilter<
  T extends {
    keywords: string
  },
>(options: { initialValue: T | (() => T) }) {
  const { initialValue } = options

  const [form, setForm] = useState(initialValue)
  const [show, setShow] = useState(false)
  const [keywords, setKeywords] = useState('')
  const [collection, setCollection] = useState(false)

  useEffect(() => {
    if (form.keywords === keywords) return
    setKeywords(form.keywords)
  }, [form])

  return {
    form,
    setForm,
    show,
    setShow,
    keywords,
    setKeywords,
    collection,
    setCollection,
  }
}
