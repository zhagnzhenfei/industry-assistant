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

import logging
import json
import os
import time
import re
from nltk.corpus import wordnet
from service.core.api.utils.file_utils import get_project_base_directory


class Dealer:
    """
    同义词处理类
    管理同义词词典，提供同义词查询功能
    支持本地词典和Redis缓存的远程词典
    """
    def __init__(self, redis=None):
        """
        初始化同义词处理器
        加载本地同义词词典文件，配置Redis连接
        
        参数:
            redis: Redis连接对象，用于获取远程同义词词典
        """
        self.lookup_num = 100000000
        self.load_tm = time.time() - 1000000
        self.dictionary = None
        path = os.path.join(get_project_base_directory(), "rag/res", "synonym.json")
        try:
            # 尝试从本地文件加载同义词词典
            self.dictionary = json.load(open(path, 'r'))
        except Exception:
            logging.debug("Missing synonym.json")
            self.dictionary = {}

        if not redis:
            logging.debug(
                "Realtime synonym is disabled, since no redis connection.")
        if not len(self.dictionary.keys()):
            logging.debug("Fail to load synonym")

        self.redis = redis
        self.load()

    def load(self):
        """
        从Redis加载同义词词典
        按需更新词典数据，避免频繁加载
        设置了刷新间隔和查询次数阈值
        """
        if not self.redis:
            return

        if self.lookup_num < 100:
            return
        tm = time.time()
        if tm - self.load_tm < 3600:
            return

        self.load_tm = time.time()
        self.lookup_num = 0
        d = self.redis.get("kevin_synonyms")
        if not d:
            return
        try:
            d = json.loads(d)
            self.dictionary = d
        except Exception as e:
            logging.error("Fail to load synonym!" + str(e))

    def lookup(self, tk):
        """
        查询词语的同义词
        英文词汇使用WordNet查询
        中文词汇使用自定义词典查询
        
        参数:
            tk: 待查询的词语
            
        返回:
            同义词列表
        """
        if re.match(r"[a-z]+$", tk):
            # 英文单词使用WordNet查询同义词
            res = list(set([re.sub("_", " ", syn.name().split(".")[0]) for syn in wordnet.synsets(tk)]) - set([tk]))
            return [t for t in res if t]

        # 非英文词汇使用自定义词典查询
        self.lookup_num += 1
        self.load()
        res = self.dictionary.get(re.sub(r"[ \t]+", " ", tk.lower()), [])
        if isinstance(res, str):
            res = [res]
        return res


if __name__ == '__main__':
    dl = Dealer()
    print(dl.dictionary)
