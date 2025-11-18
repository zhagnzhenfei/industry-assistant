#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
import re
import time
import os
import json

import copy
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Q, Search
from service.core.rag.utils import singleton
from service.core.api.utils.file_utils import get_project_base_directory
from service.core.rag.utils.doc_store_conn import MatchExpr, OrderByExpr, MatchTextExpr, MatchDenseExpr, FusionExpr
from service.core.rag.nlp import is_english
from dotenv import load_dotenv

load_dotenv()

ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", "9200"))
ES_USERNAME = os.getenv("ES_USERNAME", "")
ES_PASSWORD = os.getenv("ES_PASSWORD", "")
ATTEMPT_TIME = 2
PAGERANK_FLD = "pagerank_fea"
TAG_FLD = "tag_feas"

logger = logging.getLogger('ragflow.es_conn')


@singleton
class ESConnection():
    """
    Elasticsearch连接类
    实现DocStoreConnection接口
    负责与ES交互，进行文档存储和检索
    """
    def __init__(self):
        """
        初始化ES连接
        加载配置和映射文件
        建立与Elasticsearch的连接
        """
        self.info = {}
        self.es = None
        self.mapping = None
        self.es_available = False
        
        # 检查ES配置
        if not ES_HOST:
            logger.warning("ES_HOST not configured. Elasticsearch functionality will be disabled.")
            return
            
        try:
            logger.info(f"Use Elasticsearch {ES_HOST} as the doc engine.")
            
            # 构建ES连接参数
            es_config = {
                "hosts": [f"http://{ES_HOST}:{ES_PORT if 'ES_PORT' in globals() else 9200}"],
                "verify_certs": False,
                "timeout": 600
            }
            
            # 如果有用户名和密码，添加认证
            if ES_USERNAME and ES_PASSWORD:
                es_config["basic_auth"] = (ES_USERNAME, ES_PASSWORD)
            
            self.es = Elasticsearch(**es_config)
            
            # 测试连接
            self.es.ping()
            self.es_available = True
            logger.info("Elasticsearch connection established successfully.")
            
            # 加载映射配置
            fp_mapping = os.path.join(get_project_base_directory(), "conf", "mapping.json")
            if os.path.exists(fp_mapping):
                self.mapping = json.load(open(fp_mapping, "r"))
            else:
                logger.warning(f"Mapping file not found: {fp_mapping}")
                self.mapping = {}
                
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch connection: {str(e)}")
            logger.warning("Elasticsearch functionality will be disabled.")
            self.es = None
            self.es_available = False


    """
    Helper functions for search result
    """

    def getTotal(self, res):
        """
        获取搜索结果总数
        处理不同版本ES返回的不同格式
        """
        if isinstance(res["hits"]["total"], type({})):
            return res["hits"]["total"]["value"]
        return res["hits"]["total"]

    def getChunkIds(self, res):
        """
        提取搜索结果中的文档ID
        返回所有匹配文档的ID列表
        """
        return [d["_id"] for d in res["hits"]["hits"]]
    

    def getHighlight(self, res, keywords: list[str], fieldnm: str):
        """
        处理搜索结果的高亮片段
        特别处理中英文不同的高亮方式
        支持关键词突出显示
        """
        ans = {}
        for d in res["hits"]["hits"]:
            hlts = d.get("highlight")
            if not hlts:
                continue
            txt = "...".join([a for a in list(hlts.items())[0][1]])
            if not is_english(txt.split()):
                ans[d["_id"]] = txt
                continue

            # 针对英文内容的特殊处理
            txt = d["_source"][fieldnm]
            txt = re.sub(r"[\r\n]", " ", txt, flags=re.IGNORECASE | re.MULTILINE)
            txts = []
            for t in re.split(r"[.?!;\n]", txt):
                for w in keywords:
                    t = re.sub(r"(^|[ .?/'\"\(\)!,:;-])(%s)([ .?/'\"\(\)!,:;-])" % re.escape(w), r"\1<em>\2</em>\3", t,
                               flags=re.IGNORECASE | re.MULTILINE)
                if not re.search(r"<em>[^<>]+</em>", t, flags=re.IGNORECASE | re.MULTILINE):
                    continue
                txts.append(t)
            ans[d["_id"]] = "...".join(txts) if txts else "...".join([a for a in list(hlts.items())[0][1]])

        return ans
    

    def getAggregation(self, res, fieldnm: str):
        """
        提取搜索结果的聚合信息
        处理字段聚合统计数据
        返回字段值及其文档数量
        """
        agg_field = "aggs_" + fieldnm
        if "aggregations" not in res or agg_field not in res["aggregations"]:
            return list()
        bkts = res["aggregations"][agg_field]["buckets"]
        return [(b["key"], b["doc_count"]) for b in bkts]

    def getFields(self, res, fields: list[str]) -> dict[str, dict]:
        """
        从搜索结果中提取指定字段
        处理不同类型的字段值
        返回文档ID到字段映射的字典
        """
        res_fields = {}
        if not fields:
            return {}
        for d in self.__getSource(res):
            m = {n: d.get(n) for n in fields if d.get(n) is not None}
            for n, v in m.items():
                if isinstance(v, list):
                    m[n] = v
                    continue
                if not isinstance(v, str):
                    m[n] = str(m[n])
                # if n.find("tks") > 0:
                #     m[n] = rmSpace(m[n])

            if m:
                res_fields[d["id"]] = m
        return res_fields


    def __getSource(self, res):
        """
        处理ES搜索结果
        提取文档内容和元数据
        添加ID和分数信息
        """
        rr = []
        for d in res["hits"]["hits"]:
            d["_source"]["id"] = d["_id"]
            d["_source"]["_score"] = d["_score"]
            rr.append(d["_source"])
        return rr

    """
    Database operations
    """
    def insert(self, documents: list[dict], indexName: str, knowledgebaseId: str = None) -> list[str]:
        """
        批量插入文档到ES
        使用ES bulk API提高性能
        支持重试机制处理超时情况
        
        参数:
            documents: 要插入的文档列表
            indexName: 索引名称
            knowledgebaseId: 知识库ID
            
        返回:
            错误信息列表，成功时为空
        """
        if not self.es_available:
            logger.warning("Elasticsearch is not available. Document indexing skipped.")
            return ["Elasticsearch is not available"]
            
        # Refers to https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-bulk.html
        operations = []
        for d in documents:
            assert "_id" not in d
            assert "id" in d
            d_copy = copy.deepcopy(d)
            meta_id = d_copy.pop("id", "")
            operations.append(
                {"index": {"_index": indexName, "_id": meta_id}})
            operations.append(d_copy)

        res = []
        for _ in range(ATTEMPT_TIME):
            try:
                res = []
                r = self.es.bulk(index=(indexName), operations=operations,
                                 refresh=False, timeout="60s")
                if re.search(r"False", str(r["errors"]), re.IGNORECASE):
                    return res

                for item in r["items"]:
                    for action in ["create", "delete", "index", "update"]:
                        if action in item and "error" in item[action]:
                            res.append(str(item[action]["_id"]) + ":" + str(item[action]["error"]))
                return res
            except Exception as e:
                res.append(str(e))
                logger.warning("ESConnection.insert got exception: " + str(e))
                res = []
                if re.search(r"(Timeout|time out)", str(e), re.IGNORECASE):
                    res.append(str(e))
                    time.sleep(3)
                    continue
        return res
    

    def search(
            self, selectFields: list[str],
            highlightFields: list[str],
            condition: dict,
            matchExprs: list[MatchExpr],
            orderBy: OrderByExpr,
            offset: int,
            limit: int,
            indexNames: str | list[str],
            knowledgebaseIds: list[str],
            aggFields: list[str] = [],
            rank_feature: dict | None = None
    ):
        """
        在ES中执行复杂搜索
        支持全文搜索、向量搜索和混合检索
        处理高亮、排序、聚合和分页
        
        参数:
            selectFields: 要返回的字段
            highlightFields: 需要高亮的字段
            condition: 过滤条件
            matchExprs: 匹配表达式
            orderBy: 排序条件
            offset: 分页起始位置
            limit: 返回结果数量
            indexNames: 索引名称
            knowledgebaseIds: 知识库ID列表
            aggFields: 聚合字段
            rank_feature: 排序特征
            
        返回:
            ES搜索结果对象
        """
        if not self.es_available:
            logger.warning("Elasticsearch is not available. Returning empty search results.")
            return {
                "hits": {
                    "total": {"value": 0, "relation": "eq"},
                    "hits": []
                },
                "timed_out": False,
                "aggregations": {}
            }
            
        """
        Refers to https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html
        """
        if isinstance(indexNames, str):
            indexNames = indexNames.split(",")
        assert isinstance(indexNames, list) and len(indexNames) > 0
        assert "_id" not in condition

        # 构建布尔查询
        bqry = Q("bool", must=[])
        condition["kb_id"] = knowledgebaseIds
        for k, v in condition.items():
            if k == "available_int":
                if v == 0:
                    bqry.filter.append(Q("range", available_int={"lt": 1}))
                else:
                    bqry.filter.append(
                        Q("bool", must_not=Q("range", available_int={"lt": 1})))
                continue
            if not v:
                continue
            if isinstance(v, list):
                bqry.filter.append(Q("terms", **{k: v}))
            elif isinstance(v, str) or isinstance(v, int):
                bqry.filter.append(Q("term", **{k: v}))
            else:
                raise Exception(
                    f"Condition `{str(k)}={str(v)}` value type is {str(type(v))}, expected to be int, str or list.")

        s = Search()
        vector_similarity_weight = 0.5
        # 处理融合查询的权重设置
        for m in matchExprs:
            if isinstance(m, FusionExpr) and m.method == "weighted_sum" and "weights" in m.fusion_params:
                assert len(matchExprs) == 3 and isinstance(matchExprs[0], MatchTextExpr) and isinstance(matchExprs[1],
                                                                                                        MatchDenseExpr) and isinstance(
                    matchExprs[2], FusionExpr)
                weights = m.fusion_params["weights"]
                vector_similarity_weight = float(weights.split(",")[1])
        # 处理不同类型的匹配表达式
        for m in matchExprs:
            if isinstance(m, MatchTextExpr):
                # 全文检索查询
                minimum_should_match = m.extra_options.get("minimum_should_match", 0.0)
                if isinstance(minimum_should_match, float):
                    minimum_should_match = str(int(minimum_should_match * 100)) + "%"
                bqry.must.append(Q("query_string", fields=m.fields,
                                   type="best_fields", query=m.matching_text,
                                   minimum_should_match=minimum_should_match,
                                   boost=1))
                bqry.boost = 1.0 - vector_similarity_weight

            elif isinstance(m, MatchDenseExpr):
                # 向量检索查询
                assert (bqry is not None)
                similarity = 0.0
                if "similarity" in m.extra_options:
                    similarity = m.extra_options["similarity"]
                s = s.knn(m.vector_column_name,
                          m.topn,
                          m.topn * 2,
                          query_vector=list(m.embedding_data),
                          filter=bqry.to_dict(),
                          similarity=similarity,
                          )

        # 处理排序特征
        if bqry and rank_feature:
            for fld, sc in rank_feature.items():
                if fld != PAGERANK_FLD:
                                         fld = f"{TAG_FLD}.{fld}"
                bqry.should.append(Q("rank_feature", field=fld, linear={}, boost=sc))

        if bqry:
            s = s.query(bqry)
        # 设置高亮字段
        for field in highlightFields:
            s = s.highlight(field)

        # 处理排序
        if orderBy:
            orders = list()
            for field, order in orderBy.fields:
                order = "asc" if order == 0 else "desc"
                if field in ["page_num_int", "top_int"]:
                    order_info = {"order": order, "unmapped_type": "float",
                                  "mode": "avg", "numeric_type": "double"}
                elif field.endswith("_int") or field.endswith("_flt"):
                    order_info = {"order": order, "unmapped_type": "float"}
                else:
                    order_info = {"order": order, "unmapped_type": "text"}
                orders.append({field: order_info})
            s = s.sort(*orders)

        # 设置聚合
        for fld in aggFields:
            s.aggs.bucket(f'aggs_{fld}', 'terms', field=fld, size=1000000)

        # 处理分页
        if limit > 0:
            s = s[offset:offset + limit]
        q = s.to_dict()
        logger.debug(f"ESConnection.search {str(indexNames)} query: " + json.dumps(q))

        # 执行查询并处理超时重试
        for i in range(ATTEMPT_TIME):
            try:
                #print(json.dumps(q, ensure_ascii=False))
                res = self.es.search(index=indexNames,
                                     body=q,
                                     timeout="600s",
                                     # search_type="dfs_query_then_fetch",
                                     track_total_hits=True,
                                     _source=True)
                if str(res.get("timed_out", "")).lower() == "true":
                    raise Exception("Es Timeout.")
                logger.debug(f"ESConnection.search {str(indexNames)} res: " + str(res))
                return res
            except Exception as e:
                logger.exception(f"ESConnection.search {str(indexNames)} query: " + str(q))
                if str(e).find("Timeout") > 0:
                    continue
                raise e
        logger.error("ESConnection.search timeout for 3 times!")
        raise Exception("ESConnection.search timeout.")
    
    def delete_user_document_data(self, file_name: str, index_name: str) -> dict:
        """
        智能删除用户文档数据（按文件名）
        
        参数:
            file_name: 文件名
            index_name: 索引名称（用户ID）
            
        返回:
            删除结果详情
        """
        result = {
            'deleted_count': 0,
            'index_exists': False,
            'strategy_used': '',
            'errors': []
        }
        
        if not self.es_available:
            result['errors'].append("Elasticsearch连接不可用")
            return result
            
        try:
            # 1. 检查索引是否存在
            if not self.es.indices.exists(index=index_name):
                result['strategy_used'] = 'index_not_exists'
                logger.info(f"ES索引不存在: {index_name}")
                return result
                
            result['index_exists'] = True
            
            # 2. 检查索引中文档数量
            count_response = self.es.count(index=index_name)
            total_docs = count_response.get('count', 0)
            
            if total_docs == 0:
                result['strategy_used'] = 'index_empty'
                logger.info(f"ES索引为空: {index_name}")
                return result
            
            # 3. 尝试按文件名删除（多种字段匹配）
            import xxhash
            doc_id = xxhash.xxh64(file_name.encode("utf-8")).hexdigest()
            
            # 构建多条件查询
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"doc_id": doc_id}},
                            {"term": {"docnm": file_name}},
                            {"term": {"docnm_kwd": file_name}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            
            # 执行删除
            response = self.es.delete_by_query(
                index=index_name,
                body=query,
                refresh=True
            )
            
            deleted_count = response.get('deleted', 0)
            result['deleted_count'] = deleted_count
            result['strategy_used'] = 'multi_field_match'
            
            logger.info(f"按文件名删除ES文档: {file_name}, 删除数量: {deleted_count}, index: {index_name}")
            
            # 4. 如果删除后索引为空，可以考虑删除索引（可选）
            if deleted_count > 0:
                remaining_count = self.es.count(index=index_name).get('count', 0)
                if remaining_count == 0:
                    result['strategy_used'] += '_index_cleaned'
                    
            return result
            
        except Exception as e:
            error_msg = f"删除ES文档失败: file_name={file_name}, index={index_name}, error={str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
            return result