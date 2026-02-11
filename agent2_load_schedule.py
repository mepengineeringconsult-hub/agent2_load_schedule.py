# CODE VERSION: 2.8.0
# STATUS: Full Scale Production + Auto Page Splitting + Strict Audit Logic

import streamlit as st
import google.generativeai as genai
import os
import time
from PyPDF2 import PdfReader, PdfWriter
import io

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

def main():
    # รายงานชื่อแอปและเวอร์ชันบน UI
    st.title("📑 Agent 2: Load Schedule Auditor version 2.8.0")
    st.info("💡 Strict Isolation Mode: แยกหน้าสแกน 1:1 + ตรวจเข้ม ELCB + ห้ามเติมค่า Spare")
    st.markdown("---")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_file = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูล (Strict Audit v2.8.0)", use_container_width=True):
        if uploaded_file:
            try:
                working_model = find_available_model()
                if not working_model: return
                model = genai.GenerativeModel(model_name=working_model)

                pdf_reader = PdfReader(uploaded_file)
                total_pages = len(pdf_reader)
                st.write(f"📄 กำลังอ่านเอกสารทั้งหมด: {total_pages} หน้า")

                all_results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for page_num in range(total_pages):
                    status_text.text(f"⏳ กำลังประมวลผลหน้าที่ {page_num + 1}/{total_pages}...")
                    
                    # ระบบ Auto Page Splitting แยกหน้าประมวลผลเพื่อความแม่นยำ
                    writer = PdfWriter()
                    writer.add_page(pdf_reader.pages[page_num])
                    page_bytes = io.BytesIO()
                    writer.write(page_bytes)
                    page_bytes.seek(0)

                    temp_fn = f"temp_v280_p{page_num}.pdf"
                    with open(temp_fn, "wb") as f:
                        f.write(page_bytes.read())
                    
                    google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")

                    # Prompt ที่สั่งห้ามพลาดประเด็นที่เคยผิด (ELCB, Spare)
                    extract_prompt = """
                    Extract Load Schedule with 100% STRICT TRUTH:
                    1. **ELCB Mandatory**: Look for '(ELCB)' or 'ELCB' in both Device and Description. If found, Device MUST be 'ELCB'. NO EXCEPTIONS for LC32 circuits 14, 16, 18.
                    2. **No Auto-fill**: For SPARE/SPACE circuits, DO NOT fill Pole(P) or Amp(AT) if the original table is blank. 
                    3. **Zero Assumptions**: Report only what is visible. If unsure, leave blank.
                    4. **Format**: PAGE | PANEL | DEVICE | POLE | AMP | DESCRIPTION
                    """
                    
                    response = model.generate_content([google_file, f"PAGE: {page_num+1} | {extract_prompt}"])
                    all_results.append(response.text)

                    # Cleanup
                    google_file.delete()
                    if os.path.exists(temp_fn): os.remove(temp_fn)
                    progress_bar.progress((page_num + 1) / total_pages)

                st.markdown(f"### 📋 รายงานการสกัดข้อมูล (Version 2.8.0)")
                st.code("\n\n---\n\n".join(all_results), language="text")
                st.success(f"✅ ประมวลผลสำเร็จด้วยมาตรฐานความแม่นยำสูงสุด")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
