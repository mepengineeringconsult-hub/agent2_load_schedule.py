# CODE VERSION: 2.4.0
# STATUS: Iterative Scanning + Enhanced ELCB Detection for LC32

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
    # 1. รายงานชื่อแอปและเวอร์ชันที่หน้าจอ Streamlit ทันทีตามที่สั่ง
    st.title("📑 Agent 2: Load Schedule Auditor version 2.4.0")
    st.info("💡 โหมดสแกนละเอียด: ตรวจสอบสัญลักษณ์ ELCB/RCCB ทุกบรรทัดโดยไม่ใช้การคาดเดา")
    st.divider()

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_pdf = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูล (Iterative Audit v2.4.0)", use_container_width=True):
        if uploaded_pdf:
            temp_fn = f"temp_{int(time.time())}.pdf"
            try:
                working_model = find_available_model()
                if not working_model: return
                model = genai.GenerativeModel(model_name=working_model)

                with open(temp_fn, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())
                google_file = genai.upload_file(path=temp_fn, mime_type="application/pdf")

                # PHASE 1: Scan for Panel Names
                with st.spinner("🔍 Phase 1: กำลังค้นหารายชื่อแผงไฟฟ้าทั้งหมด..."):
                    scan_prompt = "Identify all Electrical Panel names in this PDF. Return only a comma-separated list."
                    scan_res = model.generate_content([google_file, scan_prompt])
                    panel_names = [p.strip() for p in scan_res.text.split(',') if p.strip()]
                    st.write(f"📋 ตรวจพบแผง: {', '.join(panel_names)}")

                # PHASE 2: Detailed Loop Extract per Panel
                all_results = []
                progress_bar = st.progress(0)
                
                for idx, name in enumerate(panel_names):
                    with st.spinner(f"⏳ Phase 2: กำลังสแกนข้อมูลแผง {name} รายบรรทัด..."):
                        # ปรับ Prompt ให้ AI สังเกตทุกตัวอักษรในทุกคอลัมน์
                        extract_prompt = f"""
                        Extract the Load Schedule for panel '{name}' from the PDF.
                        STRICT EXTRACTION RULES:
                        1. **Scan Every Row**: Look for symbols like (ELCB), (RCCB), or 'leakage protection' in the entire row.
                        2. **No Assumptions**: If you see ELCB mentioned anywhere in the row (Device or Description column), label it as 'ELCB'. Otherwise, label as 'Breaker'.
                        3. **Verify LC32**: Pay extreme attention to the last circuits (14, 16, 18). If they have leakage protection markings, they MUST be 'ELCB'.
                        4. **Zero Guessing**: Do not guess device type based on description. Read from the drawing only.
                        
                        Format: PANEL | DEVICE | POLE | AMP | DESCRIPTION
                        """
                        response = model.generate_content([google_file, extract_prompt])
                        all_results.append(response.text)
                        progress_bar.progress((idx + 1) / len(panel_names))

                # PHASE 3: Display consolidated result
                st.markdown(f"### 📋 รายงานการสกัดข้อมูล (Version 2.4.0)")
                st.code("\n\n---\n\n".join(all_results), language="text")
                st.success(f"✅ สกัดข้อมูลสำเร็จด้วยมาตรฐานความแม่นยำรายแผง")

                google_file.delete()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
            finally:
                if os.path.exists(temp_fn): os.remove(temp_fn)
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__": main()
