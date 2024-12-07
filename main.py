from stt import perform_stt
from tts import perform_tts
from rag_img import RagHandler_img
from rag_text import RagHandler_text
from image_processor import ImageProcessor  # 이미지 처리 함수 추가
import os

# 텍스트
def process_audio_file(audio_file_path):
    # 1. STT 수행
    stt_result = perform_stt(audio_file_path)
    if stt_result is None:
        print("STT 처리 실패")
        return
    print(f"STT 결과: {stt_result}")

    # 2. RAG 수행
    history = []  # 예시를 위해 빈 히스토리 사용
    rag_text = RagHandler_text()
    rag_result = rag_text.get_rag_response(stt_result,history)
    if isinstance(rag_result, tuple):  # 오류 시 튜플 반환
        print("RAG 처리 실패")
        return

    response_text = rag_result["reply"]
    print(f"RAG 결과: {response_text}")

    # 3. TTS 수행
    tts_result = perform_tts(response_text)
    if tts_result is None:
        print("TTS 처리 실패")
        return

    print(f"TTS 오디오 파일이 '{tts_result}'에 저장되었습니다.")


# 이미지 
def process_image_file(image_file_path):
    # 1. RAG 수행
    history = []  # 예시를 위해 빈 히스토리 사용
    rag_img = RagHandler_img()
    rag_result = rag_img.get_rag_response(image_file_path)
    if isinstance(rag_result, tuple):  # 오류 시 튜플 반환
        print("RAG 처리 실패")
        return

    response_text = rag_result["reply"]
    print(f"RAG 결과: {response_text}")

    # 2. TTS 수행
    tts_result = perform_tts(response_text)
    if tts_result is None:
        print("TTS 처리 실패")
        return

    print(f"TTS 오디오 파일이 '{tts_result}'에 저장되었습니다.")


# 파일 확장자 확인 함수
def is_audio_file(file_path):
    audio_extensions = {".wav", ".mp3", ".aac", ".ogg", ".flac"}
    return any(file_path.lower().endswith(ext) for ext in audio_extensions)

def is_image_file(file_path):
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
    return any(file_path.lower().endswith(ext) for ext in image_extensions)


# 메인 함수
if __name__ == "__main__":
    # 파일 경로 설정
    file_path = "apple_audio.wav"  # Apple.jpg, apple_audio.wav


    if not os.path.exists(file_path):
        print(f"파일 '{file_path}'이(가) 존재하지 않습니다.")
    elif is_audio_file(file_path):
        print("오디오 파일이 감지되었습니다.")
        process_audio_file(file_path)
    elif is_image_file(file_path):
        print("이미지 파일이 감지되었습니다.")
        process_image_file(file_path)
    else:
        print("지원되지 않는 파일 형식입니다.")