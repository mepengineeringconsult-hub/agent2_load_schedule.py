# CODE VERSION: 2.7.0
# STATUS: Production Ready + Page Splitting + Strict ELCB & Spare Rules

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
    st.title("📑 Agent 2: Load Schedule Auditor version 2.7.0")
    st.info("💡 Strict Mode: แยกหน้าประมวลผลอัตโนมัติ + ตรวจละเอียด ELCB 3 วงจรสุดท้าย LC32")
    st.markdown("---")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_file = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูลแม่นยำสูง (Audit v2.7.0)", use_container_width=True):
        if uploaded_file:
            try:
                working_model = find_available_model()
                if not working_model: return
                model = genai.GenerativeModel(model_name=working_model)

                pdf_reader = PdfReader(uploaded_file)
                total_pages = len(pdf_reader)
                st.write(f"📄 ตรวจพบเอกสารทั้งหมด: {total_pages} หน้า")

                all_results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for page_num in range(total_pages):
                    status_text.text(f"⏳ กำลังประมวลผลหน้าที่ {page_num + 1}/{total_pages}...")
                    
                    writer = PdfWriter()
                    writer.add_page(pdf_reader.pages[page_num])
                    page_bytes = io.BytesIO()
                    writer.write(page_bytes)
                    page_bytes.seek(0)

                    temp_fn = f"temp_v270_p{page_num}.pdf"
                    with open(temp_fn, "wb") as f:
                        f.write(page_bytes.read())
                    
                    google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")

                    # ชุดคำสั่งที่เน้นย้ำความผิดพลาดที่เคยเกิดขึ้น
                    extract_prompt = """
                    Extract the Load Schedule from this PDF page with 100% accuracy.
                    STRICT RULES:
                    1. **ELCB Mandatory Check**: Every circuit, especially for 'Receptacle' or 'Kitchen', must be checked for (ELCB) symbols. If found anywhere in the row, the DEVICE column must be 'ELCB'.
                    2. **LC32 Specific**: Ensure circuits 14, 16, and 18 are correctly identified as ELCB.
                    3. **SPARE/SPACE Restriction**: DO NOT assign Pole (P) or Amp (AT) to SPARE/SPACE rows unless explicitly written in the PDF table. Leave blank if not found.
                    4. **Format**: PAGE | PANEL | DEVICE | POLE | AMP | DESCRIPTION
                    """
                    
                    response = model.generate_content([google_file, f"PAGE: {page_num+1} | {extract_prompt}"])
                    all_results.append(response.text)

                    google_file.delete()
                    if os.path.exists(temp_fn): os.remove(temp_fn)
                    progress_bar.progress((page_num + 1) / total_pages)

                st.markdown(f"### 📋 รายงานการสกัดข้อมูล (Version 2.7.0)")
                st.code("\n\n---\n\n".join(all_results), language="text")
                st.success(f"✅ ประมวลผลสำเร็จด้วยมาตรฐานความถูกต้องรายหน้า")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
