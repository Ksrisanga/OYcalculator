import streamlit as st
import pandas as pd
from datetime import date, timedelta
import re

# ==========================================
# 1. SETUP & LUXURY BRANDING CSS
# ==========================================
st.set_page_config(page_title="O+Y Calculator Pro", layout="wide", initial_sidebar_state="expanded")

DEEP_BLUE = "#004080"      
OPDIVO_BLUE = "#007AFF"
YERVOY_ORANGE = "#FF9500"
SOFT_GRAY = "#F8F9FA"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; background-color: {SOFT_GRAY}; }}

    /* ✨ LUXURY BRANDING */
    .app-branding {{ margin-bottom: 30px; }}
    .app-title-luxury {{
        font-size: 28px; font-weight: 700;
        background: -webkit-linear-gradient(left, {DEEP_BLUE}, {YERVOY_ORANGE});
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        letter-spacing: -1.5px; margin-bottom: 2px;
    }}
    .app-subtitle-luxury {{ font-size: 10px; color: #86868B; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; }}

    .ind-title {{ font-size: 20px; font-weight: 700; color: {DEEP_BLUE}; margin-top: 5px; }}
    .protocol-sub {{ font-size: 13px; color: #666; margin-bottom: 20px; }}

    /* Phase Cards Wrapper */
    .card-wrapper {{ display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 25px; width: 100%; }}
    .phase-card {{
        flex: 1; min-width: 200px; background: #FFFFFF; padding: 18px;
        border-radius: 18px; border-bottom: 4px solid #E5E5E7;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    }}
    .phase-card.p1 {{ border-bottom-color: {OPDIVO_BLUE}; }}
    .phase-card.p2 {{ border-bottom-color: {YERVOY_ORANGE}; }}
    
    .card-label {{ font-size: 10px; color: #86868B; font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }}
    .card-value {{ font-size: 22px; font-weight: 700; color: #1D1D1F; }}
    .card-vat {{ font-size: 11px; color: {OPDIVO_BLUE}; margin-top: 4px; }}

    /* Grand Box */
    .grand-box {{
        background: linear-gradient(135deg, {DEEP_BLUE} 0%, {OPDIVO_BLUE} 100%);
        padding: 22px; border-radius: 20px; color: #FFFFFF; 
        margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,91,183,0.15);
    }}
    .metric-sub {{ font-size: 10px; opacity: 0.85; text-transform: uppercase; font-weight: 600; }}
    .metric-main {{ font-size: 24px; font-weight: 700; margin: 2px 0; }}
    .grand-vat {{ font-size: 11px; opacity: 0.9; margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 10px; }}

    .policy-box {{
        background: #FFFFFF; padding: 20px; border-radius: 18px; 
        border-left: 6px solid {DEEP_BLUE}; margin-bottom: 50px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); font-size: 13px;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CORE ENGINE
# ==========================================

def get_val(val):
    if pd.isna(val) or str(val).strip() in ['', '-', 'nan']: return 0.0
    s = str(val).replace(',', '').strip()
    match = re.search(r"(\d+(\.\d+)?)", s)
    return float(match.group(1)) if match else 0.0

def calculate_vials(mg_needed, drug_type, available_stock, multiplier=1.0):
    if mg_needed <= 0: return 0.0, "-"
    prices = {'O_40': 23540, 'O_100': 58850, 'O_120': 70620, 'Y_50': 60348}
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
            if display_date.weekday() == 5: display_date += timedelta(days=2) # Sat -> Mon
            elif display_date.weekday() == 6: display_date += timedelta(days=1) # Sun -> Mon

        curr_m, freq = ((weeks - 1) // 4) + 1, (p1_o_freq if is_p1 else max(1, int(get_val(row.get('P2_Freq_Weeks')))))
        o_dose_raw = str(row.get('P1_O_Dose' if is_p1 else 'P2_O_Dose'))
        o_mg = get_val(o_dose_raw) * (weight if 'mg/kg' in o_dose_raw.lower() else 1)
        y_mg = get_val(str(row.get('P1_Y_Dose', '0'))) * (weight if 'mg/kg' in str(row.get('P1_Y_Dose')).lower() else 1) if (is_p1 and (weeks - 1) % p1_y_freq == 0) else 0.0
        
        o_cost, o_v = calculate_vials(o_mg, 'O', stock_o, multiplier)
        y_cost, y_v = calculate_vials(y_mg, 'Y', [50], multiplier)
        o_p, y_p, status_msg = 0.0, 0.0, ""

        if o_mg > 0 and curr_m <= cap_limit:
            o_admin_total += 1
            if o_admin_total % 2 != 0:
                cost_at_cap = (((weeks + freq - 1) // 4) + 1)
                if cost_at_cap <= cap_limit: 
                    o_p, factor = o_cost, 1.0
                else: 
                    o_p, factor = o_cost * 0.5, 0.5
                    status_msg = " (Pay 50%)"
                o_paid_accum += factor
        
        if y_mg > 0 and curr_m <= cap_limit:
            y_admin_total += 1
            if y_admin_total % 2 != 0:
                y_p = y_cost if (((weeks + p1_y_freq - 1) // 4) + 1) <= cap_limit else y_cost * 0.5

        total_paid += (o_p + y_p)
        if is_p1 and p1_c == 0 and (o_p + y_p) > 0: p1_c = (o_p + y_p)
        if not is_p1 and p2_c == 0 and (o_p + y_p) > 0: p2_c = (o_p + y_p)
        
        timeline.append({
            "Phase": f"Phase {1 if is_p1 else 2}", "Cycle": cycle, "Date": display_date.strftime("%d %b %Y (%a)"),
            "Month": curr_m, "Opdivo Vials": o_v, "Yervoy Vials": y_v if y_mg > 0 else "-", 
            "Opdivo (฿)": o_p, "Yervoy (฿)": y_p, "Total (฿)": (o_p + y_p), 
            "Status": f"Paid{status_msg}" if (o_p + y_p) > 0 else "Free"
        })
        weeks, cycle, curr_date = weeks + freq, cycle + 1, curr_date + timedelta(weeks=freq)
    
    return total_paid, o_paid_accum, p1_c, p2_c, pd.DataFrame(timeline), cap_limit, has_p2

# ==========================================
# 3. LIVE RENDER
# ==========================================

@st.cache_data
def load_data():
    return pd.read_csv("https://docs.google.com/spreadsheets/d/1YXD44pN5mLwazxOiXCHHcylvB082jdtNivXX4VpXdJM/export?format=csv")

df = load_data()
with st.sidebar:
    st.markdown('<div class="app-branding"><div class="app-title-luxury">O+Y Calculator</div><div class="app-subtitle-luxury">Precision PAP Support</div></div>', unsafe_allow_html=True)
    
    # --- 1. Top Priority Inputs ---
    weight = st.number_input("Patient Weight (kg)", 1.0, 150.0, 60.0, step=0.5)
    ind = st.selectbox("Select Indication", df['Indication_Group'].dropna().unique())
    subset = df[df['Indication_Group'] == ind]
    reg = st.radio("Regimen Protocol", subset['Regimen_Name'])
    markup = st.slider("Hospital Markup (%)", 0, 50, 0)
    
    st.markdown("---")
    
    # --- 2. Advanced Settings (Minimized) ---
    with st.expander("🛠️ Scheduling & Dose Settings"):
        start_dt = st.date_input("First Dose Date", date.today())
        skip_wk = st.checkbox("Skip Weekend Appointments", value=True)
        st.markdown("---")
        stock = st.multiselect("Vials in Stock", [40, 100, 120], default=[40, 100, 120])

sel_row = subset[subset['Regimen_Name'] == reg].iloc[0]
total_val, o_rounds, p1_c, p2_c, df_res, cap_val, has_p2_flag = run_simulation(sel_row, weight, stock, (1 + markup/100), start_dt, skip_wk)

st.markdown(f'<div class="ind-title">{ind}</div><div class="protocol-sub">Regimen: {reg}</div>', unsafe_allow_html=True)

# Phase Cards
phase_html = f'<div class="card-wrapper"><div class="phase-card p1"><div class="card-label">Phase 1 / Cycle</div><div class="card-value">฿ {p1_c:,.0f}</div><div class="card-vat">● Inclusive of 7% VAT</div></div>'
if has_p2_flag or p2_c > 0:
    phase_html += f'<div class="phase-card p2"><div class="card-label">Phase 2 / Cycle</div><div class="card-value">฿ {p2_c:,.0f}</div><div class="card-vat">● Inclusive of 7% VAT</div></div>'
st.markdown(phase_html + "</div>", unsafe_allow_html=True)

# Grand Box
st.markdown(f"""
    <div class="grand-box">
        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
                <div class="metric-sub">Total Patient Pay</div>
                <div class="metric-main">฿ {total_val:,.0f}</div>
                <div class="grand-vat">● Includes 7% VAT and {markup}% Hospital Markup</div>
            </div>
            <div style="text-align: right;">
                <div class="metric-sub">Paid Rounds (Opdivo)</div>
                <div class="metric-main">{o_rounds:.1f} Cycles</div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="policy-box"><b>PAP Policy:</b> Payment capped at <b>{cap_val} months</b>. Medication beyond the cap is free until PD or max 2 years.</div>', unsafe_allow_html=True)

st.subheader("📅 Patient Treatment & Appointment Schedule")
st.dataframe(df_res.style.format({"Opdivo (฿)": "{:,.0f}", "Yervoy (฿)": "{:,.0f}", "Total (฿)": "{:,.0f}"}), use_container_width=True, height=500, hide_index=True)