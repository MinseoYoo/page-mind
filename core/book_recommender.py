"""
도서 검색 및 추천 (네이버 API 직접 호출)
"""

from typing import List
import anthropic
import json
import requests
from models import PsychologicalSummary, BookRecommendation
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET


class BookRecommender:
    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
    
    async def search_books_via_api(self, keyword: str, display: int = 10) -> List[dict]:
        """네이버 API를 직접 호출하여 책 검색"""
        try:
            url = "https://openapi.naver.com/v1/search/book.json"
            headers = {
                "X-Naver-Client-Id": NAVER_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
            }
            params = {
                "query": keyword,
                "display": min(display, 100),  # 최대 100개
                "sort": "sim"  # 정확도순
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                print(f"네이버 API 호출 성공: {keyword} ({len(items)}권)")
                return items
            else:
                print(f"네이버 API 오류 ({keyword}): HTTP {response.status_code}")
                return []
                
        except Exception as api_error:
            print(f"네이버 API 호출 실패 ({keyword}): {type(api_error).__name__}: {str(api_error)}")
            return []
    
    async def recommend_books(
        self, 
        summary: PsychologicalSummary, 
        max_books: int = 5
    ) -> List[BookRecommendation]:
        """심리 분석 결과를 바탕으로 도서 추천"""
        
        all_books = []
        
        # 각 키워드로 책 검색
        for keyword in summary.keywords[:5]:  # 상위 5개 키워드 사용
            books = await self.search_books_via_api(keyword, display=5)
            all_books.extend(books)
        
        # 중복 제거 (ISBN 기준)
        unique_books = {book['isbn']: book for book in all_books if book.get('isbn')}.values()
        
        if not unique_books:
            return []
        
        # Claude에게 가장 적합한 책 선택 요청
        book_selection_prompt = f"""다음은 사용자의 심리 상담 요약입니다:

주요 고민: {', '.join(summary.main_concerns)}
감정 상태: {', '.join(summary.emotions)}
인지 패턴: {', '.join(summary.cognitive_patterns)}
제안된 전략: {', '.join(summary.recommendations)}

다음 도서 목록에서 가장 도움이 될 {max_books}권을 선택하고, 각 책이 왜 도움이 되는지 설명해주세요:

{json.dumps([{"title": b.get("title", ""), "author": b.get("author", ""), "description": b.get("description", ""), "isbn": b.get("isbn", "")} for b in list(unique_books)[:15]], ensure_ascii=False, indent=2)}

다음 JSON 형식으로만 응답하세요:
{{
  "selected_books": [
    {{
      "isbn": "ISBN코드",
      "relevance_reason": "이 책이 도움이 되는 구체적인 이유 (2-3문장)"
    }}
  ]
}}"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": book_selection_prompt}]
        )
        
        # JSON 파싱
        response_text = response.content[0].text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        selection_data = json.loads(response_text)
        
        # 선택된 책 정보 매핑
        isbn_to_book = {book['isbn']: book for book in unique_books}
        
        recommendations = []
        for selected in selection_data['selected_books'][:max_books]:
            isbn = selected['isbn']
            if isbn in isbn_to_book:
                book = isbn_to_book[isbn]
                recommendations.append(BookRecommendation(
                    title=book.get('title', '').replace('<b>', '').replace('</b>', ''),
                    author=book.get('author', '').replace('<b>', '').replace('</b>', ''),
                    publisher=book.get('publisher', ''),
                    description=book.get('description', '').replace('<b>', '').replace('</b>', ''),
                    isbn=isbn,
                    cover_image=book.get('image', ''),
                    link=book.get('link', ''),
                    relevance_reason=selected['relevance_reason']
                ))
        
        return recommendations

