import os
from typing import Dict, Any

class ServiceConfig:
    """Configuration for service API connections"""
    
    @staticmethod
    def get_api_config() -> Dict[str, Any]:
        """
        Get API configuration from environment variables or default settings
        
        Returns:
            Dictionary with API configuration
        """
        # Validate critical environment variables
required_vars = []
if not os.environ.get('DASHSCOPE_API_KEY'):
    required_vars.append('DASHSCOPE_API_KEY')
if not os.environ.get('OPENAI_API_KEY'):
    required_vars.append('OPENAI_API_KEY')
if not os.environ.get('SERPER_API_KEY'):
    required_vars.append('SERPER_API_KEY')

if required_vars:
    raise ValueError(f"Required environment variables not set: {', '.join(required_vars)}")

return {
            'base_url': os.environ.get('API_BASE_URL', 'http://localhost:9380'),
            'api_key': os.environ.get('API_KEY'),  # Only use environment variable
            'default_dataset_id': os.environ.get('DEFAULT_DATASET_ID', '5299f1501c5a11f0a5ea56e92569c6d7'),
            'serper_api_key': os.environ.get('SERPER_API_KEY'),  # Only use environment variable
            'openai_api_key': os.environ.get('OPENAI_API_KEY'),
            'dashscope_api_key': os.environ.get('DASHSCOPE_API_KEY'),
            # Milvus配置（替代Elasticsearch）
            'milvus_host': os.environ.get('MILVUS_HOST', 'localhost'),
            'milvus_port': int(os.environ.get('MILVUS_PORT', '19530')),
            'milvus_collection': os.environ.get('MILVUS_COLLECTION', 'document_chunks')
        } 