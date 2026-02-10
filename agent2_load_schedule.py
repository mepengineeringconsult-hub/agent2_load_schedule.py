# CODE VERSION: 1.4.0
# STATUS: Rollback to Stable Base + Fixed LC32 3-circuits + UI Versioning

import streamlit as st
import google.generativeai as genai
import os
import time

# --- 1. ระบบค้นหา Model อัตโนมัติ ---
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

# --- 2. Prompt ฉบับปรับปรุงจากตัวเสถียรเดิม ---
AGENT2_PROMPT = """
คุณคือ Electrical Auditor หน้าที่คือสกัดข้อมูลจาก Load Schedule ใน PDF ทุกหน้าให้ครบถ้วน (โดยเฉพาะ DB1, DB3, LC1B)
กฎเหล็ก (Strict Rules):
1. **รายงานเลข Version**: ทุกครั้งที่สกัดข้อมูลเสร็จ ให้ขึ้นหัวแถวว่า "รายงานโดย Version 1.4.0"
2. **ต้องมี MAIN BREAKER**: สกัด Main Breaker ของทุกตู้เป็นบรรทัดแรกเสมอ
3. **ตรวจสอบ LC32 อย่างละเอียด**: 3 วงจรสุดท้ายของ LC32 ใน PDF ระบุว่าเป็นอุปกรณ์ป้องกันไฟรั่ว (ELCB/RCCB) ต้องลงข้อมูลเป็น "ELCB" เท่านั้น ห้ามลงเป็น Breaker ธรรมดาเด็ดขาด
4. **ห้ามตัดสินใจเอง**: ยึดตามแบบ 100% ตัวสะกดชื่อแผงต้องเป๊ะ เช่น LC1B ห้ามเป็น LC10
5. **การเว้นบรรทัด**: เมื่อจบข้อมูลแต่ละตู้ ให้เว้น 2 บรรทัดและใส่เส้นคั่น (---) เพื่อให้อ่านง่าย

รูปแบบผลลัพธ์:
[ชื่อตู้]
PANEL | DEVICE | POLE | AMP | DESCRIPTION
------------------------------------------
(รายการอุปกรณ์...)
"""

def main():
    # 1. แสดง Version ที่หัวข้อแอปตามที่สั่ง
    st.title("📑 Agent 2: Load Schedule Auditor version 1.4.0")
    st.markdown("---")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_pdf = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 1. เริ่มสกัดข้อมูล (Audit Mode v1.4.0)", use_container_width=True):
        if uploaded_pdf:
            temp_fn = f"temp_{int(time.time())}.pdf"
            try:
                with st.spinner("🔍 กำลังค้นหาโมเดล..."):
                    working_model = find_available_model()
                    if not working_model: return
                
                with open(temp_fn, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())
                google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")
                
                model = genai.GenerativeModel(model_name=working_model)
                with st.spinner(f"⏳ กำลังวิเคราะห์ข้อมูล (Ver 1.4.0)..."):
                    response = model.generate_content([google_file, AGENT2_PROMPT])
                    
                    if response.text:
                        st.markdown(f"### 📋 ผลการสกัดข้อมูล (Version 1.4.0)")
                        st.code(response.text, language="text")
                        st.success(f"✅ สำเร็จ! ตรวจสอบ LC32 3 วงจรสุดท้ายอีกครั้ง")
                    
                    google_file.delete()
            except Exception as e:
                st.error(f"❌ ข้อผิดพลาด: {str(e)}")
            finally:
                if os.path.exists(temp_fn): os.remove(temp_fn)
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
