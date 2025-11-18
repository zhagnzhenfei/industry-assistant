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
        return {
            'base_url': os.environ.get('API_BASE_URL', 'http://localhost:9380'),
            'api_key': os.environ.get('API_KEY', 'ragflow-FiZjAzYTVjMWM1YTExZjA4MGFmNTZlOT'),
            'default_dataset_id': os.environ.get('DEFAULT_DATASET_ID', '5299f1501c5a11f0a5ea56e92569c6d7'),
            'serper_api_key': os.environ.get('SERPER_API_KEY', '485a749de588ba9426d5de22f4ca1614a70e2e28'),
            'es_host': os.environ.get('ES_HOST', 'localhost'),
            'es_port': int(os.environ.get('ES_PORT', '1200')),
            'policy_index': os.environ.get('POLICY_INDEX', 'policy_documents'),
            'es_user': os.environ.get('ES_USER', 'elastic'),
            'es_password': os.environ.get('ES_PASSWORD', 'infini_rag_flow')
        } 