# CODE VERSION: 2.2.0
# STATUS: Iterative Mode + Multi-Column Check (Universal Precision)

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
    # 1. รายงานเวอร์ชันที่หน้าจอ Streamlit ตามสั่ง
    st.title("📑 Agent 2: Load Schedule Auditor version 2.2.0")
    st.info("💡 โหมดตรวจสอบละเอียด: สแกนสัญลักษณ์ ELCB/RCCB จากทุกคอลัมน์ในทุกวงจร")
    st.markdown("---")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_pdf = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูล (Audit v2.2.0)", use_container_width=True):
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
                with st.spinner("🔍 Phase 1: กำลังค้นหาแผงทั้งหมด..."):
                    scan_prompt = "List all electrical panel names in this PDF. Return as comma-separated list."
                    scan_res = model.generate_content([google_file, scan_prompt])
                    panel_names = [p.strip() for p in scan_res.text.split(',') if p.strip()]
                    st.write(f"📋 ตรวจพบแผง: {', '.join(panel_names)}")

                # PHASE 2: Detailed Loop Extract
                all_results = []
                progress_bar = st.progress(0)
                
                for idx, name in enumerate(panel_names):
                    with st.spinner(f"⏳ Phase 2: กำลังสกัดข้อมูลแผง {name}..."):
                        # ปรับ Prompt ให้ตรวจสอบทุกวงจรและทุกคอลัมน์อย่างละเอียด
                        extract_prompt = f"""
                        Extract the Load Schedule for panel '{name}'.
                        STRICT EXTRACTION RULES:
                        1. **Scan Every Line**: Check every circuit row for symbols like (ELCB), (RCCB), or text 'leakage protection' in BOTH the Device and Description columns.
                        2. **Universal Detection**: If any leakage protection is mentioned for a circuit, you MUST label it as 'ELCB'.
                        3. **Main Breaker**: Always list the Main Breaker as the first line of each panel.
                        4. **Zero Guessing**: Report exactly what is shown in the drawing. Do not assume device type based on circuit name.
                        
                        Format: PANEL | DEVICE | POLE | AMP | DESCRIPTION
                        """
                        response = model.generate_content([google_file, extract_prompt])
                        all_results.append(response.text)
                        progress_bar.progress((idx + 1) / len(panel_names))

                # PHASE 3: Display consolidated result
                st.markdown(f"### 📋 รายงานการสกัดข้อมูล (Version 2.2.0)")
                st.code("\n\n---\n\n".join(all_results), language="text")
                st.success(f"✅ ประมวลผลสำเร็จด้วยมาตรฐานความแม่นยำรายบรรทัด")

                google_file.delete()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
            finally:
                if os.path.exists(temp_fn): os.remove(temp_fn)
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__": main()
