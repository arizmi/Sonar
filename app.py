import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Sonar", layout="wide")
st.title("🧑‍💻 Sonar")
st.subheader("💸 Currency Swap Data")

# === GOOGLE SHEETS SETUP ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if os.path.exists("credentials.json"):
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
else:
    creds_dict = json.loads(st.secrets["credentials_json"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)

# === SHEET CONFIG ===
SPREADSHEET_ID = "1uWKm5FeRErzqEpUhwtfxwNfCU2eMbGrjBHKSJG6mnWA"
SHEET_NAME = "Sheet1"

# === LOAD DATA ===
@st.cache_data(ttl=300)
def load_data():
    workbook = client.open_by_key(SPREADSHEET_ID)
    all_dataframes = []

    for ws in workbook.worksheets():
        records = ws.get_all_records()
        if records:  # only include non-empty sheets
            df = pd.DataFrame(records)
            all_dataframes.append(df)

    # Combine all sheets into one DataFrame
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    return combined_df

# === PROCESS DATA ===
def process_data(df):
    df['Expiry'] = pd.to_datetime(df['Expiry'], format='%d/%m/%Y', errors='coerce')
    df = df[df['Expiry'] >= datetime.today()]

    # Clean Volume and Price
    df['Volume'] = df['Volume'].astype(str).str.replace(',', '').astype(float)
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')

    # Drop Trade Date if present
    if 'Trade Date' in df.columns:
        df = df.drop(columns=['Trade Date'])

    df = df.dropna(subset=['Pair', 'Order', 'Price'])

    # Convert Expiry to datetime again for grouping logic
    df['Expiry'] = pd.to_datetime(df['Expiry'], dayfirst=True, errors='coerce')

    # Consolidate orders: group by Pair, Order, Price
    df = df.groupby(['Pair', 'Order', 'Price'], as_index=False).agg({
        'Volume': lambda x: sum(int(v) for v in x),
        'Expiry': lambda x: min(x)
    })

    # Format values after grouping
    df['Volume'] = df['Volume'].apply(lambda x: f"{int(x):,}")
    df['Price'] = df['Price'].apply(lambda x: f"{x:.5f}".rstrip('0').rstrip('.') if pd.notnull(x) else "")
    df['Expiry'] = df['Expiry'].dt.strftime('%d/%m/%Y')

    return df

# === ROW HIGHLIGHTING FUNCTION ===
def highlight_order(row):
    if row['Order'] == 'CALL':
        bg = 'rgba(0, 255, 0, 0.10)'  # faint green
    elif row['Order'] == 'PUT':
        bg = 'rgba(255, 0, 0, 0.10)'  # faint red
    else:
        bg = 'transparent'
    return [f'background-color: {bg}; text-align: center;' for _ in row]

# === MAIN APP ===
try:
    df = load_data()
    df = process_data(df)

    st.markdown("#### 🔍 Filter by Currency ")
    pair_options = ["All"] + sorted(df['Pair'].dropna().unique().tolist())
    selected_pair = st.selectbox("", pair_options)

    if selected_pair != "All":
        df = df[df["Pair"] == selected_pair]

    df = df.reset_index(drop=True)
    styled_df = df.style.apply(highlight_order, axis=1).hide(axis="index")

    st.dataframe(styled_df, use_container_width=True)

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
