declare namespace API {
  interface ChatItem {
    id: number
    role: import('@/configs').ChatRole
    type: import('@/configs').ChatType
    loading?: boolean
    error?: string
    content?: string
    think?: string

    documents?: Document[]
    reference?: Reference[]
    image_results?: {
      images?: {
        title: string
        imageUrl: string
        thumbnailUrl: string
        source: string
        link: string
        googleUrl: string
      }[]
    }
    thinks?: {
      id: string
      type: 'status' | 'search_results'
      results?: {
        id: string
        count?: number
        content?: string
      }[]
    }[]
    search_results?: {
      id: string
      subquery: string
      url: string
      name: string
      summary: string
      snippet: string
      siteName: string
      siteIcon: string
      host: string
    }[]
  }

  interface Document {
    document_id: string
    document_name: string
    preview: string
  }

  interface Reference {
    id: number
    title: string
    link: string
    content: string
    source: 'web' | 'knowledge'
  }
}
