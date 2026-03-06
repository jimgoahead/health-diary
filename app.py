import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Smart Health Diary V2", page_icon="🥗", layout="wide")

# ==========================================
# ⚙️ 1. ตั้งค่าพื้นฐาน & เชื่อมต่อฐานข้อมูล
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1xq86DKoNS1uXhk9pjB6p_QtvCyfBTGw1h2Dnx6JU2_o/edit?usp=sharing"

def calculate_bmr(weight, height=178, age=48):
    return (10 * weight) + (6.25 * height) - (5 * age) + 5

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    food_db = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet2").dropna(subset=['Menu_Name (ชื่อเมนู)'])
    # อ่านข้อมูล Sheet1 เพื่อดึงน้ำหนักล่าสุดและทำแดชบอร์ด
    log_data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1")
except Exception as e:
    st.error(f"⚠️ เชื่อมต่อฐานข้อมูลไม่ได้: {e}")
    st.stop()

def get_calories(menu_name):
    if menu_name == "-" or pd.isna(menu_name): return 0
    cal = food_db.loc[food_db['Menu_Name (ชื่อเมนู)'] == menu_name, 'Calories (kcal)'].values
    return int(cal[0]) if len(cal) > 0 else 0

main_menus = ["-"] + food_db[food_db['Category (หมวดหมู่)'] == 'Main']['Menu_Name (ชื่อเมนู)'].tolist()
drink_menus = ["-"] + food_db[food_db['Category (หมวดหมู่)'] == 'Drink']['Menu_Name (ชื่อเมนู)'].tolist()
addon_menus = ["-"] + food_db[food_db['Category (หมวดหมู่)'] == 'Add-on']['Menu_Name (ชื่อเมนู)'].tolist()

# หาค่าน้ำหนักล่าสุดจากฐานข้อมูลเพื่อจำค่าไว้
latest_weight = 80.7
if not log_data.empty and 'Weight_kg' in log_data.columns:
    valid_weights = log_data['Weight_kg'].dropna()
    if not valid_weights.empty:
        latest_weight = float(valid_weights.iloc[-1])

# ==========================================
# 📱 2. โครงสร้างหน้าจอ (Tabs)
# ==========================================
st.title("🥗 Smart Health Diary")
tab1, tab2 = st.tabs(["📝 บันทึกข้อมูล", "📊 แดชบอร์ด (สถิติ)"])

# ------------------------------------------
# 📝 TAB 1: หน้าบันทึกข้อมูล (Clean UX)
# ------------------------------------------
with tab1:
    st.subheader("ส่วนที่ 1: ข้อมูลพื้นฐาน")
    col_d, col_w = st.columns(2)
    record_date = col_d.date_input("📅 วันที่บันทึก (เลือกย้อนหลังได้)", datetime.now())
    weight = col_w.number_input("⚖️ น้ำหนักตัว (kg)", value=latest_weight, step=0.1)
    
    st.divider()
    st.subheader("ส่วนที่ 2: บันทึกมื้ออาหาร")
    
    # ปุ่มสลับโหมด
    record_mode = st.radio("โหมดบันทึกอาหาร:", ["📖 เลือกจากเมนู", "✍️ กรอกแคลอรี่เอง (AI / อาหารพิเศษ)"], horizontal=True)
    
    m_main, m_drink, m_addon, custom_name = "-", "-", "-", ""
    intake_kcal = 0

    if record_mode == "📖 เลือกจากเมนู":
        c1, c2, c3 = st.columns(3)
        m_main = c1.selectbox("อาหารหลัก", main_menus)
        m_drink = c2.selectbox("เครื่องดื่ม", drink_menus)
        m_addon = c3.selectbox("ของเสริม", addon_menus)
        intake_kcal = get_calories(m_main) + get_calories(m_drink) + get_calories(m_addon)
        st.info(f"พลังงานมื้อนี้: **{intake_kcal} kcal**")
    else:
        cc1, cc2 = st.columns(2)
        custom_name = cc1.text_input("ชื่ออาหาร (ถ้ามี)", placeholder="เช่น โอมากาเสะ, บุฟเฟต์")
        intake_kcal = cc2.number_input("พลังงาน (kcal)", min_value=0, step=10, value=0)

    st.divider()
    st.subheader("ส่วนที่ 3: การออกกำลังกาย")
    exercise_options = {"ไม่ออกกำลังกาย": 0.0, "เดินเร็ว (Low Impact)": 4.3, "ปั่นจักรยาน": 5.5, "เวทเทรนนิ่งเบาๆ": 3.0, "ว่ายน้ำ": 6.0}
    ce1, ce2 = st.columns(2)
    ex_type = ce1.selectbox("กิจกรรม", list(exercise_options.keys()))
    ex_mins = ce2.number_input("เวลา (นาที)", value=0, step=10)
    
    ex_burn = (exercise_options[ex_type] * weight * ex_mins) / 60
    daily_tdee = calculate_bmr(weight) * 1.2

    st.markdown("<br>", unsafe_allow_html=True)
    
    # ย้ายปุ่มเซฟมาไว้ตรงนี้ตามเจ้านายสั่ง!
    if st.button("💾 บันทึกลงไดอารี", use_container_width=True, type="primary"):
        with st.spinner("กำลังบันทึกข้อมูล..."):
            new_row = {
                'Date': record_date.strftime('%Y-%m-%d'),
                'Weight_kg': weight,
                'Record_Mode': record_mode,
                'Menu_Main': m_main, 'Menu_Drink': m_drink, 'Menu_Addon': m_addon,
                'Custom_Name': custom_name, 'Intake_Kcal': intake_kcal,
                'Exercise_Type': ex_type, 'Exercise_Mins': ex_mins,
                'Exercise_Burn': ex_burn, 'Daily_TDEE': daily_tdee
            }
            new_df = pd.DataFrame([new_row])
            updated_data = pd.concat([log_data, new_df], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_data)
            st.success("✅ บันทึกเรียบร้อย! ข้อมูลเข้าไปอยู่ในตารางแล้วค่ะ")

