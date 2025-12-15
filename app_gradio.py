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

from core.psychology_chatbot import PsychologyChatbot
from core.counseling_analyzer import CounselingAnalyzer
from core.book_recommender import BookRecommender
from core.models import PsychologicalSummary, BookRecommendation

# 서비스 인스턴스 생성
chatbot = PsychologyChatbot(ANTHROPIC_API_KEY)
analyzer = CounselingAnalyzer(ANTHROPIC_API_KEY)
recommender = BookRecommender(ANTHROPIC_API_KEY)

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


async def chat_with_bot(message: str, history: List) -> Tuple[List, str]:
    """
    심리 상담 챗봇과 대화
    5회 이상의 assistant 응답을 받으면 자동으로 분석 및 추천 실행
    
    Args:
        message: 사용자 메시지
        history: 대화 기록 (Gradio 6.0 형식)
    
    Returns:
        (업데이트된 대화 기록, 상태 메시지)
    """
    global conversation_history, analysis_done
    
    if not message.strip():
        return history, "메시지를 입력해주세요."
    
    # Gradio 6.0 형식에서 메시지 리스트로 변환
    messages = []
    if history:
        if isinstance(history[0], dict):
            for msg in history:
                if "role" in msg and "content" in msg:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
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
        
        # 챗봇 응답 생성
        response = chatbot.chat(messages)
        
        # 대화 기록 업데이트
        conversation_history = messages + [{"role": "assistant", "content": response}]
        
        # Gradio 히스토리 업데이트
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        
        # assistant 메시지 개수 확인
        assistant_count = count_assistant_messages(history)
        
        # 5회 이상의 assistant 응답을 받았고, 아직 분석을 하지 않았다면 자동 분석 실행
        if assistant_count >= 5 and not analysis_done:
            status = f"✅ 응답 생성 완료 ({len(conversation_history)}개 메시지)\n\n"
            status += "🔍 충분한 대화가 이루어졌습니다. 자동으로 분석을 시작합니다..."
            
            # 심리 분석만 실행 (책 추천은 나중에)
            try:
                summary = analyzer.analyze_conversation(conversation_history)
                
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
                status += "\n✅ 심리 분석 완료! 책 추천을 원하시면 '📚 책 추천받기' 버튼을 눌러주세요."
                
            except Exception as analysis_error:
                import traceback
                print(f"분석 오류: {traceback.format_exc()}")
                error_msg = f"분석 중 오류가 발생했습니다: {str(analysis_error)}"
                history.append({
                    "role": "assistant",
                    "content": f"⚠️ {error_msg}"
                })
                status += f"\n❌ 분석 실패: {str(analysis_error)}"
        else:
            if analysis_done:
                status = f"✅ 응답 생성 완료 ({len(conversation_history)}개 메시지) - 분석 완료됨"
            else:
                remaining = 5 - assistant_count
                status = f"✅ 응답 생성 완료 ({len(conversation_history)}개 메시지)\n"
                status += f"💡 {remaining}회 더 대화하면 자동으로 분석이 시작됩니다."
        
        return history, status
    
    except Exception as e:
        error_msg = f"죄송합니다. 오류가 발생했습니다: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
        return history, f"❌ 오류: {str(e)}"


