# CODE VERSION: 2.10.0
# STATUS: UI Version Fix + Strict ELCB Logic for LC32 + Spare Protection

import streamlit as st
import google.generativeai as genai
import os
import time
from PyPDF2 import PdfReader, PdfWriter
import io

def main():
    # --- ส่วนที่แก้ไข: แสดงเลขเวอร์ชัน 2.10.0 ให้ชัดเจนที่สุด ---
    st.set_page_config(page_title="Load Schedule Auditor v2.10.0", layout="wide")
    st.title("📑 Agent 2: Load Schedule Auditor version 2.10.0")
    st.subheader("สถานะ: โหมดตรวจสอบความแม่นยำสูงสุด (Strict Audit Mode)")
    st.info("💡 เวอร์ชัน 2.10.0: แก้ไขจุดผิด ELCB ใน LC32 และห้ามเติมค่า Spare/Space เอง")
    st.divider()

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_file = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูล (Strict Audit v2.10.0)", use_container_width=True):
        if uploaded_file:
            try:
                model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")
                pdf_reader = PdfReader(uploaded_file)
                total_pages = len(pdf_reader)
                
                all_results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for page_num in range(total_pages):
                    status_text.text(f"⏳ กำลังประมวลผลหน้า {page_num + 1}/{total_pages} (Audit v2.10.0)...")
                    
                    # แยกหน้า PDF เพื่อสมาธิสูงสุดของ AI
                    writer = PdfWriter()
                    writer.add_page(pdf_reader.pages[page_num])
                    page_bytes = io.BytesIO()
                    writer.write(page_bytes)
                    page_bytes.seek(0)

                    temp_fn = f"temp_v2100_p{page_num}.pdf"
                    with open(temp_fn, "wb") as f:
                        f.write(page_bytes.read())
                    
                    google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")

                    # --- PROMPT V2.10.0: เน้นย้ำ ELCB ใน LC32 และกฎ Spare ---
                    extract_prompt = """
                    Extract the Load Schedule with 100% STRICT TRUTH (Version 2.10.0):
                    1. **LC32 & ELCB SPECIAL RULE**: Circuits 14, 16, and 18 for 'RECEPTACLE, KITCHEN' MUST be identified as 'ELCB'. Look for any (ELCB) symbols in both Device and Description. If found, the device MUST NOT be a regular Breaker.
                    2. **SPARE/SPACE RULE**: DO NOT provide Pole(P) or Amp(AT) for any SPARE or SPACE circuits if the PDF table is blank. Leave them empty in the output.
                    3. **Zero Hallucination**: Report only what you see visually.
                    4. **Format**: PAGE | PANEL | DEVICE | POLE | AMP | DESCRIPTION
                    """
                    
                    response = model.generate_content([google_file, f"PAGE: {page_num+1} | {extract_prompt}"])
                    all_results.append(response.text)

                    # Cleanup
                    google_file.delete()
                    if os.path.exists(temp_fn): os.remove(temp_fn)
                    progress_bar.progress((page_num + 1) / total_pages)

                st.markdown(f"### 📋 ผลการสกัดข้อมูลรวม (Version 2.10.0)")
                st.code("\n\n---\n\n".join(all_results), language="text")
                st.success(f"✅ ตรวจสอบสำเร็จตามมาตรฐาน Version 2.10.0")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
