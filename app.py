"""
Streamlit frontend for the RAG + LLM Wiki System.

Tabs:
  1. Ask Questions  — retrieve chunks, generate a cited answer
  2. Generate Wiki  — create or update a wiki page for a topic
  3. Browse Wiki    — read saved wiki pages
"""

import os
from pathlib import Path

import streamlit as st

from answer import generate_answer
from retrieval import format_citation
from wiki_writer import retrieve, save_wiki_page, WIKI_FOLDERS

WIKI_DIR = Path("wiki")

# ── Translations ──────────────────────────────────────────────────────────────

STRINGS = {
    "en": {
        "page_title": "RAG Wiki",
        "app_title": "📚 RAG + LLM Wiki System",
        "api_error": "ANTHROPIC_API_KEY is not set. Export it before launching the app.",
        "tab_ask": "Ask Questions",
        "tab_wiki": "Generate Wiki Page",
        "tab_browse": "Browse Wiki",
        # Tab 1
        "ask_header": "Ask a Question",
        "ask_caption": "Answers are generated only from your ingested documents.",
        "ask_input": "Your question",
        "ask_placeholder": "e.g. What is the main argument of the document?",
        "ask_slider": "Chunks to retrieve",
        "ask_button": "Get Answer",
        "ask_answer_header": "Answer",
        "ask_sources": "Sources used",
        "ask_spinner": "Retrieving and generating answer…",
        # Tab 2
        "wiki_header": "Generate or Update a Wiki Page",
        "wiki_caption": "The page is saved as Markdown in the `wiki/` folder.",
        "wiki_topic": "Topic",
        "wiki_topic_placeholder": "e.g. Transformer Architecture",
        "wiki_query": "Retrieval query (optional)",
        "wiki_query_placeholder": "Leave blank to use the topic name",
        "wiki_slider": "Chunks to retrieve",
        "wiki_button": "Generate / Update Wiki Page",
        "wiki_spinner": "Retrieving chunks and writing wiki page…",
        "wiki_no_chunks": "No chunks retrieved. Make sure documents have been ingested first.",
        "wiki_saved": "Wiki page saved: `{path}`",
        # Tab 3
        "browse_header": "Browse Wiki Pages",
        "browse_empty": "No wiki pages yet. Generate one in the **Generate Wiki Page** tab.",
        "browse_select": "Select a page",
        "browse_raw": "Raw Markdown",
    },
    "vi": {
        "page_title": "RAG Wiki",
        "app_title": "📚 Hệ thống RAG + Wiki LLM",
        "api_error": "ANTHROPIC_API_KEY chưa được thiết lập. Vui lòng xuất biến môi trường trước khi khởi chạy ứng dụng.",
        "tab_ask": "Đặt câu hỏi",
        "tab_wiki": "Tạo trang Wiki",
        "tab_browse": "Duyệt Wiki",
        # Tab 1
        "ask_header": "Đặt câu hỏi",
        "ask_caption": "Câu trả lời chỉ được tạo ra từ các tài liệu đã nhập.",
        "ask_input": "Câu hỏi của bạn",
        "ask_placeholder": "Ví dụ: Luận điểm chính của tài liệu là gì?",
        "ask_slider": "Số đoạn văn bản cần truy xuất",
        "ask_button": "Nhận câu trả lời",
        "ask_answer_header": "Câu trả lời",
        "ask_sources": "Nguồn đã sử dụng",
        "ask_spinner": "Đang truy xuất và tạo câu trả lời…",
        # Tab 2
        "wiki_header": "Tạo hoặc cập nhật trang Wiki",
        "wiki_caption": "Trang được lưu dưới dạng Markdown trong thư mục `wiki/`.",
        "wiki_topic": "Chủ đề",
        "wiki_topic_placeholder": "Ví dụ: Kiến trúc Transformer",
        "wiki_query": "Truy vấn truy xuất (tuỳ chọn)",
        "wiki_query_placeholder": "Để trống để sử dụng tên chủ đề",
        "wiki_slider": "Số đoạn văn bản cần truy xuất",
        "wiki_button": "Tạo / Cập nhật trang Wiki",
        "wiki_spinner": "Đang truy xuất đoạn văn bản và viết trang Wiki…",
        "wiki_no_chunks": "Không tìm thấy đoạn văn bản nào. Hãy đảm bảo tài liệu đã được nhập.",
        "wiki_saved": "Trang Wiki đã lưu: `{path}`",
        # Tab 3
        "browse_header": "Duyệt các trang Wiki",
        "browse_empty": "Chưa có trang Wiki nào. Hãy tạo một trang trong tab **Tạo trang Wiki**.",
        "browse_select": "Chọn một trang",
        "browse_raw": "Markdown thô",
    },
}

