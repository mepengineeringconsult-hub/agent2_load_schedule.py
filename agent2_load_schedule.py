# CODE VERSION: 2.1.0
# STATUS: Iterative Mode + Multi-Column Cross-Check (Fixing LC32 Circuit 14, 16, 18)

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
    # รายงาน Version บนหน้าจอ Streamlit ตามสั่ง
    st.title("📑 Agent 2: Load Schedule Auditor version 2.1.0")
    st.info("💡 โหมดตรวจสอบละเอียด: Cross-check ทุกคอลัมน์เพื่อหา ELCB/RCCB")
    st.markdown("---")

    api_key = st.secrets.get("API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ ไม่พบ API_KEY ใน Secrets")
        return
    genai.configure(api_key=api_key)

    uploaded_pdf = st.file_uploader("อัปโหลดแบบ PDF (Load Schedule)", type="pdf")

    if st.button("🔍 เริ่มสกัดข้อมูล (Audit v2.1.0)", use_container_width=True):
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
                with st.spinner("🔍 Phase 1: กำลังสแกนหาชื่อแผงทั้งหมด..."):
                    scan_prompt = "List all electrical panel names in this PDF (e.g. DB1, LC32). Return as comma-separated list."
                    scan_res = model.generate_content([google_file, scan_prompt])
                    panel_names = [p.strip() for p in scan_res.text.split(',') if p.strip()]
                    st.write(f"📋 แผงที่ตรวจพบ: {', '.join(panel_names)}")

                # --- PHASE 2: Detailed Loop Extract ---
                all_results = []
                progress_bar = st.progress(0)
                
                for idx, name in enumerate(panel_names):
                    with st.spinner(f"⏳ Phase 2: กำลังสกัดข้อมูลแผง {name}..."):
                        # ปรับ Prompt ให้ Cross-check ข้อความ ELCB จากทุกที่ในบรรทัด
                        extract_prompt = f"""
                        Extract the Load Schedule for panel '{name}'.
                        STRICT RULES for Device Type Identification:
                        1. **Search Everywhere**: Look at BOTH the 'Device' column and 'Description/Remarks' column for each circuit.
                        2. **ELCB Priority**: If the word 'ELCB', 'RCCB', 'RCD', or 'Safety Breaker' appears ANYWHERE in the row (even in the description), you MUST label the device as 'ELCB'.
                        3. **Verify LC32 Circuits**: Pay extreme attention to circuits 14, 16, and 18. If they are used for Receptacles/Kitchen and have ELCB markings, they must be 'ELCB'.
                        4. **Main Breaker**: Always include the Main Breaker as the first line.
                        
                        Format: PANEL | DEVICE | POLE | AMP | DESCRIPTION
                        """
                        response = model.generate_content([google_file, extract_prompt])
                        all_results.append(response.text)
                        progress_bar.progress((idx + 1) / len(panel_names))

                # --- PHASE 3: Display ---
                st.markdown(f"### 📋 รายงานการสกัดข้อมูล (Version 2.1.0)")
                st.code("\n\n---\n\n".join(all_results), language="text")
                st.success(f"✅ สำเร็จ! โปรดตรวจสอบวงจร 14, 16, 18 ของ LC32 อีกครั้ง")

                google_file.delete()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
            finally:
                if os.path.exists(temp_fn): os.remove(temp_fn)
        else:
            st.warning("กรุณาอัปโหลดไฟล์ PDF")

if __name__ == "__main__": main()
