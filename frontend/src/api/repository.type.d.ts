declare namespace API {
  type Repository = {
    document_id: string
    file_name: string
    file_size: number
    file_type: string
    status: 'completed'
    chunk_count: number
    created_at: string
    updated_at: string
  }
}
