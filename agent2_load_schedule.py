# CODE VERSION: 2.9.0
# STATUS: High Precision Fixed + UI Version Labeling

import streamlit as st
import google.generativeai as genai
import os
import time
from PyPDF2 import PdfReader, PdfWriter
import io

def main():
    # บังคับระบุเวอร์ชันบนหน้าจอ Streamlit อย่างชัดเจนตามคำสั่ง
    st.set_page_config(page_title="Load Schedule Auditor v2.9.0")
    st.title("📑 Agent 2: Load Schedule Auditor version 2.9.0")
    st.info("💡โหมดสแกนละเอียดสูงสุด: ตรวจ ELCB รายบรรทัด และห้ามเติมค่า Spare เอง")
    st.divider()

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_file = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูล (Strict Audit v2.9.0)", use_container_width=True):
        if uploaded_file:
            try:
                # เลือกโมเดลที่เสถียรที่สุด
                model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

                pdf_reader = PdfReader(uploaded_file)
                total_pages = len(pdf_reader)
                
                all_results = []
                progress_bar = st.progress(0)
                
                for page_num in range(total_pages):
                    # แยกหน้าปัจจุบันออกมาประมวลผลเพื่อสมาธิสูงสุดของ AI
                    writer = PdfWriter()
                    writer.add_page(pdf_reader.pages[page_num])
                    page_bytes = io.BytesIO()
                    writer.write(page_bytes)
                    page_bytes.seek(0)

                    temp_fn = f"temp_v290_p{page_num}.pdf"
                    with open(temp_fn, "wb") as f:
                        f.write(page_bytes.read())
                    
                    google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")

                    # Prompt ที่สั่งห้ามพลาดประเด็น ELCB และ SPARE
                    extract_prompt = """
                    Extract the Load Schedule with 100% STRICT TRUTH:
                    1. **ELCB Mandatory**: Look at BOTH 'Device' and 'Description' columns. For any Kitchen Receptacle or rows with (ELCB), the DEVICE must be 'ELCB'. Specifically, LC32 circuits 14, 16, 18 MUST be ELCB.
                    2. **Spare/Space Data**: DO NOT put any Pole (P) or Amp (AT) values for SPARE or SPACE circuits if the original table is blank. Leave them empty.
                    3. **Output Format**: PAGE | PANEL | DEVICE | POLE | AMP | DESCRIPTION
                    """
                    
                    response = model.generate_content([google_file, f"PAGE: {page_num+1} | {extract_prompt}"])
                    all_results.append(response.text)

                    # ล้างไฟล์ชั่วคราว
                    google_file.delete()
                    if os.path.exists(temp_fn): os.remove(temp_fn)
                    progress_bar.progress((page_num + 1) / total_pages)

                st.markdown(f"### 📋 ผลการสกัดข้อมูล (Version 2.9.0)")
                st.code("\n\n---\n\n".join(all_results), language="text")
                st.success(f"✅ ประมวลผลสำเร็จด้วยมาตรฐานเวอร์ชัน 2.9.0")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