async def manual_analyze_and_recommend(history: List) -> Tuple[List, str]:
    """
    수동으로 분석 및 도서 추천 실행
    - 분석이 안 되어 있으면: 심리 분석 수행 + 책 추천 제안
    - 분석이 되어 있으면: 책 추천 수행
    
    Args:
        history: 대화 기록
    
    Returns:
        (업데이트된 대화 기록, 상태 메시지)
    """
    global conversation_history, analysis_done, current_summary, books_recommended
    
    # 히스토리에서 메시지 리스트로 변환
    messages = []
    if history:
        if isinstance(history[0], dict):
            for msg in history:
                if "role" in msg and "content" in msg:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
        elif isinstance(history[0], tuple):
            for user_msg, bot_msg in history:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": bot_msg})
    
    if not messages:
        return history, "❌ 대화 내용이 없습니다. 먼저 상담을 진행해주세요."
    
    # conversation_history 업데이트
    conversation_history = messages
    
    try:
        # 이미 책 추천이 완료된 경우
        if books_recommended:
            return history, "ℹ️ 이미 책 추천이 완료되었습니다. 대화를 초기화하고 다시 시도해주세요."
        
        # 분석이 이미 완료된 경우 -> 책 추천만 수행
        if analysis_done and current_summary:
            status = "📚 책을 검색하고 추천해드리겠습니다. 잠시만 기다려주세요..."
            
            # 네이버 API를 통한 도서 추천
            books = await recommender.recommend_books(current_summary, max_books=5)
            
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
            
            return history, status
        
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
        
        # 심리 분석 실행
        summary = analyzer.analyze_conversation(conversation_history)
        
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
        status = "✅ 심리 분석 완료! 책 추천을 원하시면 다시 '📚 책 추천받기' 버튼을 눌러주세요."
        
        return history, status
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"수동 분석 중 오류: {error_detail}")
        error_msg = f"분석 중 오류가 발생했습니다: {str(e)}"
        return history, f"❌ {error_msg}"


def clear_conversation() -> Tuple[List, str]:
    """대화 기록 초기화"""
    global conversation_history, analysis_done, current_summary, books_recommended
    conversation_history = []
    analysis_done = False
    current_summary = None
    books_recommended = False
    return [], "🔄 대화 기록이 초기화되었습니다."


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
    
    AI 기반 심리 상담을 받고, **5회 이상 대화하면 자동으로** 맞춤형 도서를 추천받으세요.
    
    ### 사용 방법
    1. 고민이나 감정을 자유롭게 이야기하세요
    2. **5회 이상 대화하면 자동으로 분석 및 도서 추천이 시작됩니다**
    3. 추천된 도서를 통해 도움을 받으세요
    
    **상담 프레임워크:** 인지행동치료(CBT), 자기결정이론, 스트레스 대처 전략
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
    
    - **자동 분석**: 5회 이상의 상담 응답을 받으면 자동으로 심리 분석과 도서 추천이 시작됩니다
    - **수동 분석**: 언제든지 "📚 책 추천받기" 버튼을 클릭하여 분석 및 추천을 받을 수 있습니다
    - **대화 기록**: 모든 대화 내용이 위에 표시됩니다
    - **개인정보**: 민감한 개인정보는 입력하지 마세요
    
    ⚠️ **이 챗봇은 전문적인 심리 상담을 대체할 수 없습니다.**
    위기 상황이나 심각한 심리적 문제가 있다면 전문가와 상담하세요.
    """)
    
    # 이벤트 핸들러
    async def submit_message(message, history):
        """메시지 전송 처리 (async)"""
        new_history, status = await chat_with_bot(message, history)
        return new_history, status, ""
    
    submit_btn.click(
        fn=submit_message,
        inputs=[msg_input, chatbot_interface],
        outputs=[chatbot_interface, status_box, msg_input]
    )
    
    msg_input.submit(
        fn=submit_message,
        inputs=[msg_input, chatbot_interface],
        outputs=[chatbot_interface, status_box, msg_input]
    )
    
    # 책 추천받기 버튼 이벤트
    recommend_btn.click(
        fn=manual_analyze_and_recommend,
        inputs=[chatbot_interface],
        outputs=[chatbot_interface, status_box]
    )
    
    clear_btn.click(
        fn=clear_conversation,
        outputs=[chatbot_interface, status_box]
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
    
    Made with ❤️ using Claude AI and Gradio
    """)


# 앱 실행
if __name__ == "__main__":
    print("=" * 60)
    print("심리 상담 챗봇 + 도서 추천 Gradio 데모")
    print("=" * 60)
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
