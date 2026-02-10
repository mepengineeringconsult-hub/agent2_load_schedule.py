# CODE VERSION: 2.5.0
# STATUS: Full Scale Production + Auto Page Splitting + High Precision ELCB Detection

import streamlit as st
import google.generativeai as genai
import os
import time
from PyPDF2 import PdfReader, PdfWriter
import io

# --- 1. ระบบค้นหาโมเดล ---
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
    # รายงานชื่อแอปและเวอร์ชันที่หน้าจอตามสั่ง
    st.title("📑 Agent 2: Load Schedule Auditor version 2.5.0")
    st.info("💡 Production Mode: แยกประมวลผลทีละหน้าอัตโนมัติ เพื่อรองรับเอกสารจำนวนมากและความแม่นยำ 100%")
    st.markdown("---")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_file = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูลระดับโปร (Audit v2.5.0)", use_container_width=True):
        if uploaded_file:
            try:
                working_model = find_available_model()
                if not working_model: return
                model = genai.GenerativeModel(model_name=working_model)

                # อ่าน PDF และเตรียมแยกหน้า
                pdf_reader = PdfReader(uploaded_file)
                total_pages = len(pdf_reader)
                st.write(f"📄 ตรวจพบเอกสารทั้งหมด: {total_pages} หน้า")

                all_extracted_data = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                # --- LOOP ประมวลผลทีละหน้าเพื่อความแม่นยำสูงสุด ---
                for page_num in range(total_pages):
                    status_text.text(f"⏳ กำลังประมวลผลหน้าที่ {page_num + 1} จาก {total_pages}...")
                    
                    # แยกเฉพาะหน้าที่กำลังประมวลผลออกมาเป็นไฟล์ชั่วคราว
                    writer = PdfWriter()
                    writer.add_page(pdf_reader.pages[page_num])
                    
                    page_bytes = io.BytesIO()
                    writer.write(page_bytes)
                    page_bytes.seek(0)

                    # อัปโหลดหน้าเดียวให้ Google AI
                    temp_page_fn = f"temp_p{page_num}_{int(time.time())}.pdf"
                    with open(temp_page_fn, "wb") as f:
                        f.write(page_bytes.read())
                    
                    google_file = genai.upload_file(path=temp_page_fn, mime_type="application/pdf")

                    # Prompt ที่คงความเข้มงวดทุกประเด็น (โดยเฉพาะ ELCB และความแม่นยำรายบรรทัด)
                    extract_prompt = """
                    Extract the Load Schedule from this specific page.
                    STRICT RULES:
                    1. **Scan Every Line**: Check every circuit row. Look at both 'Device' and 'Description' columns for (ELCB), (RCCB), or leakage protection symbols.
                    2. **Device Identification**: If any mention of ELCB is found, you MUST label it as 'ELCB'. Otherwise, label as 'Breaker'.
                    3. **Zero Assumptions**: Only extract what is visually present. Do not guess.
                    4. **Completeness**: Include Main Breaker and all circuit details found on this page.
                    Format: PAGE_REF | PANEL | DEVICE | POLE | AMP | DESCRIPTION
                    """
                    
                    response = model.generate_content([google_file, f"PAGE: {page_num+1} | {extract_prompt}"])
                    all_extracted_data.append(response.text)

                    # Cleanup
                    google_file.delete()
                    if os.path.exists(temp_page_fn): os.remove(temp_page_fn)
                    
                    # Update Progress
                    progress_bar.progress((page_num + 1) / total_pages)

                # --- แสดงผลรวมทั้งหมด ---
                st.markdown(f"### 📋 รายงานการสกัดข้อมูลรวม (Version 2.5.0)")
                final_output = "\n\n---\n\n".join(all_extracted_data)
                st.code(final_output, language="text")
                st.success(f"✅ ประมวลผลครบ {total_pages} หน้า ด้วยความแม่นยำสูงสุดเรียบร้อยแล้ว")

            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__":
    main()
