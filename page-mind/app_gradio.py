"""
Gradio 웹 데모 - 심리 상담 챗봇 + 도서 추천
단일 탭 구성, AI가 충분한 정보를 수집했다고 판단하면 자동 분석 및 추천
CrewAI 공식 구조 사용
"""

import sys
import platform
import asyncio

import gradio as gr
from datetime import datetime
from typing import List, Tuple, Dict, Any
import json
import os

from dotenv import load_dotenv
load_dotenv()

# 새로운 CrewAI 구조 사용
import sys
project_root = os.path.abspath(os.path.dirname(__file__))
pagemind_path = os.path.join(project_root, 'pagemind', 'src')
if pagemind_path not in sys.path:
    sys.path.insert(0, pagemind_path)

from pagemind.crew import Pagemind
from pagemind.models import PsychologicalSummary, BookRecommendation
from pagemind.book_reranker import rerank_books, format_book_for_recommendation
from crewai import Crew, Process

# Crew 인스턴스 생성
crew_instance = Pagemind()

# 대화 저장소 및 분석 상태 추적
conversation_history = []
analysis_done = False  # 분석이 이미 수행되었는지 추적
current_summary = None  # 현재 분석 결과 저장
books_recommended = False  # 책 추천이 완료되었는지 추적


def count_assistant_messages(history: List) -> int:
    """히스토리에서 assistant 메시지 개수 세기"""
    count = 0
    if history:
        for msg in history:
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                count += 1
            elif isinstance(msg, tuple) and len(msg) == 2:
                # 튜플 형식인 경우 (하위 호환성)
                count += 1
    return count


def clean_message(msg: dict) -> dict:
    """
    메시지에서 role과 content만 추출 (Anthropic API 호환)
    Gradio가 추가하는 metadata 등 불필요한 필드 제거
    """
    return {
        "role": msg.get("role", "user"),
        "content": msg.get("content", "")
    }


def format_analysis_only(summary: PsychologicalSummary) -> str:
    """심리 분석 결과만 채팅 메시지 형식으로 포맷팅 (책 추천 없음)"""
    result = "## 📊 심리 분석 결과\n\n"
    
    result += "### 🎯 주요 고민\n"
    for concern in summary.main_concerns:
        result += f"- {concern}\n"
    result += "\n"
    
    result += "### 💭 감정 상태\n"
    for emotion in summary.emotions:
        result += f"- {emotion}\n"
    result += "\n"
    
    result += "### 🧠 인지 패턴\n"
    for pattern in summary.cognitive_patterns:
        result += f"- {pattern}\n"
    result += "\n"
    
    result += "### 💡 권장 전략\n"
    for rec in summary.recommendations:
        result += f"- {rec}\n"
    result += "\n"
    
    result += f"### 🔍 추출된 키워드\n{', '.join(summary.keywords)}\n\n"
    
    # 책 추천 제안 메시지 추가
    result += "---\n\n"
    result += "충분한 상담이 끝난 것 같은데 책을 추천해드릴까요?"
    
    return result


def format_analysis_and_recommendation(summary: PsychologicalSummary, books: List[BookRecommendation]) -> str:
    """심리 분석 결과와 책 추천을 함께 포맷팅"""
    result = format_analysis_only(summary)
    result = result.replace("충분한 상담이 끝난 것 같은데 책을 추천해드릴까요?", "")
    result += "\n\n" + format_books_recommendation(books, summary)
    return result


def detect_counseling_end(response: str) -> bool:
    """상담 종료 멘트 감지"""
    end_phrases = [
        "오늘 대화를 통해",
        "앞으로도 힘내시길",
        "필요하시면 언제든",
        "다시 찾아주세요",
        "상담을 마무리",
        "도움이 되었기를",
        "건강하시길",
        "행복하시길"
    ]
    response_lower = response.lower()
    return any(phrase in response_lower for phrase in end_phrases)


