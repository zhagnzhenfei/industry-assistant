"""
阿里云百炼API配置
"""
import os

class BailianConfig:
    """阿里云百炼配置类"""
    
    def __init__(self):
        # 使用DASHSCOPE_BASE_URL环境变量，并添加聊天接口路径
        # 因为我们使用直接HTTP请求，不是OpenAI客户端，所以需要手动添加完整路径
        base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.api_url = f"{base_url}/chat/completions"
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
    
    def is_configured(self) -> bool:
        """检查配置是否完整"""
        return bool(self.api_key)
    
    def get_headers(self) -> dict:
        """获取请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

# 全局配置实例
bailian_config = BailianConfig()
