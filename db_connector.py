from elasticsearch import Elasticsearch
import json


# 엘라스틱 서치 연결 초기화
class DBConnector:
    def __init__(self, es_url="https://youngchannel.co.kr:5555", index_name="products_mart2"):
        self.es = Elasticsearch(es_url, verify_certs=True)
        self.index_name = index_name

    def search_filtered_products(self, category, name, conditions, top_k=3):
        """
        카테고리, 상품명, 조건 기반으로 엘라스틱 서치에서 필터링된 상품을 검색합니다.
        """
        # Elasticsearch 쿼리 생성
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"category": category}}  # 카테고리를 제한
                    ],
                    "must": [  # 상품명에 name이 포함된 상품 검색
                        {
                            "wildcard": {
                                "product_name": f"*{name}*"  # 상품명에 name 포함
                            }
                        }
                    ]
                }
            },
            "size": top_k,  # 상위 K개 결과 제한
            "sort": {"_score": "desc"},  # 높은 점수 순으로 정렬
            "_source": ["category", "image_url", "original_price", "discount_price", "product_name", "description"]  # 필요한 필드만 반환
        }

        # 조건 추가
        # 조건 추가
        if conditions:
            query["query"]["bool"]["should"] = [  # 조건이 있으면 점수 증가
                {"match": {"description": condition}} for condition in conditions
            ]
        # 검색 요청
        try:
            response = self.es.search(index=self.index_name, body=query)
            if response["hits"]["hits"]:
                return [hit["_source"] for hit in response["hits"]["hits"]]
            else:
                return []
        except Exception as e:
            print(f"[Error] 검색 실패:: {e}")
            return []


    # 임베딩 기반 검색
    def search_image_embedding(self, embedding, top_k=3):
        """
        이미지 임베딩 기반으로 유사한 상품을 검색합니다.
        """
        # 유사도 검색 쿼리
        query = {
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'image_embedding')",
                        "params": {"query_vector": embedding},
                    },
                }
            },
            "size": top_k,
    }
    
        # 검색 요청
        try:
            response = self.es.search(index=self.index_name, body=query)
            hits = response["hits"]["hits"]

            # 유사도 필터링
            results = []
            for hit in hits:
                score = hit["_score"]  # 유사도 점수
                print("**2",score)
                if score >= 0.7:  # threshold
                    results.append(hit["_source"])
            if not results:
                print(f"비슷한 상품없음 ")
                return []
            return results
        except Exception as e:
            print(f"[Error] 검색 실패: {str(e)}")
            return []
        
    def search_filtered_products2(self, category, product_name, top_k=3):
        # Elasticsearch 쿼리 정의
        query = {
            "query": {
                "bool": {
                    "filter": [  # 필터 조건
                        {"term": {"category": category}}  # 카테고리를 제한
                    ],
                    "must": [  # 상품명에 "사과"가 포함된 상품
                    {
                        "wildcard": {
                            "product_name": f"*{product_name}*"  # "사과"가 포함된 모든 상품
                        }
                    }
                    ]
                }
            },
            "size": top_k,  # 상위 K개 결과 제한
            "sort": [{"_score": "desc"}],  # 높은 점수 순으로 정렬
            "_source": ["category", "image_url", "original_price", "discount_price", "product_name", "description"]  # 필요한 필드만 반환
        }

        # 검색 요청
        try:
            response = self.es.search(index=self.index_name, body=query)

            # hits 확인 및 데이터 추출
            if "hits" in response and "hits" in response["hits"]:
                return [hit["_source"] for hit in response["hits"]["hits"]]
            else:
                return []
        except Exception as e:
            print(f"[Error] 검색 실패: {e}")
            return []
