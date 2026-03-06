import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================
# ⚙️ 1. ตั้งค่าหน้าเพจ & คำนวณพื้นฐาน
# ==========================================
st.set_page_config(page_title="Smart Health Diary", page_icon="🥗", layout="wide")

st.title("🥗 Smart Health Diary")
st.write(f"สวัสดีค่ะเจ้านาย! วันนี้วันที่ **{datetime.now().strftime('%d/%m/%Y')}** เจนนี่พร้อมบันทึกไดอารีแล้วค่ะ")

# เอาลิงก์ Google Sheets ของเจ้านายมาวางในบรรทัดนี้เลยค่ะ!! 👇
SHEET_URL = "ใส่ลิงก์_Google_Sheets_ของเจ้านายตรงนี้"

# ฟังก์ชันคำนวณ BMR (สำหรับผู้ชาย)
def calculate_bmr(weight, height, age):
    return (10 * weight) + (6.25 * height) - (5 * age) + 5

# ==========================================
# 🔗 2. เชื่อมต่อฐานข้อมูล Google Sheets
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # บังคับระบุ Spreadsheet URL ตรงนี้เลย หมดปัญหาหาไม่เจอ!
    food_db = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet2")
    food_db = food_db.dropna(subset=['Menu_Name (ชื่อเมนู)'])
except Exception as e:
    st.error(f"⚠️ เจนนี่เชื่อมต่อ Google Sheets ไม่ได้ค่ะ: {e}")
    st.stop()

def get_calories(menu_name):
    if menu_name == "-" or pd.isna(menu_name):
        return 0
    cal = food_db.loc[food_db['Menu_Name (ชื่อเมนู)'] == menu_name, 'Calories (kcal)'].values
    return int(cal[0]) if len(cal) > 0 else 0

main_menus = ["-"] + food_db[food_db['Category (หมวดหมู่)'] == 'Main']['Menu_Name (ชื่อเมนู)'].tolist()
drink_menus = ["-"] + food_db[food_db['Category (หมวดหมู่)'] == 'Drink']['Menu_Name (ชื่อเมนู)'].tolist()
addon_menus = ["-"] + food_db[food_db['Category (หมวดหมู่)'] == 'Add-on']['Menu_Name (ชื่อเมนู)'].tolist()

# ==========================================
# 👤 3. ข้อมูลเจ้านาย & คำนวณ TDEE
# ==========================================
with st.sidebar:
    st.header("👤 ข้อมูลเจ้านายวันนี้")
    weight = st.number_input("น้ำหนักตัว (kg)", value=80.7, step=0.1)
    age = st.number_input("อายุ (ปี)", value=48)
    height = st.number_input("ส่วนสูง (cm)", value=178)
    
    bmr = calculate_bmr(weight, height, age)
    daily_baseline_tdee = bmr * 1.2
    st.info(f"🔥 BMR: {bmr:.0f} kcal\n\n⚡ Baseline TDEE: {daily_baseline_tdee:.0f} kcal")

# ==========================================
# 🍽️ 4. บันทึกอาหาร (5 มื้อ) & กิจกรรม
# ==========================================
st.header("📝 บันทึกข้อมูลประจำวัน")
col1, col2 = st.columns([2, 1])
total_intake_kcal = 0
meal_data = {}

with col1:
    st.subheader("🍽️ รายการอาหาร")
    for i in range(1, 6):
        with st.expander(f"มื้อที่ {i}", expanded=(i==1)):
            c1, c2, c3 = st.columns(3)
            m_main = c1.selectbox(f"อาหารหลัก #{i}", main_menus, key=f"main_{i}")
            m_drink = c2.selectbox(f"เครื่องดื่ม #{i}", drink_menus, key=f"drink_{i}")
            m_addon = c3.selectbox(f"ของเสริม #{i}", addon_menus, key=f"addon_{i}")
            
            meal_data[f"M{i}_Main"] = m_main
            meal_data[f"M{i}_Drink"] = m_drink
            meal_data[f"M{i}_Addon"] = m_addon
            total_intake_kcal += get_calories(m_main) + get_calories(m_drink) + get_calories(m_addon)

