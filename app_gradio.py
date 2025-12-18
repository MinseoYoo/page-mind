"""
Gradio 웹 데모 - 심리 상담 챗봇 + 도서 추천
단일 탭 구성, 5회 이상 대화 시 자동 분석 및 추천
"""

import sys
import platform
import asyncio

# Windows에서 asyncio 이벤트 루프 정책 설정 (Gradio 시작 전에)
if platform.system() == 'Windows':
    if sys.version_info >= (3, 8):
        # Windows에서 SelectorEventLoop 사용 (ProactorEventLoop 대신)
        # ProactorEventLoop는 socket.socketpair()에서 문제 발생
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            # Python 3.7 이하에서는 사용 불가
            pass

import gradio as gr
from datetime import datetime
from typing import List, Tuple
import json
import os

from dotenv import load_dotenv
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# CrewAI Multi-Agent Orchestrator
from core_crewai.crew_orchestrator import CrewOrchestrator
from core_crewai.models import PsychologicalSummary, BookRecommendation

# 서비스 인스턴스 생성 (CrewAI Orchestrator)
orchestrator = CrewOrchestrator()

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


def format_analysis_result(summary: PsychologicalSummary, books: List) -> str:
    """분석 결과를 채팅 메시지 형식으로 포맷팅 (하위 호환성용)"""
    result = format_analysis_only(summary)
    result = result.replace("충분한 상담이 끝난 것 같은데 책을 추천해드릴까요?", "")
    result += "\n" + format_books_recommendation(books, summary)
    return result


async def chat_with_bot(message: str, history: List) -> Tuple[List, str, bool, str]:
    """
    심리 상담 챗봇과 대화
    5회 이상의 assistant 응답을 받으면 자동으로 분석 및 추천 실행
    
    Args:
        message: 사용자 메시지
        history: 대화 기록 (Gradio 6.0 형식)
    
    Returns:
        (업데이트된 대화 기록, 상태 메시지, 장르 드롭다운 표시 여부, 장르 안내 메시지)
    """
    global conversation_history, analysis_done
    
    if not message.strip():
        return history, "메시지를 입력해주세요."
    
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
    
    # assistant 메시지 개수 확인 (현재 응답 전)
    assistant_count_before = count_assistant_messages(history)
    
    # 5번째 응답을 생성하기 전에 (4번째 응답까지 받은 상태) 끝맺는 말을 하도록 프롬프트 추가
    is_last_response = (assistant_count_before == 4 and not analysis_done)
    
    try:
        # 마지막 응답인 경우 끝맺는 말을 하도록 프롬프트 추가
        if is_last_response:
            closing_prompt = "\n\n[중요: 이것이 이번 상담의 마지막 응답입니다. 사용자에게 따뜻하고 격려하는 마무리 인사를 하되, 추가 질문을 하지 말고 상담을 자연스럽게 마무리해주세요. 예: '오늘 대화를 통해 많은 것을 나눈 것 같습니다. 앞으로도 힘내시길 바라며, 필요하시면 언제든 다시 찾아주세요.'와 같은 형식으로 마무리하세요.]"
            messages[-1]["content"] = message + closing_prompt
        
        # CrewAI Orchestrator를 통한 챗봇 응답 생성
        # orchestrator.chat()는 이제 (응답, 분석준비여부) 튜플 반환
        response, analysis_ready = orchestrator.chat(message, history)
        
        # 대화 기록 업데이트
        conversation_history = messages + [{"role": "assistant", "content": response}]
        
        # Gradio 히스토리 업데이트
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        
        # assistant 메시지 개수 확인
        assistant_count = count_assistant_messages(history)
        
        # LLM이 정보 수집 완료를 판단했거나, 5회 이상 대화했다면 자동 분석 실행
        if (analysis_ready or assistant_count >= 5) and not analysis_done:
            status = f"✅ 응답 생성 완료 ({len(conversation_history)}개 메시지)\n\n"
            if analysis_ready:
                status += "🤖 AI가 충분한 정보를 수집했다고 판단했습니다. 자동으로 분석을 시작합니다..."
            else:
                status += "🔍 5회 대화가 완료되었습니다. 자동으로 분석을 시작합니다..."
            
            # 심리 분석만 실행 (책 추천은 나중에) - CrewAI Orchestrator 사용
            try:
                summary = orchestrator.analyze_conversation(conversation_history)
                
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
                status += f"💡 AI가 충분한 정보를 수집했다고 판단하면 자동으로 분석이 시작됩니다.\n"
                if assistant_count < 5:
                    remaining = 5 - assistant_count
                    status += f"   (또는 {remaining}회 더 대화 후 자동 분석)"
        
        return history, status, False, ""
    
    except Exception as e:
        error_msg = f"죄송합니다. 오류가 발생했습니다: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
        return history, f"❌ 오류: {str(e)}", False, ""


