from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

# ChromeDriver 설정 및 브라우저 열기
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
driver.set_page_load_timeout(30)  # 페이지 로드 대기 시간 설정 (초)

# 전체 상품 데이터를 저장할 리스트
product_data = []

# 카테고리 ID 범위 설정
category_ids = range(6000213119, 6000213167)  # 6000213119부터 6000213166까지 번호 선택 

try:
    for category_id in category_ids:
        # 각 카테고리 페이지 URL 설정
        category_url = f"url"  # 크롤링주소 입력
        driver.get(category_url)

        # 카테고리 페이지 로드 및 상품 리스트 로딩 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.mnemitem_grid_item"))
        )

        # 각 상품의 <a> 태그에서 링크 추출
        items = driver.find_elements(By.CSS_SELECTOR, "li.mnemitem_grid_item a.mnemitem_thmb_link.clickable")
        product_links = [item.get_attribute("href") for item in items]

        # 각 상품 페이지에서 정보 추출
        for link in product_links:
            driver.get(link)
            time.sleep(2)  # 페이지 로딩 대기

            # 상품 정보 저장용 딕셔너리
            product_info = {}

            # 1. 상품 이미지 URL 추출
            try:
                product_info["이미지 URL"] = driver.find_element(By.XPATH, '//*[@id="mainImg"]').get_attribute("src")
            except:
                product_info["이미지 URL"] = None

            # 2. 상품 브랜드명 추출
            try:
                brand_name_element = driver.find_element(By.XPATH, '//*[@id="content"]/div[2]/div[1]/div[2]/div[2]/h2/span/div/div[1]/a')
                product_info["브랜드명"] = brand_name_element.text
            except:
                try:
                    brand_name_element = driver.find_element(By.XPATH, '//*[@id="content"]/div[2]/div[1]/div[2]/div[2]/span/div/span')
                    product_info["브랜드명"] = brand_name_element.text
                except:
                    product_info["브랜드명"] = None

            # 3. 상품명 추출
            try:
                product_info["상품명"] = driver.find_element(By.XPATH, '//*[@id="content"]/div[2]/div[1]/div[2]/div[2]/h2/span/span').text
            except:
                product_info["상품명"] = None

            # 4. 가격 정보 추출
            try:
                discounted_price = driver.find_element(By.XPATH, '//*[@id="content"]/div[2]/div[1]/div[2]/div[4]/div[2]/div/span[1]/em').text
                product_info["할인가"] = discounted_price
            except:
                product_info["할인가"] = None

            try:
                original_price = driver.find_element(By.XPATH, '//*[@id="content"]/div[2]/div[1]/div[2]/div[4]/div[2]/div/span[2]/em').text
                product_info["원래 가격"] = original_price
            except:
                product_info["원래 가격"] = None

            # 5. 상품 설명 추출
            try:
                # iFrame으로 전환
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.cdtl_capture_img iframe"))
                )
                iframe_element = driver.find_element(By.CSS_SELECTOR, "div.cdtl_capture_img iframe")
                driver.switch_to.frame(iframe_element)

                # 제목 텍스트 추출
                try:
                    product_info["제목"] = driver.find_element(By.CSS_SELECTOR, ".tmpl_imgcont_desc_tit").text
                except:
                    product_info["제목"] = None

                # 설명 텍스트 추출
                try:
                    product_info["설명"] = driver.find_element(By.CSS_SELECTOR, ".tmpl_imgcont_desc_txt").text
                except:
                    product_info["설명"] = None

                # 이미지 URL 및 OCR 텍스트 추출 (설명이 없는 경우 추가)
                if product_info["제목"] is None and product_info["설명"] is None:
                    image_elements = driver.find_elements(By.CSS_SELECTOR, "#descContents img")
                    
                    # 이미지 URL과 OCR 텍스트 추출
                    image_data = []
                    for img in image_elements:
                        img_url = img.get_attribute("src")
                        ocr_text = img.get_attribute("alt")  # OCR 텍스트는 alt 속성에 저장될 수 있음
                        image_data.append({"url": img_url, "ocr_text": ocr_text})

                    product_info["이미지 정보"] = image_data  # 이미지 정보 추가

                # iFrame에서 메인 페이지로 다시 전환
                driver.switch_to.default_content()
            except Exception as e:
                print("오류 발생:", e)

            # 추출한 정보를 리스트에 추가
            product_data.append(product_info)

            # 상품 정보를 콘솔에 출력
            print(product_info)

finally:
    # 브라우저 닫기
    driver.quit()

# 모든 상품 데이터를 DataFrame으로 변환
df = pd.DataFrame(product_data)

# CSV 파일로 저장
df.to_csv("product_data_multiple_categories.csv", index=False, encoding="utf-8-sig")