with col2:
    st.subheader("🏃‍♂️ การใช้พลังงานเพิ่ม")
    exercise_options = {
        "ไม่ออกกำลังกาย": 0.0, "เดินเร็ว (Low Impact)": 4.3,
        "ปั่นจักรยาน": 5.5, "เวทเทรนนิ่งเบาๆ": 3.0, "ว่ายน้ำเบาๆ": 6.0
    }
    ex_type = st.selectbox("กิจกรรม", list(exercise_options.keys()))
    ex_mins = st.number_input("เวลา (นาที)", value=0, step=10)
    
    met_value = exercise_options[ex_type]
    exercise_burn = (met_value * weight * ex_mins) / 60
    total_out = daily_baseline_tdee + exercise_burn

# ==========================================
# 📊 5. สรุปผล & พยากรณ์
# ==========================================
st.divider()
st.subheader("📊 สรุปผลลัพธ์ของวันนี้")
net_balance = total_intake_kcal - total_out
weight_forecast_g = (abs(net_balance) / 7700) * 1000 if net_balance < 0 else (net_balance / 7700) * 1000

if total_intake_kcal == 0:
    status, box_color = "รอเจ้านายบันทึกอาหาร", "#95a5a6"
elif total_intake_kcal < bmr:
    status, box_color = "🔴 น้อยไป! เสี่ยงเผากล้ามเนื้อ", "#e74c3c"
elif total_intake_kcal >= bmr and total_intake_kcal < (total_out - 500):
    status, box_color = "🟡 ทานเพิ่มได้อีกนิดค่ะ", "#f1c40f"
elif total_intake_kcal >= (total_out - 500) and total_intake_kcal <= total_out:
    status, box_color = "🟢 พอดีเป๊ะ! โซนลดน้ำหนักที่ดีที่สุด", "#2ecc71"
else:
    status, box_color = "⚪ เกินเป้าหมาย พลังงานเริ่มล้น", "#bdc3c7"

st.markdown(f"""
    <div style="background-color: {box_color}; padding: 15px; border-radius: 10px; color: {'black' if box_color == '#f1c40f' else 'white'}; text-align: center;">
        <h3 style="margin: 0;">สถานะ: {status}</h3>
    </div><br>
""", unsafe_allow_html=True)

sc1, sc2, sc3, sc4 = st.columns(4)
sc1.metric("รับเข้า (กิน)", f"{total_intake_kcal} kcal")
sc2.metric("ใช้ไปทั้งหมด", f"{total_out:.0f} kcal")
sc3.metric("ส่วนต่าง (Net)", f"{net_balance:.0f} kcal")
sc4.metric("พยากรณ์น้ำหนักลดลง" if net_balance < 0 else "พยากรณ์น้ำหนักเพิ่มขึ้น", f"{weight_forecast_g:.1f} กรัม")

# ==========================================
# 💾 6. บันทึกข้อมูลลง Google Sheets
# ==========================================
if st.button("💾 บันทึกลงไดอารี (Google Sheets)", use_container_width=True):
    with st.spinner("เจนนี่กำลังจดลงสมุดให้นะคะ..."):
        # บังคับระบุ Spreadsheet URL ตรงนี้ด้วย
        current_data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1")
        
        new_row = {
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Weight_kg': weight,
            'M1_Main': meal_data['M1_Main'], 'M1_Drink': meal_data['M1_Drink'], 'M1_Addon': meal_data['M1_Addon'],
            'M2_Main': meal_data['M2_Main'], 'M2_Drink': meal_data['M2_Drink'], 'M2_Addon': meal_data['M2_Addon'],
            'M3_Main': meal_data['M3_Main'], 'M3_Drink': meal_data['M3_Drink'], 'M3_Addon': meal_data['M3_Addon'],
            'M4_Main': meal_data['M4_Main'], 'M4_Drink': meal_data['M4_Drink'], 'M4_Addon': meal_data['M4_Addon'],
            'M5_Main': meal_data['M5_Main'], 'M5_Drink': meal_data['M5_Drink'], 'M5_Addon': meal_data['M5_Addon'],
            'Total_Intake_Kcal': total_intake_kcal, 'Daily_Baseline_TDEE': daily_baseline_tdee,
            'Exercise_Type': ex_type, 'Exercise_Mins': ex_mins, 'Exercise_Burn': exercise_burn,
            'Net_Balance': net_balance, 'Age': age, 'Height': height, 'Status': status,
            'Weight_Forecast_g': weight_forecast_g if net_balance < 0 else -weight_forecast_g
        }
        
        new_df = pd.DataFrame([new_row])
        updated_data = pd.concat([current_data, new_df], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_data)
        st.success("✅ เจนนี่บันทึกข้อมูลวันนี้เรียบร้อยแล้วค่ะเจ้านาย! ยอดเยี่ยมมากเลยค่ะ")
