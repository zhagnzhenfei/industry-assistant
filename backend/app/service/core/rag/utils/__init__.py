#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import os
import re
import tiktoken
from service.core.api.utils.file_utils import get_project_base_directory

def singleton(cls, *args, **kw):
    """
    单例模式装饰器
    确保类只有一个实例，针对每个进程创建唯一实例
    用于需要全局访问的组件和资源管理
    """
    instances = {}

    def _singleton():
        key = str(cls) + str(os.getpid())
        if key not in instances:
            instances[key] = cls(*args, **kw)
        return instances[key]

    return _singleton


def rmSpace(txt):
    """
    移除文本中多余的空格
    优化文本显示格式，保留语义相关的空格
    特别处理英文单词、标点符号等周围的空格
    """
    txt = re.sub(r"([^a-z0-9.,\)>]) +([^ ])", r"\1\2", txt, flags=re.IGNORECASE)
    return re.sub(r"([^ ]) +([^a-z0-9.,\(<])", r"\1\2", txt, flags=re.IGNORECASE)


def findMaxDt(fnm):
    """
    从文件中查找最大日期时间
    用于确定数据时间范围或最后更新时间
    返回格式为 'YYYY-MM-DD HH:MM:SS' 的最大日期时间
    """
    m = "1970-01-01 00:00:00"
    try:
        with open(fnm, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip("\n")
                if line == 'nan':
                    continue
                if line > m:
                    m = line
    except Exception:
        pass
    return m

  
def findMaxTm(fnm):
    """
    从文件中查找最大时间戳
    用于确定数据的最新时间点
    返回整数形式的最大时间戳值
    """
    m = 0
    try:
        with open(fnm, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip("\n")
                if line == 'nan':
                    continue
                if int(line) > m:
                    m = int(line)
    except Exception:
        pass
    return m


# 配置tiktoken缓存目录并初始化编码器
tiktoken_cache_dir = get_project_base_directory()
os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir
# encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
encoder = tiktoken.get_encoding("cl100k_base")


def num_tokens_from_string(string: str) -> int:
    """
    计算字符串中的token数量
    使用tiktoken库进行分词计算
    用于限制输入长度和优化资源使用
    
    参数:
        string: 要计算的文本字符串
        
    返回:
        token数量
    """
    try:
        return len(encoder.encode(string))
    except Exception:
        return 0


def truncate(string: str, max_len: int) -> str:
    """
    截断过长的文本
    基于token数量截断，而不是字符数
    保证不超过模型的最大输入长度限制
    
    参数:
        string: 原始文本
        max_len: 最大token数量
        
    返回:
        截断后的文本
    """
    return encoder.decode(encoder.encode(string)[:max_len])
