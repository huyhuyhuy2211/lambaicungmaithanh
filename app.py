import streamlit as st
import PyPDF2
import google.generativeai as genai
import json
import os
import pandas as pd
from datetime import datetime
import time # Thư viện để đếm giờ chờ

# ==========================================
# 👇 DÁN API KEY CỦA BẠN VÀO DÒNG DƯỚI 👇
MY_API_KEY = "AIzaSyBuG_sxa1T0nf4WfCrv7Hhd4Tmt5V0wsYY"
# ==========================================

st.set_page_config(page_title="Ôn Tập Pro Max (Auto-Retry)", layout="wide", page_icon="⚡")
st.title("⚡ Ôn Tập cùng Mai Thanh")

# --- CSS CHO BẢNG CÂU HỎI ---
st.markdown("""
<style>
    .nav-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; padding: 10px 0; }
    .nav-item { display: flex; align-items: center; justify-content: center; height: 35px; text-decoration: none; font-weight: bold; border-radius: 4px; border: 1px solid #e0e0e0; color: #333; background-color: white;}
    .nav-item:hover { transform: scale(1.1); border-color: #aaa; }
    .status-correct { background-color: #d1fae5 !important; border-color: #34d399 !important; color: #065f46 !important; }
    .status-wrong { background-color: #fee2e2 !important; border-color: #f87171 !important; color: #991b1b !important; }
</style>
""", unsafe_allow_html=True)

# --- CẤU HÌNH LỊCH SỬ ---
HISTORY_FILE = 'quiz_history.json'
def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return []

def save_to_history(filename, score, total_questions):
    history = load_history()
    record = {
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "filename": filename,
        "score": f"{score}/{total_questions}",
        "percentage": round((score/total_questions)*100, 1)
    }
    history.insert(0, record)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

# --- HÀM ĐỌC PDF ---
def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except: return ""

# --- HÀM GỌI AI (CÓ TỰ ĐỘNG THỬ LẠI) ---
def generate_quiz(text):
    if "DÁN_MÃ" in MY_API_KEY or len(MY_API_KEY) < 10:
        st.error("⚠️ Chưa nhập API Key!")
        return []

    genai.configure(api_key=MY_API_KEY)
    
    # Giảm bớt dung lượng văn bản xuống 100k ký tự để tránh quá tải quota
    safe_text = text[:100000]
    
    prompt = f"""
    Tạo bộ câu hỏi trắc nghiệm từ văn bản sau.
    Văn bản: "{safe_text}"
    
    YÊU CẦU:
    1. Trích xuất TOÀN BỘ câu hỏi.
    2. Nếu thiếu đáp án, hãy TỰ GIẢI.
    3. Trả về JSON list thuần túy:
    [
        {{
            "question": "Nội dung câu hỏi?",
            "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
            "answer": "A. ..."
        }}
    ]
    """
    
    # Ưu tiên bản 2.5 mới nhất, sau đó đến 2.0
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]

    for model_name in models_to_try:
        # Cơ chế thử lại 3 lần (Retry Loop)
        for attempt in range(3): 
            try:
                status_placeholder = st.empty()
                if attempt > 0:
                    status_placeholder.warning(f"⏳ Server đang bận, đang thử lại lần {attempt+1} với model {model_name}...")
                
                model = genai.GenerativeModel(model_name=model_name)
                response = model.generate_content(prompt)
                
                # Xử lý làm sạch JSON
                raw_text = response.text
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0]
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0]
                
                status_placeholder.empty() # Xóa thông báo chờ
                return json.loads(raw_text.strip())

            except Exception as e:
                # Nếu gặp lỗi 429 (Quota), chờ 10 giây rồi thử lại
                if "429" in str(e):
                    time.sleep(10) # Nghỉ 10 giây
                    continue
                else:
                    print(f"Lỗi khác: {e}")
                    break # Nếu lỗi khác thì đổi model
                    
    st.error("❌ Đã thử hết các cách nhưng server Google vẫn quá tải. Bạn hãy đợi 1-2 phút nữa rồi thử lại nhé!")
    return []

