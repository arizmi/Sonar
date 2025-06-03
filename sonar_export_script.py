import pandas as pd
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# === GOOGLE SHEETS SETUP ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if os.path.exists("credentials.json"):
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
else:
    raise FileNotFoundError("credentials.json not found")

client = gspread.authorize(creds)
SPREADSHEET_ID = "1uWKm5FeRErzqEpUhwtfxwNfCU2eMbGrjBHKSJG6mnWA"

block_trade_thresholds = {
    'EURUSD': 145_000_000, 'AUDUSD': 50_000_000, 'GBPUSD': 110_000_000, 'USDCAD': 100_000_000,
    'NZDUSD': 30_000_000, 'USDCHF': 100_000_000, 'USDSGD': 100_000_000, 'USDHKD': 100_000_000,
    'AUDJPY': 50_000_000, 'CADJPY': 75_000_000, 'CHFJPY': 120_000_000, 'EURJPY': 145_000_000,
    'GBPJPY': 110_000_000, 'NZDJPY': 30_000_000, 'AUDCAD': 50_000_000, 'AUDCHF': 50_000_000,
    'AUDNZD': 50_000_000, 'CADCHF': 75_000_000, 'EURAUD': 145_000_000, 'EURCAD': 145_000_000,
    'EURCHF': 145_000_000, 'EURGBP': 145_000_000, 'EURNZD': 145_000_000, 'GBPAUD': 110_000_000,
    'GBPCHF': 110_000_000, 'GBPNZD': 110_000_000, 'NZDCAD': 30_000_000, 'NZDCHF': 30_000_000
}

# === LOAD DATA ===
def load_data():
    workbook = client.open_by_key(SPREADSHEET_ID)
    all_dataframes = []
    for ws in workbook.worksheets():
        records = ws.get_all_records()
        if records:
            df = pd.DataFrame(records)
            all_dataframes.append(df)
    return pd.concat(all_dataframes, ignore_index=True)

# === PROCESS & EXPORT ===
def export_json():
    df = load_data()

    df['Trade Date'] = pd.to_datetime(df['Trade Date'], format='%d/%m/%Y', errors='coerce')
    df['Expiry'] = pd.to_datetime(df['Expiry'], format='%d/%m/%Y', errors='coerce')
    df = df[df['Expiry'] >= datetime.today()]
    df['Volume'] = df['Volume'].astype(str).str.replace(',', '').astype(float)
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
    df = df.dropna(subset=['Pair', 'Order', 'Price'])

    df = df.groupby(['Trade Date', 'Pair', 'Order', 'Price'], as_index=False).agg({
        'Volume': 'sum',
        'Expiry': 'min'
    })

    df['IsBlockTrade'] = df.apply(
        lambda row: row['Volume'] > block_trade_thresholds.get(row['Pair'], float('inf')),
        axis=1
    )

    df['Trade Date'] = df['Trade Date'].dt.strftime('%Y-%m-%d')
    df['Expiry'] = df['Expiry'].dt.strftime('%Y-%m-%d')

    df[['Trade Date', 'Pair', 'Order', 'Price', 'Volume', 'Expiry', 'IsBlockTrade']].to_json(
        'sonar_blocktrades.json', orient='records', indent=2
    )

if __name__ == "__main__":
    export_json()