# ── Page config & language toggle ────────────────────────────────────────────

st.set_page_config(page_title="RAG Wiki", page_icon="📚", layout="wide")

if "lang" not in st.session_state:
    st.session_state.lang = "en"

col_title, col_toggle = st.columns([6, 1])
with col_title:
    t = STRINGS[st.session_state.lang]
    st.title(t["app_title"])
with col_toggle:
    st.write("")  # vertical alignment nudge
    label = "🇻🇳 Tiếng Việt" if st.session_state.lang == "en" else "🇬🇧 English"
    if st.button(label):
        st.session_state.lang = "vi" if st.session_state.lang == "en" else "en"
        st.rerun()

t = STRINGS[st.session_state.lang]

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(t["api_error"])
    st.stop()

tab_ask, tab_wiki, tab_browse = st.tabs([t["tab_ask"], t["tab_wiki"], t["tab_browse"]])


# ── Tab 1: Ask Questions ──────────────────────────────────────────────────────

with tab_ask:
    st.header(t["ask_header"])
    st.caption(t["ask_caption"])

    question = st.text_input(t["ask_input"], placeholder=t["ask_placeholder"])
    top_k = st.slider(t["ask_slider"], min_value=1, max_value=15, value=5, key="ask_top_k")

    if st.button(t["ask_button"], disabled=not question.strip()):
        with st.spinner(t["ask_spinner"]):
            result = generate_answer(question.strip(), top_k=top_k)

        st.subheader(t["ask_answer_header"])
        st.markdown(result["answer"])

        if result["chunks"]:
            with st.expander(t["ask_sources"]):
                for i, chunk in enumerate(result["chunks"], start=1):
                    st.markdown(f"**[{i}] {format_citation(chunk)}**")
                    st.caption(chunk["text"][:300] + ("…" if len(chunk["text"]) > 300 else ""))


# ── Tab 2: Generate Wiki Page ─────────────────────────────────────────────────

with tab_wiki:
    st.header(t["wiki_header"])
    st.caption(t["wiki_caption"])

    topic = st.text_input(t["wiki_topic"], placeholder=t["wiki_topic_placeholder"])
    custom_query = st.text_input(t["wiki_query"], placeholder=t["wiki_query_placeholder"])
    folder = st.selectbox("Save to folder", WIKI_FOLDERS)
    top_k_wiki = st.slider(t["wiki_slider"], min_value=1, max_value=15, value=6, key="wiki_top_k")

    if st.button(t["wiki_button"], disabled=not topic.strip()):
        query = custom_query.strip() or topic.strip()
        with st.spinner(t["wiki_spinner"]):
            chunks = retrieve(query, top_k=top_k_wiki)
            if not chunks:
                st.error(t["wiki_no_chunks"])
            else:
                page_path = save_wiki_page(topic.strip(), chunks, folder=folder)
                st.success(t["wiki_saved"].format(path=page_path))
                st.markdown(page_path.read_text(encoding="utf-8"))


# ── Tab 3: Browse Wiki ────────────────────────────────────────────────────────

with tab_browse:
    st.header(t["browse_header"])

    WIKI_DIR.mkdir(exist_ok=True)

    # Collect pages from all subfolders
    all_pages = sorted(WIKI_DIR.glob("**/*.md"))
    all_pages = [p for p in all_pages if p.name != ".gitkeep"]

    if not all_pages:
        st.info(t["browse_empty"])
    else:
        # Group by folder
        folders_with_pages = {}
        for p in all_pages:
            folder_name = p.parent.name
            folders_with_pages.setdefault(folder_name, []).append(p)

        selected_folder = st.selectbox("Folder", list(folders_with_pages.keys()))
        folder_pages = folders_with_pages[selected_folder]
        page_names = {p.stem.replace("_", " ").title(): p for p in folder_pages}
        selected = st.selectbox(t["browse_select"], list(page_names.keys()))

        if selected:
            page_path = page_names[selected]
            content = page_path.read_text(encoding="utf-8")

            col_render, col_raw = st.columns([3, 2])
            with col_render:
                st.markdown(content)
            with col_raw:
                st.caption(t["browse_raw"])
                st.code(content, language="markdown")
