# CODE VERSION: 1.1.0
# UPDATE: Fixed LC32 ELCB logic & Added Panel Spacing

import streamlit as st
import google.generativeai as genai
import os
import time

# --- 1. ระบบสแกนหาโมเดลที่ใช้งานได้จริงอัตโนมัติ ---
def find_available_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_list = ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]
        for priority in priority_list:
            if priority in available_models: return priority
        return available_models[0] if available_models else None
    except Exception as e:
        st.error(f"ไม่สามารถสแกนหาโมเดลได้: {e}")
        return None

# --- 2. Prompt สำหรับ Agent 2 (ปรับปรุงเรื่อง ELCB และการเว้นบรรทัด) ---
AGENT2_PROMPT = """
คุณคือ Electrical Auditor มือโปร ภารกิจคือสกัดข้อมูลจาก Load Schedule ทุกหน้าอย่างละเอียด
กฎเหล็กในการทำงาน (Strict Rules):
1. **ต้องมี MAIN BREAKER**: ห้ามข้าม Main Breaker ของทุกตู้ (เช่น DB1, DB3, LC32) ต้องสกัดออกมาเป็นบรรทัดแรกของตู้นั้นๆ เสมอ
2. **ห้ามตัดสินใจเอง**: ยึดตามแบบ 100% (Strictly follow the PDF)
3. **ตรวจสอบ ELCB ท้ายตาราง (Focus LC32)**: ตรวจสอบ 3 วงจรสุดท้ายของ LC32 ให้ดี หากในแบบระบุว่าเป็น ELCB หรือมีเครื่องหมายกำกับว่าเป็นอุปกรณ์ป้องกันไฟรั่ว ต้องลงข้อมูลเป็น ELCB เท่านั้น ห้ามลงเป็น Breaker ธรรมดา
4. **การเว้นบรรทัด**: เมื่อจบข้อมูลของหนึ่งตู้ (Panel) ให้ทำการเว้น 2 บรรทัดก่อนเริ่มตู้ใหม่ เพื่อให้อ่านง่าย

รูปแบบผลลัพธ์:
[ชื่อตู้]
PANEL | DEVICE | POLE | AMP | DESCRIPTION
------------------------------------------
(รายการอุปกรณ์...)
"""

def main():
    st.title("📑 Agent 2: Load Schedule Auditor")
    st.caption("Code Version: 1.1.0")
    st.info("🔄 โหมด Auto-Scan Model + ตรวจสอบ ELCB ท้ายตาราง")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY")
        return
    genai.configure(api_key=api_key)

    uploaded_pdf = st.file_uploader("อัปโหลดแบบ PDF", type="pdf")

    if st.button("🔍 1. เริ่มสกัดข้อมูล (Audit Mode)", use_container_width=True):
        if uploaded_pdf:
            temp_fn = f"temp_{int(time.time())}.pdf"
            try:
                with st.spinner("🔍 กำลังสแกนหาโมเดล..."):
                    working_model = find_available_model()
                    if not working_model: return
                
                with open(temp_fn, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())
                google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")
                
                model = genai.GenerativeModel(model_name=working_model)
                with st.spinner(f"⏳ วิเคราะห์ข้อมูลด้วย {working_model}..."):
                    response = model.generate_content([google_file, AGENT2_PROMPT])
                    
                    if response.text:
                        st.markdown("### 📋 ผลการสกัดข้อมูล")
                        st.code(response.text, language="text")
                        st.success(f"✅ สำเร็จ (Version 1.1.0) - ใช้โมเดล: {working_model}")
                    
                    google_file.delete()
            except Exception as e:
                st.error(f"❌ ข้อผิดพลาด: {str(e)}")
            finally:
                if os.path.exists(temp_fn): os.remove(temp_fn)
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
