import requests
from flask import jsonify
import re
import json
import pandas as pd
from db_connector import DBConnector
from image_processor import ImageProcessor


class RagHandler_img:
    # [1] 클래스 초기화
    def __init__(self):
        self.api_url = "api_url"
        self.models = [
            {
                "app_id": "app_id",
                "name": "name",
                "item": ["item"],
            },
            {
                "app_id": "app_id",
                "name": "name",
                "item": ["item"],
            },
        ]
        self.db_connector = DBConnector()

    # [2] 사용자 메시지 및 대화내역 기반으로 제품 추천결과 생성 => LLM 사용1 : 질문에서 주요부분 추출
    def get_rag_response(self, image_path):
        try:
            # 이미지 임베딩 생성
            image_processor = ImageProcessor()
            embedding = image_processor.process_image(image_path)
            if embedding is None:
                return {"reply": "이미지 처리 중 오류가 발생했습니다.", "status": 500}

            # 이미지 임베딩을 사용하여 검색
            search_results = self.db_connector.search_image_embedding(embedding, top_k=3)

            # 검색 결과가 없는 경우 처리
            if not search_results:
                return {"reply": "추천할 상품이 없습니다. 다른 이미지를 시도해보세요.", "status": 200}

            # 결과 정리
            result_text = "### 추천 상품 목록 ###\n\n"
            rank = 1
            detailed_results = []
            for hit in search_results:
                if rank == 1:
                    result_text += f"- 추천순위: {rank}\n"
                    search_text = f"{hit['product_name']}"
                    result_text += f"  - 상품명: {hit['product_name']}\n"
                    result_text += f"  - 할인가: {hit['discount_price']}\n"
                    result_text += f"  - 원래 가격: {hit['original_price']}\n"
                    result_text += f"  - 설명: {hit['description']}\n\n"
                    result_text += "#########################\n\n"
                    detailed_results.append({
                        "rank": rank,
                        "product_name": hit["product_name"],
                        "discount_price": hit["discount_price"],
                        "original_price": hit["original_price"],
                        "image_url": hit["image_url"]
                    })
                    rank+=1
                else:
                    break
            print("resulttext",result_text)
            print("searchtext",search_text)

            # 시스템 메시지를 포함한 기본 대화 설정
            utterances = [
                {
                    "role": "ROLE_SYSTEM",
                    "content": """
                    Extract what the product is from the product name.
                    Identify and extract the main product from the product name, strictly in one word. 
                    For example: '저탄소 알뜰사과(부사) 1kg 5~6입/봉' -> '사과'
                    Please provide a category for the product. The category must be one of the following: 과일, 채소, 수산물, 정육, 잡곡, 양념. Note: Tomatoes are classified as fruits.
                    Provide your response in a structured JSON format for each message as follows: { "category": "카테고리명", "name": "상품명"}
                    Ensure all outputs are in Korean.

                    """,
                }
            ]

            # 마음GPT에 POST 요청
            payload = {
                "app_id": self.models[1]["app_id"],
                "name": self.models[1]["name"],
                "item": self.models[1]["item"],
                "param": [
                    {
                        "utterances": utterances,
                        "config": {
                            "top_p": 0.6,
                            "top_k": 1,
                            "temperature": 0.9,
                            "presence_penalty": 0.0,
                            "frequency_penalty": 0.0,
                            "repetition_penalty": 1.0,
                        },
                    }
                ],
            }

            # 현재 사용자 메시지 추가
            utterances.append(
                {"role": "ROLE_USER", "content": search_text}
            )  # 상품목록 삽입

            headers = {"Content-Type": "application/json", "cache-control": "no-cache"}
            # 요청 후 응답 처리
            response = requests.post(self.api_url, json=payload, headers=headers)
            if response.status_code != 200:
                return {"error": "Failed to get response from MaumGPT API", "status": 500}
            response_text = response.content.decode(
            "utf-8"
            )

            # JSON 응답 파싱
            try:
                dictionary = json.loads(response_text)
                text_data = json.loads(dictionary["text"])

                # Now you can access 'category', 'name', and 'conditions' from text_data
                category = text_data["category"]
                name = text_data["name"]

                print("카테고리:", category)
                print("상품명:", name)

                if not name:
                    return {"reply": "추천할 상품 이름을 추출하지 못했습니다.", "status": 500}

            except json.JSONDecodeError as e:
                print(f"JSON 디코딩 오류: {e}")
                return {"reply": "응답 데이터 형식 오류", "status": 500}

            # 필터링된 상품 검색 (2,3순위 찾기)
            search_results = self.db_connector.search_filtered_products2(category,name, top_k=2)

            for hit in search_results:
                detailed_results.append({  # 2,3순위 입력
                    "rank": rank,
                    "product_name": hit["product_name"],
                    "discount_price": hit["discount_price"],
                    "original_price": hit["original_price"],
                    "image_url": hit["image_url"]
                })
                rank += 1

            # 추천 상품 목록을 기반으로 응답 생성
            utterances = [
                {
                    "role": "ROLE_SYSTEM",
                    "content": """
                    Role: You are a friendly and professional Emart employee, helping customers with product recommendations.
                    Task:
                    1. Ignore any repeated or unnecessary information.
                    2. Create a concise response in the following format:
                    "The recommended product is [Product Name], priced at [Price or Discounted Price]. If the product is on sale, mention that it is discounted. This product is [Product Description]."
                    3. Ensure the output is:
                    Written in Korean.
                    Clear, professional, and free from unnecessary symbols or formatting.
                    Limited to two to three sentences only.
                    """,
                },
                {"role": "ROLE_USER", "content": result_text}, # 1순위 응답
            ]
            payload["param"][0]["utterances"] = utterances
            response = requests.post(self.api_url, json=payload, headers=headers)

            if response.status_code != 200:
                return {"reply": "오류가 발생했습니다. 다시 시도해주세요.", "status": 500}

            response_text = response.json().get("text", "")
            return {"reply": response_text, "detailed_results": detailed_results, "status": 200}

        except json.JSONDecodeError as e:
            print(f"JSON 디코딩 오류: {e}")
            return {"reply": "오류가 발생했습니다. 다시 시도해주세요.", "status": 500}
