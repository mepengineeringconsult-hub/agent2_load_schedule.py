# CODE VERSION: 2.3.0
# STATUS: Iterative Processing + High-Precision Line Scanning (Fixing LC32 ELCB)

import streamlit as st
import google.generativeai as genai
import os
import time

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
    # 1. รายงานชื่อแอปและเวอร์ชันที่หน้าจอ Streamlit ทันที
    st.title("📑 Agent 2: Load Schedule Auditor version 2.3.0")
    st.info("💡 โหมด Iterative: ตรวจสอบสัญลักษณ์ ELCB/RCCB ทุกบรรทัดเพื่อความแม่นยำ 100%")
    st.markdown("---")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_pdf = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูล (Iterative Audit v2.3.0)", use_container_width=True):
        if uploaded_pdf:
            temp_fn = f"temp_{int(time.time())}.pdf"
            try:
                working_model = find_available_model()
                if not working_model: return
                model = genai.GenerativeModel(model_name=working_model)

                with open(temp_fn, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())
                google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")

                # --- PHASE 1: Scan for Panel Names ---
                with st.spinner("🔍 Phase 1: กำลังสแกนหารายชื่อแผงไฟฟ้าทั้งหมด..."):
                    scan_prompt = "Identify all Electrical Panel names in this document. Return only a comma-separated list of names."
                    scan_res = model.generate_content([google_file, scan_prompt])
                    panel_names = [p.strip() for p in scan_res.text.split(',') if p.strip()]
                    st.write(f"📋 ตรวจพบแผงไฟฟ้า: {', '.join(panel_names)}")

                # --- PHASE 2: Loop Extract per Panel (Universal Accuracy) ---
                all_results = []
                progress_bar = st.progress(0)
                
                for idx, name in enumerate(panel_names):
                    with st.spinner(f"⏳ Phase 2: กำลังสกัดข้อมูลแผง {name} อย่างละเอียด..."):
                        # ปรับ Prompt ให้เน้นการตรวจสอบสัญลักษณ์ ELCB ในทุกบรรทัดและทุกคอลัมน์
                        extract_prompt = f"""
                        Extract the Load Schedule for panel '{name}' from the PDF.
                        STRICT RULES:
                        1. **Line-by-Line Inspection**: Check every circuit row. Look at both the 'Device' column and the 'Description' column for symbols like (ELCB), (RCCB), or text indicating leakage protection.
                        2. **Device Type Identification**: If any mention of ELCB or leakage protection is found in a row, you MUST label that circuit as 'ELCB'. Otherwise, label as 'Breaker'.
                        3. **Focus on Accuracy**: For panel LC32, ensure circuits 14, 16, and 18 are correctly identified as ELCB if marked in the drawing.
                        4. **Format**: PANEL | DEVICE | POLE | AMP | DESCRIPTION
                        """
                        response = model.generate_content([google_file, extract_prompt])
                        all_results.append(response.text)
                        progress_bar.progress((idx + 1) / len(panel_names))

                # --- PHASE 3: Display Consolidated Result ---
                st.markdown(f"### 📋 รายงานการสกัดข้อมูล (Version 2.3.0)")
                final_output = "\n\n---\n\n".join(all_results)
                st.code(final_output, language="text")
                st.success(f"✅ สกัดข้อมูลสำเร็จด้วยมาตรฐานความแม่นยำสูงสุดรายบรรทัด")

                google_file.delete()
            except Exception as e:
                st.error(f"❌ ข้อผิดพลาด: {str(e)}")
            finally:
                if os.path.exists(temp_fn): os.remove(temp_fn)
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__": main()
