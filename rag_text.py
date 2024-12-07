import requests
from flask import jsonify
import re
import json
import pandas as pd
from db_connector import DBConnector
from image_processor import ImageProcessor


class RagHandler_text:
    # [1] 클래스 초기화
    def __init__(self):
        self.api_url = "app_url"
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
        ],
        self.db_connector = DBConnector()

    # [2] 사용자 메시지 및 대화내역 기반으로 제품 추천결과 생성 => LLM 사용1 : 질문에서 주요부분 추출
    def get_rag_response(self, message,history):
        """
        RAG 응답 생성 함수.
        - message: 사용자 텍스트 메시지
        - image: 이미지 파일 경로 (없으면 None)
        - history: 대화 히스토리
        - mode: 0 = 텍스트 검색, 1 = 이미지 검색
        """
        # 시스템 메시지를 포함한 기본 대화 설정
        utterances = [
            {
                "role": "ROLE_SYSTEM",
                "content": """
                Assume you are an Emart employee. Based on the customer’s messages in the history and the current message, 
                analyze each message to identify and extract key information about the primary product category, product name, 
                and specific conditions or preferences the user may have mentioned for the desired product. 
                If a message does not refer to a product, output it as \"notfound\". 
                Please provide a category for the product. The category must be one of the following: 과일, 채소, 수산물, 정육, 잡곡, 양념. Note: Tomatoes are classified as fruits.
                Provide your response in a structured JSON format for each message as follows: { "category": "카테고리명", "name": "상품명", "conditions": ["조건1", "조건2", ...] }
                If no product category or name is found in the message, output:"notfound"
                """,
            }
        ]

        # 히스토리 : 이전 대화내역 순회하며, 프롬프트에 순서대로 추가함, 대화의 문맥을 유지
        for msg in history:
            role = "ROLE_ASSISTANT" if msg.get("isBot") else "ROLE_USER"
            utterances.append({"role": role, "content": msg.get("content")})
        utterances.append({"role": "ROLE_USER", "content": message})

        # 마음GPT에 POST 요청 보낼 때 데이터 구조 설정 부분
        payload = {
            "app_id": self.models[1]["app_id"],  # 마음GPT 사용
            "name": self.models[1]["name"],
            "item": self.models[1]["item"],
            "param": [
                {
                    "utterances": utterances,  # 대화맥락 제공
                    "config": {  # AI 모델이 응답 생성시 사용하는 설정값
                        "top_p": 0.6,  # 샘플링 사용시의 확률값, 낮을수록 확실한 선택
                        "top_k": 1,  # 가장 가능성 높은 k개의 단어 고려
                        "temperature": 0.9,  # 모델의 출력 다양성 조절
                        "presence_penalty": 0.0,  # 이전 대화에서 단어 다시 사용되는 빈도
                        "frequency_penalty": 0.0,  # 특정 단어 반복되는 빈도
                        "repetition_penalty": 1.0,  # 반복된 단어, 구의 사용 억제
                    },
                }
            ],
        }
        headers = {"Content-Type": "application/json", "cache-control": "no-cache"}
        response = requests.post(self.api_url, json=payload, headers=headers)
        if response.status_code != 200:
            return {"error": "Failed to get response from MaumGPT API", "status": 500}

        response_text = response.content.decode(
            "utf-8"
        )  # 사람이 읽을 수 있도록 응답변경

        # 마음API의 응답처리 후 이를 기반으로 상품 추천 목록 구성 -> 다시 API 호출하여 사용자에게 최종응답 반환
        try:
            # 1. API 응답파싱
            dictionary = json.loads(response_text)
            text_data = json.loads(dictionary["text"])

            # Now you can access 'category', 'name', and 'conditions' from text_data
            category = text_data["category"]
            name = text_data["name"]
            conditions = text_data["conditions"]

            print("카테고리:", category)
            print("상품명:", name)
            print("조건:", conditions)

            search_results = self.db_connector.search_filtered_products(
                    category, name, conditions, top_k=3)
            
            if search_results == []:
                return {"reply": "매장에 해당 상품이 존재하지 않습니다.", "status": 500}

            # 결과 정리
            result_text = "### 추천 상품 목록 ###\n\n"
            rank = 1
            detailed_results = []
            for hit in search_results:  # 검색 결과의 실제 데이터 추출
                print("***hit:", hit,"*****\n")
                if rank == 1:
                    result_text += f"- 추천순위: {rank}\n"
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
                rank +=1
                
            # [4] 추천 상품 목록을 기반으로 응답 생성 => LLM 사용2 : 추천상품 기반으로 응답 생성
            #####################################
            utterances = [
                {
                    "role": "ROLE_SYSTEM",
                    "content": """
                Role: You are a professional Emart employee helping customers with product recommendations.

                Task: Summarize the product information into a response that is exactly 2 to 3 sentences long.  
                Rules:  
                1. Include only the product name, discounted price, and a short product description.  
                2. Do not repeat any information or include unnecessary details.  
                3. Ensure the response is concise, clear, and does not exceed 3 sentences.

                Output Format Example:  
                "The recommended product is [Product Name], priced at [Discounted Price]. [Product Description]."

                Example Input:  
                - Product Name: 햇사과 5~8입/봉 (1.3kg)  
                - Discount Price: 11500  
                - Original Price: 17900  
                - Description: 국내산 햇사과는 단단한 과육과 아삭한 식감이 일품이며, 달콤한 과육과 사각 사각한 식감이 매력적인 과일입니다.

                Expected Output:  
                "추천 상품은 햇사과 5~8입/봉 (1.3kg)이며, 할인가는 11,500원입니다. 국내산 햇사과는 단단한 과육과 아삭한 식감이 매력적인 과일입니다."

                Now process the following input and ensure the response follows this format and does not exceed 3 sentences:

                """,
                }
            ]

            # 현재 사용자 메시지 추가
            utterances.append(
                {"role": "ROLE_USER", "content": result_text}
            )  # 상품목록 삽입

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

            headers = {"Content-Type": "application/json", "cache-control": "no-cache"}
            response = requests.post(self.api_url, json=payload, headers=headers)
            if response.status_code != 200:
                return {"reply": "오류가 발생했습니다. 다시 시도해주세요.", "status": 500}

            response_json = response.json()
            response_text = response_json.get("text", "")

            return {"reply": response_text, 
                     "detailed_results": detailed_results,
                     "status": 200}
        
        # 에러처리
        except json.JSONDecodeError as e:
            print(f"JSON 디코딩 오류: {e}")
            return {"reply": "오류가 발생했습니다. 다시 시도해주세요.", "status": 200}
