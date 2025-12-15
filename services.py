"""
심리 상담 챗봇 + 도서 추천 시스템
비즈니스 로직 구현
"""

from typing import List
import anthropic
import json
import requests
from models import PsychologicalSummary, BookRecommendation
from config import ANTHROPIC_API_KEY, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET

# ============================================================================
# 1. 심리 상담 챗봇 핵심 로직
# ============================================================================

class PsychologyChatbot:
    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        return """당신은 따뜻하고 공감적인 심리 상담사입니다.

## 핵심 역할

1. **경청 (Active Listening)**
   - 사용자의 감정을 반영하고 검증
   - "~하게 느끼시는군요", "힘드셨겠어요"
   - 비판단적 수용

2. **탐색 (Gentle Exploration)**
   - 부드럽고 개방적인 질문
   - "그 상황에서 어떤 감정을 느꼈나요?"
   - "구체적으로 어떤 점이 가장 힘드셨나요?"
   - "그때 어떤 생각이 들었나요?"

3. **지지 (Supportive Presence)**
   - 따뜻한 격려
   - 강점과 자원 찾기
   - 작은 변화 인정

## 중요: 하지 말아야 할 것

- ❌ 복잡한 심리학 이론 설명
- ❌ 즉각적인 해결책 제시
- ❌ 분석이나 진단
- ❌ 긴 설명

## 응답 스타일

- 짧고 따뜻하게 (2-4문장)
- 감정 중심
- 자연스러운 대화 흐름
- 필요시 하나의 탐색 질문

충분한 대화 후 분석은 별도로 진행됩니다. 지금은 사용자의 이야기를 듣는 데 집중하세요."""

    def chat(self, messages: List[dict]) -> str:
        """사용자와 대화"""
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=self.system_prompt,
            messages=messages
        )
        return response.content[0].text


# ============================================================================
# 2. 상담 내용 요약 및 분석
# ============================================================================

