# CODE VERSION: 2.6.0
# STATUS: Strict Extraction + No Auto-fill for Spare/Space + LC32 ELCB Fixed

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
    # รายงานชื่อแอปและเวอร์ชันที่หน้าจอ
    st.title("📑 Agent 2: Load Schedule Auditor version 2.6.0")
    st.info("💡 Strict Mode: ห้ามใส่ค่า Spare เอง และเน้นความแม่นยำ ELCB รายบรรทัด")
    st.markdown("---")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_file = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูล (Strict Audit v2.6.0)", use_container_width=True):
        if uploaded_file:
            try:
                working_model = find_available_model()
                if not working_model: return
                model = genai.GenerativeModel(model_name=working_model)

                pdf_reader = PdfReader(uploaded_file)
                total_pages = len(pdf_reader)
                
                all_extracted_data = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for page_num in range(total_pages):
                    status_text.text(f"⏳ กำลังประมวลผลหน้าที่ {page_num + 1}/{total_pages}...")
                    
                    writer = PdfWriter()
                    writer.add_page(pdf_reader.pages[page_num])
                    page_bytes = io.BytesIO()
                    writer.write(page_bytes)
                    page_bytes.seek(0)

                    temp_page_fn = f"temp_v260_p{page_num}.pdf"
                    with open(temp_page_fn, "wb") as f:
                        f.write(page_bytes.read())
                    
                    google_file = genai.upload_file(path=temp_page_fn, mime_type="application/pdf")

                    # Prompt ที่ปรับปรุงตามคำสั่งล่าสุด
                    extract_prompt = """
                    Extract the Load Schedule from this page.
                    CRITICAL RULES:
                    1. **SPARE/SPACE Policy**: DO NOT provide Pole (P) or Amp (AT) for SPARE or SPACE circuits unless they are explicitly written in the table. If blank in the PDF, leave it blank in the output.
                    2. **ELCB Detection**: Scan every row carefully. For Receptacle/Kitchen or any row with ELCB/RCCB symbols, the device MUST be 'ELCB'. Pay special attention to the last rows of LC32.
                    3. **Zero Guessing**: Report exactly what you see. Do not fill in missing data based on assumptions.
                    4. **Format**: PAGE | PANEL | DEVICE | POLE | AMP | DESCRIPTION
                    """
                    
                    response = model.generate_content([google_file, f"PAGE: {page_num+1} | {extract_prompt}"])
                    all_extracted_data.append(response.text)

                    google_file.delete()
                    if os.path.exists(temp_page_fn): os.remove(temp_page_fn)
                    progress_bar.progress((page_num + 1) / total_pages)

                st.markdown(f"### 📋 รายงานการสกัดข้อมูล (Version 2.6.0)")
                st.code("\n\n---\n\n".join(all_extracted_data), language="text")
                st.success(f"✅ ประมวลผลสำเร็จตามเงื่อนไข Strict Truth")

            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
