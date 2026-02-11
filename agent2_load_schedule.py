# CODE VERSION: 2.6.0
# STATUS: Full Scale Production + Auto Page Splitting + Strict Spare/Space Rule

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
    st.info("💡 Strict Mode: แยกประมวลผลทีละหน้า + ห้ามเติมค่า Spare เอง + ตรวจละเอียด ELCB")
    st.markdown("---")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_file = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูล (Audit v2.6.0)", use_container_width=True):
        if uploaded_file:
            try:
                working_model = find_available_model()
                if not working_model: return
                model = genai.GenerativeModel(model_name=working_model)

                # อ่าน PDF เพื่อแยกหน้า
                pdf_reader = PdfReader(uploaded_file)
                total_pages = len(pdf_reader)
                st.write(f"📄 ตรวจพบเอกสารทั้งหมด: {total_pages} หน้า")

                all_results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for page_num in range(total_pages):
                    status_text.text(f"⏳ กำลังประมวลผลหน้าที่ {page_num + 1}/{total_pages}...")
                    
                    # แยกหน้าปัจจุบันออกมาเป็นไบต์
                    writer = PdfWriter()
                    writer.add_page(pdf_reader.pages[page_num])
                    page_bytes = io.BytesIO()
                    writer.write(page_bytes)
                    page_bytes.seek(0)

                    # บันทึกไฟล์ชั่วคราวเพื่ออัปโหลด
                    temp_fn = f"temp_p{page_num}_{int(time.time())}.pdf"
                    with open(temp_fn, "wb") as f:
                        f.write(page_bytes.read())
                    
                    google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")

                    # Prompt ที่รวมทุกประเด็นความถูกต้อง (Strict Rule)
                    extract_prompt = """
                    Extract the Load Schedule from this PDF page.
                    STRICT EXTRACTION RULES:
                    1. **SPARE/SPACE Restriction**: DO NOT provide Pole(P) or Amp(AT) for any SPARE or SPACE circuits unless they are explicitly written in the table. If blank in PDF, leave them blank.
                    2. **ELCB Precision**: Every row must be scanned for (ELCB) or (RCCB) symbols in both Device and Description columns. If present, the device must be labeled 'ELCB'.
                    3. **Zero Assumptions**: Only extract what is visually present in the drawing. Do not guess or auto-fill data.
                    4. **Format**: PAGE | PANEL | DEVICE | POLE | AMP | DESCRIPTION
                    """
                    
                    response = model.generate_content([google_file, f"PAGE: {page_num+1} | {extract_prompt}"])
                    all_results.append(response.text)

                    # Cleanup
                    google_file.delete()
                    if os.path.exists(temp_fn): os.remove(temp_fn)
                    progress_bar.progress((page_num + 1) / total_pages)

                # แสดงผลลัพธ์รวม
                st.markdown(f"### 📋 รายงานการสกัดข้อมูล (Version 2.6.0)")
                st.code("\n\n---\n\n".join(all_results), language="text")
                st.success(f"✅ ประมวลผลสำเร็จครบทุกหน้าด้วยความแม่นยำรายบรรทัด")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