# ------------------------------------------
# 📊 TAB 2: หน้าแดชบอร์ด (สถิติย้อนหลัง)
# ------------------------------------------
with tab2:
    if log_data.empty or 'Date' not in log_data.columns:
        st.warning("ยังไม่มีข้อมูลให้แสดงผลค่ะ เจ้านายลองบันทึกข้อมูลหน้าแรกดูก่อนนะคะ")
    else:
        # ล้างข้อมูลที่ว่าง
        df = log_data.dropna(subset=['Date']).copy()
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        df['Month'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')

        st.subheader("🔍 ตัวกรองข้อมูล")
        months_list = sorted(df['Month'].unique().tolist(), reverse=True)
        sel_month = st.selectbox("เลือกเดือน", months_list)
        
        # กรองข้อมูลตามเดือนที่เลือก
        df_month = df[df['Month'] == sel_month]
        
        # เลือกแบบรวมทั้งเดือน หรือดูรายวัน
        days_in_month = sorted(df_month['Date'].unique().tolist(), reverse=True)
        view_type = st.selectbox("มุมมอง", ["รวมทั้งเดือน"] + days_in_month)

        if view_type == "รวมทั้งเดือน":
            filtered_df = df_month
            st.markdown(f"### สถิติรวมของเดือน: {sel_month}")
        else:
            filtered_df = df_month[df_month['Date'] == view_type]
            st.markdown(f"### สถิติประจำวันที่: {view_type}")

        # คำนวณยอดรวมต่างๆ
        total_intake = filtered_df['Intake_Kcal'].sum()
        total_ex_burn = filtered_df['Exercise_Burn'].sum()
        # TDEE ใช้ค่าเฉลี่ยของวันนั้นๆ หรือเดือนนั้นๆ
        avg_tdee = filtered_df['Daily_TDEE'].mean() if not filtered_df.empty else 0
        
        # ถ้ารวมทั้งเดือน ให้คูณ TDEE ด้วยจำนวนวันที่มีการบันทึก
        if view_type == "รวมทั้งเดือน":
            days_count = len(filtered_df['Date'].unique())
            total_tdee = avg_tdee * days_count
        else:
            total_tdee = avg_tdee

        total_burn = total_tdee + total_ex_burn
        net_balance = total_intake - total_burn

        # KPI Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("รับเข้า (กิน)", f"{total_intake:,.0f} kcal")
        c2.metric("ใช้ไป (TDEE + ออกกำลัง)", f"{total_burn:,.0f} kcal")
        c3.metric("Net Balance (ส่วนต่าง)", f"{net_balance:,.0f} kcal", 
                  delta="ลดน้ำหนักได้" if net_balance < 0 else "พลังงานเกิน",
                  delta_color="inverse")

        st.divider()
        
        # กราฟแท่ง (Intake vs Burn)
        st.subheader("📈 เปรียบเทียบพลังงาน")
        bar_data = pd.DataFrame({
            "ประเภท": ["รับเข้า (Intake)", "ใช้ไป (Burn)"],
            "พลังงาน (kcal)": [total_intake, total_burn]
        })
        fig_bar = px.bar(bar_data, x="ประเภท", y="พลังงาน (kcal)", color="ประเภท", 
                         color_discrete_map={"รับเข้า (Intake)": "#e74c3c", "ใช้ไป (Burn)": "#2ecc71"})
        st.plotly_chart(fig_bar, use_container_width=True)

        # กราฟโดนัท (สัดส่วนของอาหารที่กิน)
        st.subheader("🍩 สัดส่วนแคลอรี่ที่รับเข้า (จำแนกตามโหมด)")
        if total_intake > 0:
            pie_data = filtered_df.groupby('Record_Mode')['Intake_Kcal'].sum().reset_index()
            fig_pie = px.pie(pie_data, values='Intake_Kcal', names='Record_Mode', hole=0.4,
                             color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("ไม่พบข้อมูลการกินในหมวดหมู่นี้ค่ะ")