# --- GIAO DIỆN ---
if 'step' not in st.session_state: st.session_state['step'] = 1

# BƯỚC 1: UPLOAD
if st.session_state['step'] == 1:
    with st.sidebar:
        st.header("🗂️ Lịch sử")
        history_data = load_history()
        if history_data:
            st.dataframe(history_data, hide_index=True)
            if st.button("Xóa lịch sử"):
                if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE); st.rerun()

    st.info("👋 Xin chào Mai Thanh, hãy upload bài để anh Huy giúp nhe ^^")
    uploaded_file = st.file_uploader("Chọn file PDF...", type=['pdf'])
    
    if uploaded_file:
        if st.button("🚀Tạo Đề Thi"):
            with st.spinner("Đợi anh Huy 1 tí, trong lúc đợi thì uống giúp anh Huy ly nước..."):
                text = extract_text_from_pdf(uploaded_file)
                data = generate_quiz(text)
                if data:
                    st.session_state['quiz_data'] = data
                    st.session_state['filename'] = uploaded_file.name
                    st.session_state['step'] = 2
                    st.rerun()

# BƯỚC 2: CHỈNH SỬA
elif st.session_state['step'] == 2:
    st.info(f"✅ Đã tìm thấy {len(st.session_state['quiz_data'])} câu hỏi.")
    edited_data = st.data_editor(st.session_state['quiz_data'], num_rows="dynamic", use_container_width=True, height=500)
    if st.button("✅ Vào làm bài"):
        st.session_state['final_quiz'] = edited_data
        st.session_state['step'] = 3
        st.rerun()

# BƯỚC 3: LÀM BÀI
elif st.session_state['step'] == 3:
    questions = st.session_state['final_quiz']
    total_q = len(questions)
    current_score = 0
    
    for i, q in enumerate(questions):
        user_choice = st.session_state.get(f"q_{i}")
        if user_choice:
            if user_choice.split('.')[0] == q['answer'].strip().split('.')[0]:
                current_score += 1

    with st.sidebar:
        st.metric("Điểm số", f"{current_score} / {total_q}")
        if st.button("💾 LƯU ĐIỂM", type="primary", use_container_width=True):
            save_to_history(st.session_state.get('filename'), current_score, total_q)
            st.toast("Đã lưu!"); st.balloons()
        
        if st.button("⬅️ Thoát", use_container_width=True):
            st.session_state.clear(); st.rerun()

        st.divider()
        st.write("📍 **Bảng tiến độ:**")
        
        grid_html = "<div class='nav-grid'>"
        for i in range(total_q):
            user_choice = st.session_state.get(f"q_{i}")
            status_class = "status-none"
            if user_choice:
                if user_choice.split('.')[0] == questions[i]['answer'].strip().split('.')[0]:
                    status_class = "status-correct"
                else:
                    status_class = "status-wrong"
            grid_html += f"<a href='#q_anchor_{i}' class='nav-item {status_class}' target='_self'>{i+1}</a>"
        grid_html += "</div>"
        st.markdown(f"<div style='max-height: 600px; overflow-y: auto;'>{grid_html}</div>", unsafe_allow_html=True)

    st.subheader(f"📝 Đề: {st.session_state.get('filename')}")
    st.divider()
    
    for i, q in enumerate(questions):
        st.markdown(f"<div id='q_anchor_{i}'></div>", unsafe_allow_html=True) 
        st.markdown(f"**Câu {i+1}: {q['question']}**")
        user_choice = st.radio("Chọn:", q['options'], key=f"q_{i}", index=None, label_visibility="collapsed")
        
        if user_choice:
            correct = q['answer'].strip()
            if user_choice.split('.')[0] == correct.split('.')[0]:
                st.success("✅ Chính xác! Bé Mai Thanh quá tuyệt!")
            else:
                st.error(f"❌ OMG. Đáp án đúng là: {correct}")
        st.markdown("---")