async def manual_analyze_and_recommend(history: List, selected_genre: str) -> Tuple[List, str, bool, str]:
    """
    수동으로 분석 및 도서 추천 실행
    - 분석이 안 되어 있으면: 심리 분석 수행 + 책 추천 제안
    - 분석이 되어 있으면: 책 추천 수행
    
    Args:
        history: 대화 기록
        selected_genre: 선택된 장르
    
    Returns:
        (업데이트된 대화 기록, 상태 메시지, 장르 드롭다운 표시 여부, 장르 안내 메시지)
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
        return history, "❌ 대화 내용이 없습니다. 먼저 상담을 진행해주세요.", False, ""
    
    # conversation_history 업데이트
    conversation_history = messages
    
    try:
        # 이미 책 추천이 완료된 경우
        if books_recommended:
            return history, "ℹ️ 이미 책 추천이 완료되었습니다. 대화를 초기화하고 다시 시도해주세요.", False, ""
        
        # 분석이 이미 완료된 경우 -> 책 추천만 수행
        if analysis_done and current_summary:
            status = f"📚 '{selected_genre}' 장르 중심으로 책을 검색하고 추천해드리겠습니다. 잠시만 기다려주세요..."
            
            # 장르 정보를 summary에 추가
            current_summary.genre = selected_genre
            
            # CrewAI Orchestrator를 통한 도서 추천
            books = orchestrator.recommend_books_from_summary(current_summary, max_books=5)
            
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
            return history, status, False, ""
        
        # 분석이 안 되어 있는 경우 -> 심리 분석 수행 + 책 추천 제안
        # 먼저 AI의 안내 메시지를 채팅에 추가
        intro_message = "지금까지 나눈 대화를 통해 도움이 될 만한 책을 추천해줄게요"
        history.append({
            "role": "assistant",
            "content": intro_message
        })
        conversation_history.append({
            "role": "assistant",
            "content": intro_message
        })
        
        status = "🔍 분석을 시작합니다. 잠시만 기다려주세요..."
        
        # CrewAI Orchestrator를 통한 심리 분석 실행
        summary = orchestrator.analyze_conversation(conversation_history)
        
        # 전역 변수에 저장
        current_summary = summary
        
        # 분석 결과를 채팅 메시지로 추가 (책 추천 제안 포함)
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
        status = "✅ 심리 분석 완료! 선호 장르를 선택한 후 '📚 책 추천받기' 버튼을 눌러주세요."
        
        # 장르 선택 UI 표시
        return history, status, True, "💡 장르를 선택하면 더 정확한 추천을 받을 수 있습니다."
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"수동 분석 중 오류: {error_detail}")
        error_msg = f"분석 중 오류가 발생했습니다: {str(e)}"
        return history, f"❌ {error_msg}", False, ""


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
    
    # 헤더
    gr.Markdown("""
    # 🧠 심리 상담 챗봇 + 📚 도서 추천 시스템
    
    **CrewAI 멀티 에이전트 시스템** 기반 심리 상담 및 도서 추천 서비스
    
    ### 사용 방법
    1. 고민이나 감정을 자유롭게 이야기하세요
    2. **AI가 충분한 정보를 수집했다고 판단하면 자동으로 분석이 시작됩니다**
       - 또는 5회 대화 후 자동 분석 (안전장치)
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
      - 안전장치: 5회 대화 후 자동 분석 (정보 부족 시)
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
    
    **Architecture**: Multi-Agent System with Sequential Workflow
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