class CounselingAnalyzer:
    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.analysis_tools = self._create_analysis_tools()
    
    def _create_analysis_tools(self) -> List[dict]:
        """SKILL.md 기반 6단계 분석 도구"""
        return [
            {
                "name": "define_psychological_phenomenon",
                "description": "Step 1: 심리학적 현상을 명확히 정의 (SKILL.md 1단계)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "behavior_pattern": {
                            "type": "string",
                            "description": "관찰되는 행동이나 사고 패턴"
                        },
                        "context": {
                            "type": "string",
                            "description": "상황적 맥락 (누가, 언제, 어디서, 어떤 상황)"
                        },
                        "level_of_analysis": {
                            "type": "string",
                            "enum": ["individual", "interpersonal", "group"],
                            "description": "분석 수준"
                        },
                        "relevant_domains": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["cognitive", "social", "clinical", "developmental"]
                            },
                            "description": "관련 심리학 영역"
                        }
                    },
                    "required": ["behavior_pattern", "context", "level_of_analysis"]
                }
            },
            {
                "name": "apply_psychological_theories",
                "description": "Step 3: 관련 심리학 이론 적용 (SKILL.md 3단계)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cognitive_theories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "인지심리학 이론 (예: Dual-process, 편향)"
                        },
                        "social_theories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "사회심리학 이론 (예: 귀인, 동조)"
                        },
                        "clinical_frameworks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "임상 프레임워크 (예: CBT, Stress-Coping)"
                        },
                        "proposed_mechanisms": {
                            "type": "string",
                            "description": "이론이 제안하는 심리적 메커니즘"
                        }
                    },
                    "required": ["proposed_mechanisms"]
                }
            },
            {
                "name": "analyze_cognitive_processes",
                "description": "Step 4: 인지 과정 분석 - 편향, 휴리스틱, 정보처리 (SKILL.md 4단계)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cognitive_biases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "확인된 인지 편향 (확증편향, 가용성 휴리스틱 등)"
                        },
                        "thinking_patterns": {
                            "type": "string",
                            "description": "사고 패턴 분석 (자동적 사고, 인지 왜곡)"
                        },
                        "decision_making": {
                            "type": "string",
                            "description": "의사결정 과정 분석 (System 1/2)"
                        },
                        "information_processing": {
                            "type": "string",
                            "description": "정보처리 방식 (주의, 기억, 판단)"
                        }
                    },
                    "required": ["thinking_patterns"]
                }
            },
            {
                "name": "examine_emotional_motivational",
                "description": "Step 5: 감정 및 동기 요인 검토 (SKILL.md 5단계)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "primary_emotions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "주요 감정 상태"
                        },
                        "emotional_regulation": {
                            "type": "string",
                            "description": "감정 조절 방식 및 효과성"
                        },
                        "motivations": {
                            "type": "string",
                            "description": "행동을 이끄는 동기 (자율성, 역량, 관계성)"
                        },
                        "needs_assessment": {
                            "type": "string",
                            "description": "충족/좌절된 심리적 욕구 (Maslow, SDT)"
                        }
                    },
                    "required": ["primary_emotions", "motivations"]
                }
            },
            {
                "name": "assess_social_situational",
                "description": "Step 6: 사회적 및 상황적 영향 평가 (SKILL.md 6단계)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "situational_forces": {
                            "type": "string",
                            "description": "상황의 힘 (권위, 규범, 역할)"
                        },
                        "social_influences": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "사회적 영향 (동조, 복종, 설득)"
                        },
                        "group_dynamics": {
                            "type": "string",
                            "description": "집단 역학 (집단사고, 사회적 촉진)"
                        },
                        "person_situation_interaction": {
                            "type": "string",
                            "description": "개인-상황 상호작용 분석"
                        }
                    },
                    "required": ["situational_forces", "person_situation_interaction"]
                }
            },
            {
                "name": "evaluate_mental_health_dimensions",
                "description": "Step 8: 정신건강 차원 평가 (SKILL.md 8단계)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "distress_level": {
                            "type": "string",
                            "enum": ["minimal", "mild", "moderate", "severe"],
                            "description": "고통 수준"
                        },
                        "functioning_impact": {
                            "type": "string",
                            "description": "일상 기능에 미치는 영향"
                        },
                        "risk_factors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "위험 요인 (취약성)"
                        },
                        "protective_factors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "보호 요인 (회복탄력성)"
                        },
                        "clinical_considerations": {
                            "type": "string",
                            "description": "임상적 고려사항 (정상 vs 병리적)"
                        }
                    },
                    "required": ["distress_level", "functioning_impact", "clinical_considerations"]
                }
            }
        ]
    
    def _format_conversation(self, messages: List[dict]) -> str:
        """대화를 텍스트로 포맷팅"""
        return "\n\n".join([
            f"{'사용자' if m['role'] == 'user' else '상담사'}: {m['content']}"
            for m in messages if m['role'] != 'system'
        ])
    
    def analyze_conversation(self, messages: List[dict]) -> PsychologicalSummary:
        """
        Tool Calling을 활용한 체계적 6단계 분석
        """
        conversation_text = self._format_conversation(messages)
        
        # Phase 1: 초기 분석 + Tool Calling
        analysis_prompt = f"""당신은 심리학 전문 분석가입니다. SKILL.md의 체계적 분석 프레임워크를 사용하여 다음 상담 대화를 분석하세요.

## 분석 프로세스 (6단계)

1. define_psychological_phenomenon: 현상 정의
2. apply_psychological_theories: 이론 적용
3. analyze_cognitive_processes: 인지 분석
4. examine_emotional_motivational: 감정/동기 분석
5. assess_social_situational: 사회/상황 분석
6. evaluate_mental_health_dimensions: 정신건강 평가

각 단계별 도구를 순차적으로 호출하여 체계적으로 분석하세요.

=== 상담 대화 ===
{conversation_text}
"""
        
        messages_for_analysis = [{"role": "user", "content": analysis_prompt}]
        
        # Tool Calling Loop
        tool_use_results = {}
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                tools=self.analysis_tools,
                messages=messages_for_analysis
            )
            
            # Tool 호출이 없으면 종료
            if response.stop_reason != "tool_use":
                break
            
            # Tool 실행 및 결과 수집
            tool_results_for_claude = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    
                    # 결과 저장
                    tool_use_results[tool_name] = tool_input
                    
                    # Claude에게 반환할 결과
                    tool_results_for_claude.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": json.dumps({
                            "status": "success",
                            "note": f"{tool_name} 분석 완료"
                        }, ensure_ascii=False)
                    })
            
            # 다음 반복을 위한 메시지 추가
            messages_for_analysis.append({
                "role": "assistant",
                "content": response.content
            })
            messages_for_analysis.append({
                "role": "user",
                "content": tool_results_for_claude
            })
            
            iteration += 1
        
        # Phase 2: 통합 분석 및 PsychologicalSummary 생성
        synthesis_prompt = """모든 분석 도구 실행이 완료되었습니다. 

다음 형식의 JSON으로 최종 요약을 생성하세요:

{
  "main_concerns": ["주요 고민 1", "주요 고민 2"],
  "emotions": ["감정 1", "감정 2"],
  "cognitive_patterns": ["인지 패턴 1", "인지 패턴 2"],
  "recommendations": ["권장사항 1", "권장사항 2"],
  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"]
}

분석 도구 결과를 통합하여 작성하세요. 
keywords는 도서 검색에 사용할 키워드로, 심리학 용어와 일반적인 단어를 균형있게 5-8개 포함하세요.
오직 JSON만 출력하세요."""
        
        final_response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=messages_for_analysis + [{
                "role": "user",
                "content": synthesis_prompt
            }]
        )
        
        # JSON 파싱
        response_text = final_response.content[0].text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        summary_data = json.loads(response_text)
        return PsychologicalSummary(**summary_data)


# ============================================================================
# 3. 도서 검색 및 추천 (네이버 API 직접 호출)
# ============================================================================

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
                print(f"✅ 네이버 API 호출 성공: {keyword} ({len(items)}권)")
                return items
            else:
                print(f"❌ 네이버 API 오류 ({keyword}): HTTP {response.status_code}")
                return []
                
        except Exception as api_error:
            print(f"❌ 네이버 API 호출 실패 ({keyword}): {type(api_error).__name__}: {str(api_error)}")
            return []
    
    async def recommend_books(
        self, 
        summary: PsychologicalSummary, 
        max_books: int = 5
    ) -> List[BookRecommendation]:
        """심리 분석 결과를 바탕으로 도서 추천"""
        
        all_books = []
        
        # 각 키워드로 책 검색 (더 많은 키워드 사용)
        # 심리학 용어에는 "심리" 접두사 추가, 일반적인 단어는 그대로 검색
        for keyword in summary.keywords[:5]:  # 상위 5개 키워드 사용
            # 심리학 전문 용어인지 일반적인 단어인지 판단
            # 일반적인 단어(직장, 관계, 스트레스, 감정 등)는 그대로, 전문 용어는 "심리" 접두사 추가
            search_query = keyword
            # 전문 용어 패턴 체크 (예: "치료", "치유", "인지", "행동" 등이 포함된 경우)
            if any(term in keyword for term in ["치료", "치유", "인지", "행동", "트라우마", "불안", "우울"]):
                search_query = f"심리 {keyword}"
            else:
                # 일반적인 단어는 그대로 검색하되, 필요시 "자기계발" 또는 "심리" 추가
                search_query = keyword
            
            books = await self.search_books_via_api(search_query, display=5)
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

