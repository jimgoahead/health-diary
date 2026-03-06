import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

st.set_page_config(page_title="Smart Health Diary V2.5", page_icon="🥗", layout="wide")

# ==========================================
# ⚙️ 1. ตั้งค่าพื้นฐาน & เชื่อมต่อฐานข้อมูล
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1xq86DKoNS1uXhk9pjB6p_QtvCyfBTGw1h2Dnx6JU2_o/edit?usp=sharing"

def calculate_bmr(weight, height=178, age=48):
    return (10 * weight) + (6.25 * height) - (5 * age) + 5

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    food_db = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet2", ttl=0).dropna(subset=['Menu_Name (ชื่อเมนู)'])
    log_data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
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

latest_weight = 80.7
if not log_data.empty and 'Weight_kg' in log_data.columns:
    valid_weights = pd.to_numeric(log_data['Weight_kg'], errors='coerce').dropna()
    if not valid_weights.empty:
        latest_weight = float(valid_weights.iloc[-1])

# ==========================================
# 📱 2. โครงสร้างหน้าจอ 
# ==========================================
st.title("🥗 Smart Health Diary")

# ------------------------------------------
# ส่วนที่ 1: ข้อมูลพื้นฐาน
# ------------------------------------------
st.subheader("ส่วนที่ 1: ข้อมูลพื้นฐาน")
col_d, col_w = st.columns(2)
record_date = col_d.date_input("📅 วันที่บันทึก", datetime.now())
weight = col_w.number_input("⚖️ น้ำหนักตัว (kg)", value=latest_weight, step=0.1)
daily_tdee = calculate_bmr(weight) * 1.2

# ------------------------------------------
# ส่วนที่ 2: บันทึกมื้ออาหาร
# ------------------------------------------
st.divider()
st.subheader("ส่วนที่ 2: บันทึกมื้ออาหาร 🍽️")

record_mode = st.radio("โหมดบันทึกอาหาร:", ["📖 เลือกจากเมนู", "✍️ กรอกแคลอรี่เอง (AI / อาหารพิเศษ)"], horizontal=True, key="record_mode")

m_main, m_drink, m_addon, custom_name = "-", "-", "-", ""
intake_kcal = 0

if record_mode == "📖 เลือกจากเมนู":
    c1, c2, c3 = st.columns(3)
    m_main = c1.selectbox("อาหารหลัก", main_menus, key="m_main")
    m_drink = c2.selectbox("เครื่องดื่ม", drink_menus, key="m_drink")
    m_addon = c3.selectbox("ของเสริม", addon_menus, key="m_addon")
    intake_kcal = get_calories(m_main) + get_calories(m_drink) + get_calories(m_addon)
    st.info(f"พลังงานมื้อนี้: **{intake_kcal} kcal**")
else:
    cc1, cc2 = st.columns(2)
    custom_name = cc1.text_input("ชื่ออาหาร (ถ้ามี)", placeholder="เช่น บุฟเฟต์หมูกระทะ", key="custom_name")
    intake_kcal = cc2.number_input("พลังงาน (kcal)", min_value=0, step=10, value=0, key="custom_kcal")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("🟢 💾 บันทึกเฉพาะมื้ออาหาร", use_container_width=True, type="primary"):
    with st.spinner("กำลังบันทึกมื้ออาหาร..."):
        new_row = {
            'Date': record_date.strftime('%Y-%m-%d'), 'Weight_kg': weight,
            'Record_Mode': record_mode, 'Menu_Main': m_main, 'Menu_Drink': m_drink, 'Menu_Addon': m_addon,
            'Custom_Name': custom_name, 'Intake_Kcal': intake_kcal,
            'Exercise_Type': "-", 'Exercise_Mins': 0, 'Exercise_Burn': 0, 'Daily_TDEE': daily_tdee
        }
        new_df = pd.DataFrame([new_row])
        updated_data = pd.concat([log_data, new_df], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_data)
        
        st.cache_data.clear()
        for key in ['record_mode', 'm_main', 'm_drink', 'm_addon', 'custom_name', 'custom_kcal']:
            if key in st.session_state:
                del st.session_state[key]
                
        st.success("✅ บันทึกมื้ออาหารเรียบร้อยค่ะ!")
        st.rerun()

# ------------------------------------------
# ส่วนที่ 3: การออกกำลังกาย
# ------------------------------------------
st.divider()
st.subheader("ส่วนที่ 3: การออกกำลังกาย 🏃‍♂️")
exercise_options = {"ไม่ออกกำลังกาย": 0.0, "เดินเร็ว (Low Impact)": 4.3, "ปั่นจักรยาน": 5.5, "เวทเทรนนิ่งเบาๆ": 3.0, "ว่ายน้ำ": 6.0}
ce1, ce2 = st.columns(2)
ex_type = ce1.selectbox("กิจกรรม", list(exercise_options.keys()), key="ex_type")
ex_mins = ce2.number_input("เวลา (นาที)", value=0, step=10, key="ex_mins")
ex_burn = (exercise_options[ex_type] * weight * ex_mins) / 60

st.markdown("<br>", unsafe_allow_html=True)

