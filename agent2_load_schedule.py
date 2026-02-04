import streamlit as st
import google.generativeai as genai
import openpyxl
import io
import re
from collections import defaultdict

st.set_page_config(page_title="Agent 2: Load Schedule Auditor", layout="wide")

def get_working_model():
    return "gemini-1.5-flash"

def main():
    st.title("📑 Agent 2: Load Schedule Auditor")
    st.subheader("โฟกัสการแกะและเรียงลำดับอุปกรณ์ภายในตู้ไฟฟ้า")

    api_key = st.secrets.get("API_KEY")
    if api_key: genai.configure(api_key=api_key)

    uploaded_pdf = st.file_uploader("1. อัปโหลดแบบ PDF (Load Schedule Only)", type="pdf")
    uploaded_excel = st.file_uploader("2. อัปโหลด BOQ Excel (เพื่อเตรียมหยอด)", type=["xlsx"])

    if st.button("🔍 สกัดข้อมูลและจัดเรียง (Audit Mode)", use_container_width=True):
        if uploaded_pdf:
            model = genai.GenerativeModel(model_name=get_working_model())
            pdf_data = uploaded_pdf.read()
            
            # สั่ง AI สกัดข้อมูลดิบ
            prompt = "Extract all breakers from all load schedules. Format: PANEL|TYPE|AMP|POLE|DEVICE_TYPE. Do not sum, list every row."
            response = model.generate_content([{"mime_type": "application/pdf", "data": pdf_data}, prompt])
            
            raw_data = []
            for line in response.text.strip().split('\n'):
                p = line.split('|')
                if len(p) >= 5:
                    raw_data.append({
                        "panel": p[0].strip().upper(),
                        "type": p[1].strip(), # Main or Branch
                        "amp": int(re.sub(r'\D', '', p[2]) or 0),
                        "pole": int(re.sub(r'\D', '', p[3]) or 1),
                        "device": p[4].strip().upper() # CB or ELCB
                    })

            # --- LOGIC การเรียงลำดับตามความต้องการของผู้ใช้ ---
            # 1. เรียงชื่อแผง A-Z
            # 2. ในแผง: Main ขึ้นก่อน Branch
            # 3. ใน Branch: CB ขึ้นก่อน ELCB
            # 4. ในกลุ่มเดียวกัน: Pole มากไปน้อย -> Amp มากไปน้อย
            sorted_data = sorted(raw_data, key=lambda x: (
                x['panel'], 
                x['type'] != 'Main', 
                x['device'] == 'ELCB', 
                -x['pole'], 
                -x['amp']
            ))

            st.session_state['agent2_data'] = sorted_data
            st.success("✅ สกัดและจัดเรียงข้อมูลเรียบร้อยแล้ว!")

    if 'agent2_data' in st.session_state:
        st.divider()
        st.subheader("📋 รายงานการสกัดข้อมูล (Sorted Audit Report)")
        
        # แสดงผลแบบตารางที่หน้าจอ (IO) ให้ตรวจก่อน
        st.table(st.session_state['agent2_data'])

        if uploaded_excel and st.button("📥 ยืนยันข้อมูลและหยอดลง Excel", type="primary"):
            # Logic การหยอดจะใช้ข้อมูลที่ Sorted แล้วนี้ลงไปในไฟล์
            # (จะใช้ Logic ค้นหาแผง + Amp + Pole เหมือนเดิมแต่แม่นยำขึ้น)
            st.info("กำลังพัฒนาส่วนการ Mapping ลง Excel ให้ตรงกับลำดับใหม่...")

# เรียกใช้แอป
if __name__ == "__main__": main()
