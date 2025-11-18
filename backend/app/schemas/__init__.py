# Document schemas package 

from .document import (
    DocumentUploadResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentDeleteRequest,
    DocumentDeleteResponse,
    DocumentSearchRequest,
    DocumentSearchResponse
)

from .search import (
    WebSearchRequest,
    SearchResultItem,
    WebSearchResponse
)

from .chat import (
    ChatSessionCreateRequest,
    ChatSessionResponse,
    ChatSessionListResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatSessionUpdateRequest,
    ChatSessionDeleteResponse
)

from .user import (
    UserRegister,
    UserLogin,
    UserInfo,
    TokenResponse,
    UserResponse,
    PasswordChange,
    UserUpdate
)

from .assistant import (
    AssistantCreateRequest,
    AssistantUpdateRequest,
    AssistantResponse,
    AssistantListResponse,
    AssistantDeleteResponse,
    KnowledgeBaseItem,
    AssistantDetailResponse
)


__all__ = [
    # Document schemas
    'DocumentUploadResponse',
    'DocumentInfo',
    'DocumentListResponse',
    'DocumentDeleteRequest',
    'DocumentDeleteResponse',
    'DocumentSearchRequest',
    'DocumentSearchResponse',
    
    # Search schemas
    'WebSearchRequest',
    'SearchResultItem',
    'WebSearchResponse',
    
    # Chat schemas
    'ChatSessionCreateRequest',
    'ChatSessionResponse',
    'ChatSessionListResponse',
    'ChatMessageRequest',
    'ChatMessageResponse',
    'ChatHistoryResponse',
    'ChatCompletionRequest',
    'ChatCompletionResponse',
    'ChatSessionUpdateRequest',
    'ChatSessionDeleteResponse',
    
    # User schemas
    'UserRegister',
    'UserLogin',
    'UserInfo',
    'TokenResponse',
    'UserResponse',
    'PasswordChange',
    'UserUpdate',
    
    # Assistant schemas
    'AssistantCreateRequest',
    'AssistantUpdateRequest',
    'AssistantResponse',
    'AssistantListResponse',
    'AssistantDeleteResponse',
    'KnowledgeBaseItem',
    'AssistantDetailResponse'
] 