def add_analysis_button_to_message(message: str) -> str:
    """메시지에 분석/추천 또는 추가 대화 선택 버튼 추가 (HTML)"""
    button_html = """
<div style="margin-top: 15px; padding: 15px; background-color: #f0f4ff; border-radius: 8px; border: 2px solid #4a90e2;">
    <p style="margin: 0 0 10px 0; font-weight: bold; color: #2c3e50;">📊 다음 행동을 선택해주세요</p>
    <p style="margin: 0 0 15px 0; color: #555; font-size: 0.9em;">심리 분석 및 맞춤 도서 추천을 받거나, 조금 더 대화를 이어갈 수 있습니다.</p>
    <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
        <span class="analysis-choice" data-action="analyze" style="display: inline-block; padding: 12px 18px; background-color: #4a90e2; color: white; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 0.95em; user-select: none; transition: background-color 0.3s;">🔍 분석과 책 추천을 원해요</span>
        <span class="analysis-choice" data-action="chat_more" style="display: inline-block; padding: 12px 18px; background-color: #6c7a89; color: white; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 0.95em; user-select: none; transition: background-color 0.3s;">💬 조금 더 대화하고 싶어요</span>
    </div>
</div>
"""
    return message + "\n\n" + button_html


def format_books_recommendation(books: List[BookRecommendation], summary: PsychologicalSummary) -> str:
    """책 추천 결과만 채팅 메시지 형식으로 포맷팅"""
    result = "## 📚 추천 도서\n\n"
    
    if books:
        for i, book in enumerate(books, 1):
            result += f"**{i}. {book.title}** - {book.author}\n"
            result += f"- 출판사: {book.publisher}\n"
            result += f"- 추천 이유: {book.relevance_reason}\n"
            if book.link:
                result += f"- [네이버 도서 보기]({book.link})\n"
            result += "\n"
    else:
        result += "⚠️ 도서 검색에 실패했습니다. "
        result += f"다음 키워드로 직접 검색해보세요: {', '.join(summary.keywords)}\n"
    
    return result


def run_counseling_crew(user_message: str, conversation_history: List[Dict]) -> Tuple[str, bool]:
    """
    Counselor Agent와 대화 실행
    
    Returns:
        (상담사 응답, 분석 준비 완료 여부)
    """
    # 대화 기록 포맷팅
    history_text = ""
    if conversation_history:
        history_text = "\n\n=== 이전 대화 ===\n"
        for msg in conversation_history[-10:]:  # 최근 10개 메시지
            role = "사용자" if msg["role"] == "user" else "상담사"
            history_text += f"{role}: {msg['content']}\n"
        history_text += "================\n\n"
    
    inputs = {
        'user_message': user_message,
        'conversation_context': history_text,
    }
    
    try:
        crew = Crew(
            agents=[crew_instance.counselor()],
            tasks=[crew_instance.counseling_task()],
            process=Process.sequential,
            verbose=False  # 대화는 verbose 끄기
        )
        
        result = crew.kickoff(inputs=inputs)
        response = str(result).strip()
        
        # Tool 호출 확인 (signal_analysis_ready)
        # CrewAI의 실행 결과에서 Tool 호출 정보 확인
        analysis_ready = False
        try:
            # CrewAI는 실행 결과에 Tool 호출 정보를 포함
            if hasattr(result, 'tasks') and result.tasks:
                for task in result.tasks:
                    if hasattr(task, 'agent') and hasattr(task, 'output'):
                        output = str(task.output)
                        # signal_analysis_ready Tool이 호출되었는지 확인
                        if "분석 준비 완료" in output or "signal_analysis_ready" in output.lower():
                            analysis_ready = True
                            break
                    # task의 tool_calls 속성 확인
                    if hasattr(task, 'tool_calls') and task.tool_calls:
                        for tool_call in task.tool_calls:
                            if hasattr(tool_call, 'name') and 'signal_analysis_ready' in str(tool_call.name).lower():
                                analysis_ready = True
                                break
                    if analysis_ready:
                        break
        except Exception as e:
            # Tool 확인 실패 시 응답 내용으로 판단 (fallback)
            if "분석 준비 완료" in response or "signal_analysis_ready" in response.lower():
                analysis_ready = True
        
        return response, analysis_ready
    except Exception as e:
        raise Exception(f"상담 실행 중 오류 발생: {e}")


