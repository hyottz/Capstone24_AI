import base64
import os
from flask_cors import CORS  # CORS 모듈 추가
from flask import Flask, request, jsonify
from rag_img import RagHandler_img
from rag_text import RagHandler_text
from image_processor import ImageProcessor  # 이미지 처리 함수 추가
from io import BytesIO

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        # "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 업로드 폴더 설정
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 1. 오디오
@app.route('/process_text', methods=['POST'])
def process_text():
    try:
        # 요청 데이터 확인
        data = request.get_json()
        print(f"요청 데이터: {data}")  # 요청 데이터 디버깅

        text = data.get("text", "")
        if not text:
            return jsonify({"error": "텍스트 입력이 필요합니다."}), 400

        # 질문 유형 분류 함수
        def classify_question(question: str) -> str:
            if any(keyword in question for keyword in ["상품", "가격", "설명", "구매", "추천","찾아","알려줘",]):
                return "product"
            return "non_product"

        # 질문 유형 확인
        question_type = classify_question(text)

        if question_type == "product":
            history = []
            rag_text = RagHandler_text()

            try:
                # RAG 응답 처리
                rag_result = rag_text.get_rag_response(text, history)
                print(f"RAG 결과: {rag_result}")  # RAG 결과 디버깅
                
                if isinstance(rag_result, dict):
                    response_text = rag_result.get("reply", "응답 데이터 없음")
                    detailed_results = rag_result.get("detailed_results", [])
                else:
                    response_text = "RAG에서 비정상 데이터를 반환했습니다."
                    detailed_results = []
                
                print(f"응답 텍스트: {response_text}")
                print(f"세부 결과: {detailed_results}")
                
                # JSON 응답
                return jsonify({"reply": response_text, "detailed_results": detailed_results}), 200
            
            except Exception as e:
                print(f"RAG 처리 중 오류: {str(e)}")
                return jsonify({"reply": f"RAG 처리 중 오류: {str(e)}"}), 500
        
        else:
            # 비상품 질문 처리
            response_text = "찾고자 하는 상품을 말씀해주세요. (예시 : 맛있는 사과를 추천해주세요!)"
            return jsonify({"reply": response_text}), 200

    except Exception as e:
        # 서버 오류 처리
        print(f"서버 내부 오류: {str(e)}")
        return jsonify({"error": f"처리 중 오류 발생: {str(e)}"}), 500


# 2. 이미지
@app.route('/process_image', methods=['POST'])
def process_image():
    data = request.get_json()
    base64_image = data.get('image') 
    if not base64_image:
        return jsonify({"error": "이미지 입력이 없습니다."}), 400

    try:
        # Base64 데이터를 디코딩하여 메모리에서 처리
        image_data = base64.b64decode(base64_image)
        image_stream = BytesIO(image_data)  # BytesIO 객체 생성 (파일처럼 동작)

        # Image RAG 사용
        rag_img = RagHandler_img()
        rag_result = rag_img.get_rag_response(image_stream)
        
        # RAG 응답에서 텍스트 추출
        if isinstance(rag_result, dict):
            response_text = rag_result.get("reply", "응답 데이터 없음")
            detailed_results = rag_result.get("detailed_results", {})
        else:
            response_text = "RAG에서 비정상 데이터를 반환했습니다."
            detailed_results = {}

        print(f"응답 텍스트: {response_text}")
        print(f"세부 결과: {detailed_results}")

        # 프론트엔드에 JSON 응답으로 전달
        return jsonify({"reply": response_text, "detailed_results": detailed_results}), 200


    except Exception as e:
        print(f"처리 중 오류 발생: {str(e)}")
        return jsonify({"error": f"처리 중 오류 발생: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=2000, debug=True)   # 로컬로 테스트