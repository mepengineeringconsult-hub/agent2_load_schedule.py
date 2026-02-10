# CODE VERSION: 1.3.0
# UPDATE: Rollback to Stable Base + Fix LC32 ELCB + Fix LC1B Naming + UI Version Info

import streamlit as st
import google.generativeai as genai
import os
import time

# --- 1. ระบบสแกนหาโมเดลที่ใช้งานได้จริงอัตโนมัติ ---
def find_available_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # เน้นใช้ Flash เพื่อความเร็ว ถ้าไม่ได้จะสลับไป Pro
        priority_list = ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]
        for priority in priority_list:
            if priority in available_models: return priority
        return available_models[0] if available_models else None
    except Exception as e:
        st.error(f"ไม่สามารถสแกนหาโมเดลได้: {e}")
        return None

# --- 2. Prompt สำหรับ Agent 2 (ย้อนกลับไปใช้ตัวที่เสถียรที่สุด) ---
AGENT2_PROMPT = """
คุณคือ Electrical Auditor หน้าที่คือสกัดข้อมูลจาก Load Schedule ใน PDF 
กฎเหล็ก (Strict Rules):
1. **ชื่อแผงต้องแม่นยำ**: ตรวจสอบชื่อแผงให้ดี เช่น "LC1B" ห้ามอ่านผิดเป็น "LC10" 
2. **ต้องมี MAIN BREAKER**: สกัด Main Breaker ของทุกตู้ (DB1, DB3, LC32 ฯลฯ) เป็นบรรทัดแรกเสมอ
3. **ตรวจสอบ LC32**: 3 วงจรสุดท้ายของ LC32 ในหน้าแบบระบุว่าเป็น ELCB/RCCB ต้องลงเป็น "ELCB" เท่านั้น ห้ามลงเป็น Breaker ธรรมดา
4. **ห้ามตัดสินใจเอง**: ยึดตามแบบ 100% (Strictly follow drawing)
5. **การเว้นบรรทัด**: เมื่อจบข้อมูลแต่ละตู้ ให้เว้น 2 บรรทัดและใส่เส้นคั่น (---) เพื่อให้อ่านง่าย

รูปแบบผลลัพธ์:
[ชื่อตู้]
PANEL | DEVICE | POLE | AMP | DESCRIPTION
------------------------------------------
(รายการอุปกรณ์...)
"""

def main():
    # 1. รายงานเวอร์ชันที่ Streamlit UI
    st.title("📑 Agent 2: Load Schedule Auditor")
    st.markdown(f"**Current Version:** `1.3.0` (Stable Rollback)")
    st.divider()

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_pdf = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 1. เริ่มสกัดข้อมูล (Audit Mode)", use_container_width=True):
        if uploaded_pdf:
            temp_fn = f"temp_{int(time.time())}.pdf"
            try:
                with st.spinner("🔍 กำลังค้นหาโมเดลและเตรียมประมวลผล..."):
                    working_model = find_available_model()
                    if not working_model: return
                
                with open(temp_fn, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())
                google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")
                
                model = genai.GenerativeModel(model_name=working_model)
                with st.spinner(f"⏳ กำลังวิเคราะห์ข้อมูล (Ver 1.3.0)..."):
                    response = model.generate_content([google_file, AGENT2_PROMPT])
                    
                    if response.text:
                        st.markdown(f"### 📋 ผลการสกัดข้อมูล (Code Version: 1.3.0)")
                        st.code(response.text, language="text")
                        st.success(f"✅ สกัดข้อมูลสำเร็จด้วยโมเดล {working_model}")
                    
                    google_file.delete()
            except Exception as e:
                st.error(f"❌ ข้อผิดพลาด: {str(e)}")
            finally:
                if os.path.exists(temp_fn): os.remove(temp_fn)
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