if st.button("⚪ 💾 บันทึกเฉพาะการออกกำลังกาย", use_container_width=True, type="secondary"):
    if ex_mins == 0 and ex_type != "ไม่ออกกำลังกาย":
        st.warning("เจ้านายอย่าลืมใส่เวลา (นาที) ที่ออกกำลังกายด้วยนะคะ")
    else:
        with st.spinner("กำลังบันทึกการออกกำลังกาย..."):
            new_row = {
                'Date': record_date.strftime('%Y-%m-%d'), 'Weight_kg': weight,
                'Record_Mode': "ออกกำลังกาย", 'Menu_Main': "-", 'Menu_Drink': "-", 'Menu_Addon': "-",
                'Custom_Name': "-", 'Intake_Kcal': 0,
                'Exercise_Type': ex_type, 'Exercise_Mins': ex_mins, 'Exercise_Burn': ex_burn, 'Daily_TDEE': daily_tdee
            }
            new_df = pd.DataFrame([new_row])
            updated_data = pd.concat([log_data, new_df], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_data)
            
            st.cache_data.clear()
            for key in ['ex_type', 'ex_mins']:
                if key in st.session_state:
                    del st.session_state[key]
                    
            st.success("✅ บันทึกการออกกำลังกายเรียบร้อยค่ะ!")
            st.rerun()

# ------------------------------------------
# ส่วนที่ 4: แดชบอร์ด (สถิติย้อนหลัง)
# ------------------------------------------
st.divider()
st.header("📊 ส่วนที่ 4: แดชบอร์ดและสถิติย้อนหลัง")

if not log_data.empty and 'Date' in log_data.columns:
    df = log_data.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
else:
    df = pd.DataFrame()

if df.empty:
    st.warning("ยังไม่มีข้อมูลให้แสดงผลค่ะ เจ้านายลองบันทึกข้อมูลด้านบนดูก่อนนะคะ")
else:
    df['Date_Str'] = df['Date'].dt.date
    df['Month'] = df['Date'].dt.strftime('%Y-%m')

    st.markdown("#### 🔍 ตัวกรองข้อมูลย้อนหลัง")
    
    # 1. เลือกเดือน
    months_list = sorted(df['Month'].unique().tolist(), reverse=True)
    sel_month = st.selectbox("📅 1. เลือกเดือนที่ต้องการดู", months_list)
    df_month = df[df['Month'] == sel_month]
    
    # 2. รวม Dropdown เลือกรูปแบบการแสดงผล (เรียงวันที่ล่าสุดไปเก่าสุด และปิดท้ายด้วยภาพรวม)
    days_in_month = sorted(df_month['Date_Str'].unique().tolist(), reverse=True)
    view_options = list(days_in_month) + ["รวมทั้งเดือน"]
    
    # ฟังก์ชันช่วยแต่งหน้าตาตัวเลือกให้สวยงาม
    def format_view_option(opt):
        if opt == "รวมทั้งเดือน":
            return "📊 ดูภาพรวมทั้งเดือน"
        else:
            return f"📅 ประจำวันที่ {opt}"

    sel_view = st.selectbox("📍 2. รูปแบบการแสดงผล", view_options, format_func=format_view_option)

    # ประมวลผลตามสิ่งที่เลือก
    if sel_view == "รวมทั้งเดือน":
        filtered_df = df_month
        st.info(f"**กำลังแสดงสถิติรวมของเดือน:** {sel_month}")
        avg_tdee = filtered_df['Daily_TDEE'].mean() if not filtered_df.empty else 0
        days_count = len(filtered_df['Date_Str'].unique())
        total_tdee = avg_tdee * days_count
    else:
        filtered_df = df_month[df_month['Date_Str'] == sel_view]
        st.info(f"**กำลังแสดงสถิติประจำวันที่:** {sel_view}")
        total_tdee = filtered_df['Daily_TDEE'].mean() if not filtered_df.empty else 0

    total_intake = pd.to_numeric(filtered_df['Intake_Kcal'], errors='coerce').fillna(0).sum()
    total_ex_burn = pd.to_numeric(filtered_df['Exercise_Burn'], errors='coerce').fillna(0).sum()
    total_burn = total_tdee + total_ex_burn
    net_balance = total_intake - total_burn

    c1, c2, c3 = st.columns(3)
    c1.metric("รับเข้า (กิน)", f"{total_intake:,.0f} kcal")
    c2.metric("ใช้ไป (TDEE+ออกกำลัง)", f"{total_burn:,.0f} kcal")
    c3.metric("Net Balance", f"{net_balance:,.0f} kcal", 
              delta="ลดน้ำหนักได้" if net_balance < 0 else "พลังงานเกิน",
              delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("##### 📈 เปรียบเทียบพลังงาน")
    bar_data = pd.DataFrame({
        "ประเภท": ["รับเข้า (Intake)", "ใช้ไป (Burn)"],
        "พลังงาน (kcal)": [total_intake, total_burn]
    })
    fig_bar = px.bar(bar_data, x="ประเภท", y="พลังงาน (kcal)", color="ประเภท", 
                     color_discrete_map={"รับเข้า (Intake)": "#e74c3c", "ใช้ไป (Burn)": "#2ecc71"})
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("##### 🍩 สัดส่วนแคลอรี่ที่รับเข้า")
    food_df = filtered_df[pd.to_numeric(filtered_df['Intake_Kcal'], errors='coerce').fillna(0) > 0]
    if not food_df.empty:
        pie_data = food_df.groupby('Record_Mode')['Intake_Kcal'].sum().reset_index()
        fig_pie = px.pie(pie_data, values='Intake_Kcal', names='Record_Mode', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("ไม่มีข้อมูลการทานอาหารในช่วงเวลาที่เลือกค่ะ")