def run_analysis_crew(conversation_history: List[Dict]) -> PsychologicalSummary:
    """
    심리 분석 실행
    
    Returns:
        PsychologicalSummary 객체
    """
    # 대화 텍스트 포맷팅
    conversation_text = "\n\n".join([
        f"{'사용자' if m['role'] == 'user' else '상담사'}: {m['content']}"
        for m in conversation_history if m['role'] != 'system'
    ])
    
    inputs = {
        'conversation_text': conversation_text,
    }
    
    try:
        crew = Crew(
            agents=[crew_instance.psychological_analyzer()],
            tasks=[crew_instance.analysis_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff(inputs=inputs)
        result_text = str(result)
        
        # JSON 추출
        if "```json" in result_text:
            json_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            json_text = result_text.split("```")[1].split("```")[0].strip()
        else:
            start_idx = result_text.find("{")
            end_idx = result_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_text = result_text[start_idx:end_idx]
            else:
                raise ValueError("JSON을 찾을 수 없습니다")
        
        analysis_data = json.loads(json_text)
        
        # PsychologicalSummary 객체 생성
        return PsychologicalSummary(
            main_concerns=analysis_data.get("main_concerns", []),
            emotions=analysis_data.get("emotions", []),
            cognitive_patterns=analysis_data.get("cognitive_patterns", []),
            recommendations=analysis_data.get("recommendations", []),
            keywords=analysis_data.get("keywords", []),
            genre=None  # 장르는 나중에 설정됨
        )
    except Exception as e:
        raise Exception(f"분석 실행 중 오류 발생: {e}")


def run_book_recommendation_crew(summary: PsychologicalSummary, preferred_genre: str = None) -> List[BookRecommendation]:
    """
    도서 추천 실행
    
    Returns:
        BookRecommendation 객체 리스트
    """
    # analysis_task의 출력을 시뮬레이션하기 위한 입력 생성
    # book_recommendation_task는 analysis_task의 출력을 컨텍스트로 받지만,
    # 개별 실행 시에는 수동으로 전달해야 함
    analysis_output = json.dumps({
        "main_concerns": summary.main_concerns,
        "emotions": summary.emotions,
        "cognitive_patterns": summary.cognitive_patterns,
        "recommendations": summary.recommendations,
        "keywords": summary.keywords
    }, ensure_ascii=False)
    
    # Task description을 동적으로 수정하여 analysis_task의 출력을 포함
    from crewai import Task
    book_task = crew_instance.book_recommendation_task()
    
    # analysis_task의 출력을 포함한 description 생성
    enhanced_description = f"""
이전 태스크(analysis_task)의 출력:

```json
{analysis_output}
```

위 분석 결과를 바탕으로 관련 도서를 검색하세요. keywords 배열에서 3개의 키워드를 추출하여 각각으로 네이버 도서 API를 사용하여 검색하세요.
"""
    
    # Task를 새로 생성 (description 수정)
    book_task_modified = Task(
        description=enhanced_description,
        agent=crew_instance.book_recommender(),
        expected_output=book_task.expected_output
    )
    
    try:
        crew = Crew(
            agents=[crew_instance.book_recommender()],
            tasks=[book_task_modified],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        result_text = str(result)
        
        # JSON 추출
        if "```json" in result_text:
            json_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            json_text = result_text.split("```")[1].split("```")[0].strip()
        else:
            start_idx = result_text.find("{")
            end_idx = result_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_text = result_text[start_idx:end_idx]
            else:
                raise ValueError("JSON을 찾을 수 없습니다")
        
        search_data = json.loads(json_text)
        all_books = search_data.get("all_books", [])
        
        if not all_books:
            return []
        
        # 하이브리드 랭킹 알고리즘 적용
        reranked_books = rerank_books(
            all_books,
            preferred_genre=preferred_genre or summary.genre,
            max_results=5
        )
        
        # BookRecommendation 객체 리스트 생성
        recommendations = []
        for book_data in reranked_books:
            formatted = format_book_for_recommendation(book_data)
            
            # 추천 이유 생성
            relevance_reason = _generate_relevance_reason(
                book_data,
                summary,
                formatted.get("ranking_scores", {})
            )
            
            recommendations.append(BookRecommendation(
                title=formatted.get("title", ""),
                author=formatted.get("author", ""),
                publisher=formatted.get("publisher", ""),
                description=formatted.get("description", ""),
                isbn=formatted.get("isbn", ""),
                cover_image=formatted.get("cover_image", ""),
                link=formatted.get("link", ""),
                relevance_reason=relevance_reason
            ))
        
        return recommendations
    except Exception as e:
        raise Exception(f"도서 추천 실행 중 오류 발생: {e}")


def _generate_relevance_reason(book: Dict, summary: PsychologicalSummary, scores: Dict) -> str:
    """템플릿 기반 추천 이유 생성"""
    reasons = []
    
    # 최신성
    if scores.get("recency", 0) > 0.7:
        reasons.append("최신 출간된 책으로")
    
    # 장르 매칭
    if scores.get("genre_match", 0) > 0.7 and summary.genre:
        reasons.append(f"{summary.genre} 장르에 적합하며")
    
    # 주요 고민 연결
    if summary.main_concerns:
        concern = summary.main_concerns[0]
        reasons.append(f"'{concern}'에 대한 통찰을 제공합니다")
    
    # 기본 추천 이유
    if not reasons:
        reasons.append("검색 키워드와 높은 관련성을 보이며 도움이 될 수 있습니다")
    
    return " ".join(reasons) + "."


async def chat_with_bot(message: str, history: List) -> Tuple[List, str, bool, str]:
    """
    심리 상담 챗봇과 대화
    signal_analysis_ready tool이 호출되면 자동으로 분석 시작
    
    Args:
        message: 사용자 메시지
        history: 대화 기록 (Gradio 6.0 형식)
    
    Returns:
        (업데이트된 대화 기록, 상태 메시지, 장르 드롭다운 표시 여부, 장르 안내 메시지)
    """
    global conversation_history, analysis_done
    
    if not message.strip():
        return history, "메시지를 입력해주세요.", False, ""
    
    # Gradio 6.0 형식에서 메시지 리스트로 변환 (메타데이터 제거)
    messages = []
    if history:
        if isinstance(history[0], dict):
            for msg in history:
                if "role" in msg and "content" in msg:
                    messages.append(clean_message(msg))
        elif isinstance(history[0], tuple):
            for user_msg, bot_msg in history:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": bot_msg})
    
    # 현재 메시지 추가
    messages.append({"role": "user", "content": message})
    
    try:
        # 새로운 CrewAI 구조를 통한 챗봇 응답 생성
        # signal_analysis_ready tool 호출 여부 확인
        response, analysis_ready = run_counseling_crew(message, messages[:-1])  # 현재 메시지 제외
        
        # 상담 종료 멘트 감지
        counseling_ended = detect_counseling_end(response)
        
        # 대화 기록 업데이트 (원본 응답 저장)
        conversation_history = messages + [{"role": "assistant", "content": response}]
        
        # Gradio 히스토리 업데이트
        history.append({"role": "user", "content": message})
        
        # 상담 종료 멘트가 있으면 버튼 추가 (자동 실행하지 않음)
        if counseling_ended and not analysis_done:
            response_with_button = add_analysis_button_to_message(response)
            history.append({"role": "assistant", "content": response_with_button})
            # 상담 종료 멘트가 있으면 분석 준비 상태로 표시하지만 자동 실행하지 않음
            status = f"✅ 응답 생성 완료 ({len(conversation_history)}개 메시지)\n\n"
            status += "💡 위 메시지의 '🔍 상담 분석 및 책 추천받기' 버튼을 클릭하시면 심리 분석과 맞춤 도서 추천을 받으실 수 있습니다."
            return history, status, False, ""
        else:
            history.append({"role": "assistant", "content": response})
        
        # signal_analysis_ready tool이 호출되었을 때만 자동 분석 실행
        if analysis_ready and not analysis_done:
            status = f"✅ 응답 생성 완료 ({len(conversation_history)}개 메시지)\n\n"
            status += "🤖 AI가 충분한 정보를 수집했다고 판단했습니다. 자동으로 분석을 시작합니다..."
            
            # 심리 분석만 실행 (책 추천은 나중에)
            try:
                summary = run_analysis_crew(conversation_history)
                
                # 전역 변수에 저장
                global current_summary
                current_summary = summary
                
                # 분석 결과만 채팅 메시지로 추가 (책 추천 제안 포함)
                analysis_result = format_analysis_only(summary)
                history.append({
                    "role": "assistant",
                    "content": analysis_result
                })
                
                # conversation_history에도 추가
                conversation_history.append({
                    "role": "assistant",
                    "content": analysis_result
                })
                
                analysis_done = True
                status += "\n✅ 심리 분석 완료! 선호 장르를 선택한 후 '📚 책 추천받기' 버튼을 눌러주세요."
                
                # 장르 선택 UI 표시
                return history, status, True, "💡 장르를 선택하면 더 정확한 추천을 받을 수 있습니다."
                
            except Exception as analysis_error:
                import traceback
                print(f"분석 오류: {traceback.format_exc()}")
                error_msg = f"분석 중 오류가 발생했습니다: {str(analysis_error)}"
                history.append({
                    "role": "assistant",
                    "content": f"⚠️ {error_msg}"
                })
                status += f"\n❌ 분석 실패: {str(analysis_error)}"
                return history, status, False, ""
        else:
            if analysis_done:
                status = f"✅ 응답 생성 완료 ({len(conversation_history)}개 메시지) - 분석 완료됨"
                return history, status, True, "💡 장르를 선택하면 더 정확한 추천을 받을 수 있습니다."
            else:
                status = f"✅ 응답 생성 완료 ({len(conversation_history)}개 메시지)\n"
                status += f"💡 AI가 충분한 정보를 수집했다고 판단하면 자동으로 분석이 시작됩니다."
        
        return history, status, False, ""
    
    except Exception as e:
        error_msg = f"죄송합니다. 오류가 발생했습니다: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
        return history, f"❌ 오류: {str(e)}", False, ""


async def manual_analyze_and_recommend(history: List, selected_genre: str) -> Tuple[List, str, Any, Any]:
    """
    수동으로 분석 및 도서 추천 실행
    - 분석이 안 되어 있으면: 심리 분석 수행 + 책 추천 제안
    - 분석이 되어 있으면: 책 추천 수행
    
    Args:
        history: 대화 기록
        selected_genre: 선택된 장르
    
    Returns:
        (업데이트된 대화 기록, 상태 메시지, 장르 드롭다운 업데이트, 장르 안내 메시지 업데이트)
    """
    global conversation_history, analysis_done, current_summary, books_recommended
    
    # 히스토리에서 메시지 리스트로 변환 (메타데이터 제거)
    messages = []
    if history:
        if isinstance(history[0], dict):
            for msg in history:
                if "role" in msg and "content" in msg:
                    messages.append(clean_message(msg))
        elif isinstance(history[0], tuple):
            for user_msg, bot_msg in history:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": bot_msg})
    
    if not messages:
        return history, "❌ 대화 내용이 없습니다. 먼저 상담을 진행해주세요.", gr.update(visible=False), gr.update(value="", visible=False)
    
    # conversation_history 업데이트
    conversation_history = messages
    
    try:
        # 이미 책 추천이 완료된 경우
        if books_recommended:
            return history, "ℹ️ 이미 책 추천이 완료되었습니다. 대화를 초기화하고 다시 시도해주세요.", gr.update(visible=False), gr.update(value="", visible=False)
        
        # 분석이 이미 완료된 경우 -> 책 추천만 수행
        if analysis_done and current_summary:
            status = f"📚 '{selected_genre}' 장르 중심으로 책을 검색하고 추천해드리겠습니다. 잠시만 기다려주세요..."
            
            # 장르 정보를 summary에 추가
            current_summary.genre = selected_genre
            
            # 새로운 CrewAI 구조를 통한 도서 추천
            books = run_book_recommendation_crew(current_summary, selected_genre)
            
            # 책 추천 결과를 채팅 메시지로 추가
            books_result = format_books_recommendation(books, current_summary)
            history.append({
                "role": "assistant",
                "content": books_result
            })
            
            # conversation_history에도 추가
            conversation_history.append({
                "role": "assistant",
                "content": books_result
            })
            
            books_recommended = True
            status = f"✅ 책 추천 완료! ({len(books)}권 추천)"
            
            # 장르 드롭다운 숨기기
            return history, status, gr.update(visible=False), gr.update(value="", visible=False)
        
        # 분석이 안 되어 있는 경우 -> 심리 분석 수행 + 책 추천 실행
        status = "🔍 분석 및 책 추천을 시작합니다. 잠시만 기다려주세요..."
        
        # 새로운 CrewAI 구조를 통한 심리 분석 실행
        summary = run_analysis_crew(conversation_history)
        
        # 전역 변수에 저장
        current_summary = summary
        current_summary.genre = selected_genre
        
        # 도서 추천 실행
        books = run_book_recommendation_crew(summary, selected_genre)
        
        # 분석 결과와 책 추천을 함께 포맷팅
        combined_result = format_analysis_and_recommendation(summary, books)
        
        # 결과를 채팅 메시지로 추가
        history.append({
            "role": "assistant",
            "content": combined_result
        })
        
        # conversation_history에도 추가
        conversation_history.append({
            "role": "assistant",
            "content": combined_result
        })
        
        analysis_done = True
        books_recommended = True
        status = f"✅ 심리 분석 및 책 추천 완료! ({len(books)}권 추천)"
        
        # 장르 드롭다운 숨기기
        return history, status, gr.update(visible=False), gr.update(value="", visible=False)
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"수동 분석 중 오류: {error_detail}")
        error_msg = f"분석 중 오류가 발생했습니다: {str(e)}"
        return history, f"❌ {error_msg}", gr.update(visible=False), gr.update(value="", visible=False)


def clear_conversation() -> Tuple[List, str, bool, str]:
    """대화 기록 초기화"""
    global conversation_history, analysis_done, current_summary, books_recommended
    conversation_history = []
    analysis_done = False
    current_summary = None
    books_recommended = False
    return [], "🔄 대화 기록이 초기화되었습니다.", False, ""


def export_conversation() -> str:
    """대화 내용을 JSON으로 내보내기"""
    global conversation_history
    
    if not conversation_history:
        return "내보낼 대화 내용이 없습니다."
    
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "message_count": len(conversation_history),
        "messages": conversation_history
    }
    
    return json.dumps(export_data, ensure_ascii=False, indent=2)


# Gradio 인터페이스 구성 (단일 탭)
with gr.Blocks(
    title="심리 상담 챗봇 + 도서 추천"
) as demo:
    
    # JavaScript 이벤트 리스너 추가 (버튼 클릭 감지)
    demo.load(
        fn=None,
        js="""
        () => {
            // 채팅 메시지 내 선택 버튼 클릭 감지를 위한 이벤트 위임
            setInterval(() => {
                document.querySelectorAll('.analysis-choice').forEach(btn => {
                    if (!btn.dataset.listenerAdded) {
                        btn.dataset.listenerAdded = 'true';
                        btn.addEventListener('click', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            this.style.backgroundColor = '#357abd';
                            this.style.pointerEvents = 'none';
                            
                            const action = this.dataset.action || '';
                            const buttons = Array.from(document.querySelectorAll('button'));
                            
                            if (action === 'analyze') {
                                const recommendBtn = buttons.find(b => b.textContent.includes('책 추천받기'));
                                if (recommendBtn) {
                                    recommendBtn.click();
                                }
                                this.textContent = '분석/추천 실행 중...';
                            } else if (action === 'chat_more') {
                                const inputBox = document.querySelector('textarea');
                                if (inputBox) {
                                    inputBox.focus();
                                }
                                this.textContent = '계속 대화해요';
                                // 잠시 후 다시 클릭 가능하도록 복원
                                setTimeout(() => {
                                    this.style.backgroundColor = '#6c7a89';
                                    this.style.pointerEvents = 'auto';
                                }, 800);
                            }
                        });
                    }
                });
            }, 400);
        }
        """
    )
    
    # 헤더
    gr.Markdown("""
    # 🧠 심리 상담 챗봇 + 📚 도서 추천 시스템
    
    **CrewAI 멀티 에이전트 시스템** 기반 심리 상담 및 도서 추천 서비스
    
    ### 사용 방법
    1. 고민이나 감정을 자유롭게 이야기하세요
    2. **AI가 충분한 정보를 수집했다고 판단하면 자동으로 분석이 시작됩니다**
       - AI가 자연스럽게 상담을 마무리하고 분석을 시작합니다
    3. 추천된 도서를 통해 도움을 받으세요
    
    ### 멀티 에이전트 시스템
    - **Counselor Agent**: 공감적 경청과 데이터 수집 (LLM이 정보 충분성 판단)
    - **Psychological Analyzer Agent**: SKILL.md 프레임워크 기반 심층 심리 분석
    - **Book Recommender Agent**: 맞춤형 독서 치료 도서 추천
    
    **분석 프레임워크:** SKILL.md (인지심리학, 사회심리학, 임상심리학, 발달심리학, 신경과학)
    """)
    
    # 상태 표시
    status_box = gr.Textbox(
        label="상태",
        value="준비됨 - 대화를 시작해주세요",
        interactive=False,
        max_lines=3
    )
    
    # 채팅 인터페이스
    chatbot_interface = gr.Chatbot(
        label="대화",
        elem_id="chatbot",
        height=600,
        show_label=True,
        avatar_images=(None, "🤖")
    )
    
    # 메시지 입력 영역
    with gr.Row():
        msg_input = gr.Textbox(
            label="메시지 입력",
            placeholder="고민이나 감정을 이야기해주세요...",
            scale=4,
            max_lines=3,
            container=False
        )
        submit_btn = gr.Button("전송", scale=1, variant="primary", size="lg")
    
    # 장르 선택 (분석 후 표시)
    genre_dropdown = gr.Dropdown(
        label="📖 선호하는 책 장르를 선택해주세요",
        choices=["자기계발", "심리학", "소설", "에세이", "인문", "경제/경영", "기타"],
        value="자기계발",
        interactive=True,
        visible=False
    )
    genre_info = gr.Markdown("", visible=False)
    
    # 컨트롤 버튼
    with gr.Row():
        recommend_btn = gr.Button("📚 책 추천받기", variant="primary", size="lg")
        clear_btn = gr.Button("🔄 대화 초기화", variant="secondary")
        export_btn = gr.Button("💾 대화 내보내기", variant="secondary")
    
    # 내보내기 출력 (숨김)
    export_output = gr.Textbox(
        label="내보낸 대화 (JSON)",
        lines=10,
        visible=False
    )
    
    # 안내 메시지
    gr.Markdown("""
    ---
    
    ### 💡 안내사항
    
    - **🤖 지능형 분석**: AI가 충분한 정보를 수집했다고 판단하면 자동으로 분석 시작
      - AI 판단 기준: 주요 고민, 감정, 상황, 원인 인식, 대처 방식 파악 완료
      - 상담이 자연스럽게 끝나는 시점에 자동으로 분석이 시작됩니다
    - **수동 분석**: 언제든지 "📚 책 추천받기" 버튼을 클릭하여 분석 및 추천을 받을 수 있습니다
    - **대화 기록**: 모든 대화 내용이 위에 표시됩니다
    - **개인정보**: 민감한 개인정보는 입력하지 마세요
    
    ### 🤖 CrewAI 멀티 에이전트 시스템
    
    이 시스템은 세 개의 전문 AI 에이전트가 협력하여 작동합니다:
    
    1. **Counselor Agent** 🧑‍⚕️
       - 공감적 경청과 핵심 정보 수집
       - SKILL.md의 사회심리학 원리 적용
       
    2. **Psychological Analyzer Agent** 🧠
       - SKILL.md 프레임워크 기반 6단계 분석
       - 인지/사회/임상/발달 심리학 통합 분석
       
    3. **Book Recommender Agent** 📚
       - 심리 분석 결과 기반 맞춤 도서 추천
       - 네이버 도서 API 활용
    
    ⚠️ **이 챗봇은 전문적인 심리 상담을 대체할 수 없습니다.**
    위기 상황이나 심각한 심리적 문제가 있다면 전문가와 상담하세요.
    """)
    
    # 이벤트 핸들러
    async def submit_message(message, history):
        """메시지 전송 처리 (async)"""
        new_history, status, show_genre, genre_msg = await chat_with_bot(message, history)
        return new_history, status, "", gr.update(visible=show_genre), gr.update(value=genre_msg, visible=show_genre)
    
    submit_btn.click(
        fn=submit_message,
        inputs=[msg_input, chatbot_interface],
        outputs=[chatbot_interface, status_box, msg_input, genre_dropdown, genre_info]
    )
    
    msg_input.submit(
        fn=submit_message,
        inputs=[msg_input, chatbot_interface],
        outputs=[chatbot_interface, status_box, msg_input, genre_dropdown, genre_info]
    )
    
    # 책 추천받기 버튼 이벤트
    recommend_btn.click(
        fn=manual_analyze_and_recommend,
        inputs=[chatbot_interface, genre_dropdown],
        outputs=[chatbot_interface, status_box, genre_dropdown, genre_info]
    )
    
    clear_btn.click(
        fn=clear_conversation,
        outputs=[chatbot_interface, status_box, genre_dropdown, genre_info]
    )
    
    export_btn.click(
        fn=export_conversation,
        outputs=[export_output]
    ).then(
        fn=lambda: gr.Textbox(visible=True),
        outputs=[export_output]
    )
    
    # 푸터
    gr.Markdown("""
    ---
    
    Made with ❤️ using CrewAI, Claude AI (Sonnet 4), SKILL.md Framework, and Gradio
    
    **Architecture**: Multi-Agent System with Sequential Workflow (CrewAI Official Structure)
    """)


# 앱 실행
if __name__ == "__main__":
    print("=" * 60)
    print("CrewAI 멀티 에이전트 심리 상담 + 도서 추천 시스템")
    print("=" * 60)
    print("\n🤖 에이전트 시스템:")
    print("  - Counselor Agent (경청 & 데이터 수집)")
    print("  - Psychological Analyzer Agent (SKILL.md 기반 분석)")
    print("  - Book Recommender Agent (맞춤 도서 추천)")
    print("\n서버를 시작합니다...")
    print("브라우저에서 자동으로 열립니다.")
    print("=" * 60 + "\n")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        quiet=False,
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1400px !important;
        }
        #chatbot {
            height: 600px;
        }
        """
    )
