import streamlit as st
import pandas as pd
from datetime import date, timedelta
import re
import matplotlib.pyplot as plt
import io

# ==========================================
# 1. SECURITY SYSTEM
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "bms123": 
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown('<div style="margin-top:15vh; text-align:center;">', unsafe_allow_html=True)
        st.title("🔒 O+Y Calculator Pro")
        st.text_input("Enter Password to Access", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่ครับ")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if check_password():
    # ==========================================
    # 2. SETUP & CSS
    # ==========================================
    st.set_page_config(page_title="O+Y Calculator Pro", layout="wide", initial_sidebar_state="expanded")

    DEEP_BLUE = "#004080"      
    OPDIVO_BLUE = "#007AFF"
    YERVOY_ORANGE = "#FF9500"
    SOFT_GRAY = "#EFF1F5" 

    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; background-color: {SOFT_GRAY}; }}

        .block-container {{ padding-top: 3rem !important; padding-bottom: 2rem !important; }}

        .app-branding {{ margin-bottom: 30px; }}
        .app-title-luxury {{
            font-size: 28px; font-weight: 700;
            background: -webkit-linear-gradient(left, {DEEP_BLUE}, {YERVOY_ORANGE});
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: -1.5px; margin-bottom: 2px;
        }}
        .app-subtitle-luxury {{ font-size: 10px; color: #86868B; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; }}
        
        .ind-title {{ font-size: 20px; font-weight: 700; color: {DEEP_BLUE}; margin-top: 5px; margin-bottom: 4px; }}
        .protocol-sub {{ font-size: 13px; color: #666; margin-bottom: 20px; }}

        .card-wrapper {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 25px; width: 100%; }}
        .phase-card {{
            flex: 1; min-width: 200px; background: #FFFFFF; padding: 18px;
            border-radius: 18px; 
            border: 1px solid #D1D1D6; 
            border-left-width: 8px; 
            box-shadow: 0 6px 16px rgba(0,0,0,0.08); 
        }}
        .phase-card.p1 {{ border-left-color: {OPDIVO_BLUE}; }}
        .phase-card.p2 {{ border-left-color: {YERVOY_ORANGE}; }}
        
        .card-label {{ font-size: 10px; color: #86868B; font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }}
        .card-value {{ font-size: 22px; font-weight: 700; color: #1D1D1F; }}
        .card-vat {{ font-size: 11px; color: {OPDIVO_BLUE}; margin-top: 4px; }}

        .grand-box {{
            background: linear-gradient(90deg, #007AFF 0%, #5856D6 50%, #FF9500 100%);
            padding: 22px; border-radius: 20px; color: #FFFFFF; 
            margin-bottom: 30px; 
            box-shadow: 0 10px 25px rgba(88, 86, 214, 0.3); 
        }}
        .metric-sub {{ font-size: 10px; opacity: 0.85; text-transform: uppercase; font-weight: 600; }}
        .metric-main {{ font-size: 24px; font-weight: 700; margin: 2px 0; }}
        .grand-vat {{ font-size: 11px; opacity: 0.9; margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 10px; }}

        .policy-box {{
            background: #FFFFFF; padding: 20px; border-radius: 18px; 
            border-left: 6px solid {DEEP_BLUE}; margin-bottom: 50px; 
            border: 1px solid #E5E5EA;
            border-left-width: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); font-size: 13px;
        }}

        iframe[title="streamlit_option_menu.option_menu"] {{ width: 100% !important; }}
        
        .comp-container {{
            background-color: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 12px; 
            padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;
        }}
        .comp-title {{ font-size: 14px; font-weight: 600; color: #333; }}
        .comp-val {{ font-size: 14px; font-weight: 700; color: #004080; }}
        .comp-diff {{ font-size: 12px; font-weight: 500; }}
        .diff-pos {{ color: #28a745; }} 
        .diff-neg {{ color: #dc3545; }} 

        footer {{visibility: hidden;}}
        </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # 3. CORE LOGIC
    # ==========================================
    def get_val(val):
        if pd.isna(val) or str(val).strip() in ['', '-', 'nan']: return 0.0
        s = str(val).replace(',', '').strip()
        match = re.search(r"(\d+(\.\d+)?)", s)
        return float(match.group(1)) if match else 0.0

    def calculate_vials(mg_needed, drug_type, available_stock, multiplier=1.0):
        if mg_needed <= 0: return 0.0, "-"
        # 🟢 PRICE UPDATED: Yervoy 50mg = 63,558 THB
        prices = {'O_40': 23540, 'O_100': 58850, 'O_120': 70620, 'Y_50': 63558}
        options = []
        if drug_type == 'O':
            for s in [40, 100, 120]:
                if s in available_stock: options.append((s, prices[f'O_{s}'] * multiplier))
        else: options.append((50, prices['Y_50'] * multiplier))
        memo = {}
        def solve(rem_mg):
            if rem_mg <= 0: return 0, {}, 0
            if rem_mg in memo: return memo[rem_mg]
            best_cost, best_combo, min_vials = float('inf'), {}, float('inf')
            for size, price in options:
                res_cost, res_combo, res_vials = solve(rem_mg - size)
                current_cost, current_vials = price + res_cost, 1 + res_vials
                if current_cost < best_cost or (current_cost == best_cost and current_vials < min_vials):
                    best_cost, min_vials = current_cost, current_vials
                    best_combo = res_combo.copy()
                    best_combo[size] = best_combo.get(size, 0) + 1
            memo[rem_mg] = (best_cost, best_combo, min_vials)
            return best_cost, best_combo, min_vials
        cost, combo, _ = solve(mg_needed)
        details = [f"{s}mg x {count}" for s, count in sorted(combo.items(), reverse=True)]
        return cost, ", ".join(details)

    def run_simulation(row, weight, stock_o, multiplier, start_dt, skip_wknd):
        p1_limit, p1_o_freq = int(get_val(row.get('P1_Cycle_Limit'))), max(1, int(get_val(row.get('P1_O_Freq_Weeks', 2))))
        p1_y_freq, cap_limit = max(1, int(get_val(row.get('P1_Y_Freq_Weeks', p1_o_freq)))), int(get_val(row.get('PAP_Cap_Months', 10)))
        has_p2 = pd.notna(row.get('P2_O_Dose')) and str(row.get('P2_O_Dose', '-')).strip() not in ['', '-', '0']
        
        timeline, total_paid, curr_date, cycle, weeks = [], 0.0, start_dt, 1, 1 
        o_admin_total, y_admin_total, o_paid_accum, p1_c, p2_c = 0, 0, 0.0, 0.0, 0.0

        while weeks <= 104:
            is_p1 = (cycle <= p1_limit)
            if not is_p1 and not has_p2: break
            display_date = curr_date
            if skip_wknd:
                if display_date.weekday() == 5: display_date += timedelta(days=2)
                elif display_date.weekday() == 6: display_date += timedelta(days=1)
            curr_m, freq = ((weeks - 1) // 4) + 1, (p1_o_freq if is_p1 else max(1, int(get_val(row.get('P2_Freq_Weeks')))))
            o_mg = get_val(str(row.get('P1_O_Dose' if is_p1 else 'P2_O_Dose'))) * (weight if 'mg/kg' in str(row.get('P1_O_Dose' if is_p1 else 'P2_O_Dose')).lower() else 1)
            y_mg = get_val(str(row.get('P1_Y_Dose', '0'))) * (weight if 'mg/kg' in str(row.get('P1_Y_Dose')).lower() else 1) if (is_p1 and (weeks - 1) % p1_y_freq == 0) else 0.0
            o_cost, o_v = calculate_vials(o_mg, 'O', stock_o, multiplier)
            y_cost, y_v = calculate_vials(y_mg, 'Y', [50], multiplier)
            o_p, y_p, status_msg = 0.0, 0.0, ""
            if o_mg > 0 and curr_m <= cap_limit:
                o_admin_total += 1
                if o_admin_total % 2 != 0:
                    o_p, status_msg = (o_cost, "") if (((weeks + freq - 1) // 4) + 1) <= cap_limit else (o_cost * 0.5, " (Pay 50%)")
                    o_paid_accum += (1.0 if "50%" not in status_msg else 0.5)
            if y_mg > 0 and curr_m <= cap_limit:
                y_admin_total += 1
                if y_admin_total % 2 != 0:
                    y_p = y_cost if (((weeks + p1_y_freq - 1) // 4) + 1) <= cap_limit else y_cost * 0.5
            total_paid += (o_p + y_p)
            if is_p1 and p1_c == 0 and (o_p + y_p) > 0: p1_c = (o_p + y_p)
            if not is_p1 and p2_c == 0 and (o_p + y_p) > 0: p2_c = (o_p + y_p)
            timeline.append({"Phase": f"Phase {1 if is_p1 else 2}", "Cycle": cycle, "RawDate": display_date, "Date": display_date.strftime("%d %b %Y (%a)"),"Month": curr_m, "Opdivo Vials": o_v, "Yervoy Vials": y_v if y_mg > 0 else "-", "Opdivo (฿)": o_p, "Yervoy (฿)": y_p, "Total (฿)": (o_p + y_p), "Status": f"Paid{status_msg}" if (o_p + y_p) > 0 else "Free"})
            weeks, cycle, curr_date = weeks + freq, cycle + 1, curr_date + timedelta(weeks=freq)
        
        return total_paid, o_paid_accum, p1_c, p2_c, pd.DataFrame(timeline), cap_limit, has_p2

    # ==========================================
    # 4. EXPORT FUNCTION
    # ==========================================
    def generate_image(ind, reg, weight, markup, sector, p1, p2, total, rounds, df, cap_limit):
        df_display = df[df['Month'] <= (cap_limit + 1)].copy()
        num_rows = len(df_display) + 1
        height = 5.0 + (num_rows * 0.5)
        fig, ax = plt.subplots(figsize=(15, height)) 
        ax.axis('off')
        
        # Header include Sector
        header_text = (
            f"O+Y Treatment Expense Summary | Sector: {sector}\n"
            f"----------------------------------------------------------------------------------------------------\n"
            f"Indication: {ind}\n"
            f"Regimen:    {reg}\n"
            f"Weight:     {weight} kg  |  Hospital Markup: {markup}%\n"
            f"PAP Policy: Capped at {cap_limit} months\n\n"
            f"Cost per Cycle (Phase 1): {p1:,.0f} THB\n"
            f"Cost per Cycle (Phase 2): {p2:,.0f} THB\n"
            f"----------------------------------------------------------------------------------------------------\n"
            f"Summary - Patient Paid Rounds: {rounds:.1f} Cycles\n"
            f"Estimated Total Investment:     {total:,.0f} THB\n"
        )
        
        ax.text(0.05, 0.98, header_text, transform=ax.transAxes, fontsize=11, va='top', ha='left', family='monospace', linespacing=1.4)
        cols = ["Phase", "Cycle", "Date (DD/MM/YY)", "Month", "Opdivo Vials", "Yervoy Vials", "Opdivo (THB)", "Yervoy (THB)", "Total (THB)"]
        table_data = [cols]
        for _, r in df_display.iterrows():
            short_date = r['RawDate'].strftime("%d/%m/%Y")
            table_data.append([
                r['Phase'], r['Cycle'], short_date, r['Month'], 
                r['Opdivo Vials'].replace(', ', '\n'), 
                r['Yervoy Vials'].replace(', ', '\n'),
                f"{r['Opdivo (฿)']:,.0f}", f"{r['Yervoy (฿)']:,.0f}", f"{r['Total (฿)']:,.0f}"
            ])
        
        table_height = (num_rows * 0.5) / height
        the_table = ax.table(cellText=table_data, loc='bottom', bbox=[0.02, 0.05, 0.96, table_height], cellLoc='center')
        the_table.auto_set_font_size(False); the_table.set_fontsize(10); the_table.scale(1, 2.0) 
        for (i, j), cell in the_table.get_celld().items():
            cell.set_edgecolor('#DDDDDD')
            if i == 0: cell.set_facecolor('#004080'); cell.set_text_props(color='white', weight='bold')
            else:
                is_free = "Free" in str(df_display.iloc[i-1]['Status'])
                if is_free: cell.set_facecolor('#F9F9F9'); cell.set_text_props(color='#888888')
                else: cell.set_facecolor('white' if i % 2 != 0 else '#F2F5F8')
        
        buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); buf.seek(0); plt.close(fig)
        return buf

    # ==========================================
    # 5. RENDER UI
    # ==========================================
    @st.cache_data
    def load_data(tab_name):
        sheet_id = "1YXD44pN5mLwazxOiXCHHcylvB082jdtNivXX4VpXdJM"
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
        return pd.read_csv(url)

    with st.sidebar:
        st.markdown('<div class="app-branding"><div class="app-title-luxury">O+Y Calculator</div><div class="app-subtitle-luxury">Precision PAP Support</div></div>', unsafe_allow_html=True)
        
        # 🔵 Try-Except for Option Menu (Fallback system)
        try:
            from streamlit_option_menu import option_menu
            sector = option_menu(
                menu_title=None, 
                options=["Government", "Private"], 
                icons=["bank", "building"], 
                default_index=0, 
                orientation="horizontal",
                manual_select=False,
                styles={
                    "container": { "padding": "0!important", "background-color": "#FFFFFF", "border": "1px solid #E5E5EA", "border-radius": "12px", "margin-bottom": "25px", "display": "grid", "grid-template-columns": "1fr 1fr" },
                    "icon": {"color": "#FF9500", "font-size": "18px"}, 
                    "nav-link": { "font-size": "13px", "font-weight": "500", "margin":"0px", "padding": "10px", "text-align": "center", "display": "flex", "flex-direction": "column", "align-items": "center", "justify-content": "center", "height": "100%" },
                    "nav-link-selected": { "background-color": "#004080", "color": "white", "font-weight": "600" },
                }
            )
        except ImportError:
            st.warning("⚠️ Module 'streamlit-option-menu' not found. Using standard buttons.")
            sector = st.radio("Select Sector", ["Government", "Private"], horizontal=True)
        
        df = load_data(sector)
        weight = st.number_input("Patient Weight (kg)", 1.0, 150.0, 60.0, step=0.5)
        ind = st.selectbox("Select Indication", df['Indication_Group'].dropna().unique())
        subset = df[df['Indication_Group'] == ind]
        reg = st.radio("Protocol", subset['Regimen_Name'])
        markup = st.slider("Hospital Markup (%)", 0, 100, 0)
        
        # 🟢 NEW: MARKUP PREVIEW (Opdivo 100mg Reference)
        base_price = 58850 # Opdivo 100mg Base
        marked_price = base_price * (1 + markup/100)
        st.caption(f"💡 Ref (O_100): ฿{base_price:,.0f} ➡️ **฿{marked_price:,.0f}**")
        
        st.markdown("---")
        with st.expander("🛠️ Advanced Settings"):
            start_dt = st.date_input("First Dose Date", date.today())
            skip_wk = st.checkbox("Skip Weekend Appointments", value=True)
            stock = st.multiselect("Vials in Stock", [40, 100, 120], default=[40, 100, 120])
        if st.button("🚪 Logout"): del st.session_state["password_correct"]; st.rerun()

    # --- MAIN SIMULATION ---
    sel_row = subset[subset['Regimen_Name'] == reg].iloc[0]
    total_val, o_rounds, p1_c, p2_c, df_res, cap_val, has_p2_flag = run_simulation(sel_row, weight, stock, (1 + markup/100), start_dt, skip_wk)

    # --- DISPLAY ---
    st.markdown(f'<div class="ind-title">{ind}</div><div class="protocol-sub">Regimen: {reg} | Sector: {sector}</div>', unsafe_allow_html=True)
    phase_html = f'<div class="card-wrapper"><div class="phase-card p1"><div class="card-label">Phase 1 / Cycle</div><div class="card-value">฿ {p1_c:,.0f}</div><div class="card-vat">● Inclusive of 7% VAT</div></div>'
    if has_p2_flag or p2_c > 0:
        phase_html += f'<div class="phase-card p2"><div class="card-label">Phase 2 / Cycle</div><div class="card-value">฿ {p2_c:,.0f}</div><div class="card-vat">● Inclusive of 7% VAT</div></div>'
    st.markdown(phase_html + "</div>", unsafe_allow_html=True)

    # 🟢 AUTO-COMPARE
    other_regimens = subset[subset['Regimen_Name'] != reg]
    if not other_regimens.empty:
        with st.expander(f"⚖️ Compare with other {ind} protocols", expanded=False):
            st.markdown(f"**Comparing with current selection ({reg}):**")
            for _, other_row in other_regimens.iterrows():
                other_name = other_row['Regimen_Name']
                other_res = run_simulation(other_row, weight, stock, (1 + markup/100), start_dt, skip_wk)
                other_total = other_res[0]
                diff = other_total - total_val
                diff_text = f"+฿ {diff:,.0f}" if diff > 0 else f"-฿ {abs(diff):,.0f}"
                diff_color = "diff-neg" if diff > 0 else "diff-pos"
                icon = "🔺" if diff > 0 else "🔻"
                st.markdown(f"""<div class="comp-container"><div><div class="comp-title">{other_name}</div><div class="comp-diff {diff_color}">{icon} {diff_text} vs current</div></div><div class="comp-val">฿ {other_total:,.0f}</div></div>""", unsafe_allow_html=True)

    st.markdown(f'<div class="grand-box"><div style="display: flex; justify-content: space-between; align-items: flex-end;"><div><div class="metric-sub">Total Patient Pay</div><div class="metric-main">฿ {total_val:,.0f}</div><div class="grand-vat">● Includes 7% VAT and {markup}% Hospital Markup</div></div><div style="text-align: right;"><div class="metric-sub">Paid Rounds (Opdivo)</div><div class="metric-main">{o_rounds:.1f} Cycles</div></div></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="policy-box"><b>PAP Policy:</b> Payment capped at <b>{cap_val} months</b>. Medication beyond the cap is free until PD or max 2 years.</div>', unsafe_allow_html=True)
    st.dataframe(df_res.drop(columns=['RawDate']).style.format({"Opdivo (฿)": "{:,.0f}", "Yervoy (฿)": "{:,.0f}", "Total (฿)": "{:,.0f}"}), use_container_width=True, height=500, hide_index=True)

    st.markdown("---")
    if st.button("📸 Generate Summary Image"):
        with st.spinner("Generating Image..."):
            img_buf = generate_image(ind, reg, weight, markup, sector, p1_c, p2_c, total_val, o_rounds, df_res, cap_val)
            st.download_button(label="⬇️ Download PNG Report", data=img_buf, file_name=f"OY_Plan_{sector}_{ind}.png", mime="image/png")

    # 🟢 NEW: SMART TEXT (Hidden in Expander)
    st.markdown("---")
    with st.expander("💬 กดเพื่อดูข้อความสำหรับส่ง LINE", expanded=False):
        p1_o_dose_raw = str(sel_row.get('P1_O_Dose'))
        p1_o_mg = get_val(p1_o_dose_raw) * (weight if 'mg/kg' in p1_o_dose_raw.lower() else 1)
        _, p1_o_vials_txt = calculate_vials(p1_o_mg, 'O', stock, (1 + markup/100))
        
        p1_y_dose_raw = str(sel_row.get('P1_Y_Dose', '0'))
        p1_y_mg = get_val(p1_y_dose_raw) * (weight if 'mg/kg' in p1_y_dose_raw.lower() else 1)
        _, p1_y_vials_txt = calculate_vials(p1_y_mg, 'Y', [50], (1 + markup/100))
        
        freq_weeks = max(1, int(get_val(sel_row.get('P1_O_Freq_Weeks', 2))))
        
        copy_text = f"""สรุปแผนการรักษา (O+Y PAP) สำหรับคนไข้ {ind}

👤 น้ำหนัก: {weight} kg
Indication: {ind}
Protocol: {reg}

📅 รอบการให้ยา (Cycle): ทุกๆ {freq_weeks} สัปดาห์

💉 ขนาดยาที่ใช้ (Phase 1):
- Opdivo: {p1_o_mg:.0f} mg ({p1_o_vials_txt})
- Yervoy: {p1_y_mg:.0f} mg ({p1_y_vials_txt})

💰 สรุปค่าใช้จ่าย:
- Phase 1 (O+Y): ฿{p1_c:,.0f} / รอบ
- Phase 2 (O only): ฿{p2_c:,.0f} / รอบ
- ราคารวมทั้งคอร์ส (ประมาณ): ฿{total_val:,.0f}

✅ สิทธิประโยชน์ PAP:
ชำระเพียง {cap_val} เดือนแรก (ประมาณ {o_rounds:.1f} รอบ) หลังจากนั้นรับยาฟรีจนกว่าจะ PD (หรือสูงสุด 2 ปี)"""
        st.code(copy_text, language="text")
