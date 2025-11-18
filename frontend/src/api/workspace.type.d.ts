declare namespace API {
  interface Workspace {
    assistant_id: number
    name: string
    description?: string
    color?: string
  }

  interface WorkspaceDetail extends Workspace {
    prompt?: string
    repository_enable: boolean
    mcp_services?: {
      mcp_server_id: string
    }[]
    enable_knowledge_base?: boolean
  }
}
