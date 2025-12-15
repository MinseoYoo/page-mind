"""
상담 내용 요약 및 분석
"""

from typing import List
import anthropic
import json
from models import PsychologicalSummary


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
keywords는 도서 검색에 사용할 키워드로, 사용자의 상태, 감정, 상황을 나타내는 일상적인 용어를 5-8개 포함하세요.
심리학 전문 용어(예: 인지왜곡, 투사, 억압)보다는 일반인이 이해하기 쉬운 표현(예: 외로움, 자존감, 직장스트레스, 인간관계)을 사용하세요.
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

