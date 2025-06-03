import json
from datetime import datetime

# Load JSON
with open("sonar_blocktrades.json", "r") as f:
    data = json.load(f)

# Helper: Clean number to PineScript float
def format_price(value):
    return f"{float(value):.5f}".rstrip('0').rstrip('.') if value else ""

# Group by Pair
pairs = {}
for entry in data:
    pair = entry.get("Pair")
    price = entry.get("Price")
    expiry = entry.get("Expiry")

    if not (pair and price and expiry):
        continue

    # Filter for future expiry only
    try:
        expiry_dt = datetime.strptime(expiry, "%d/%m/%Y")
        if expiry_dt < datetime.today():
            continue
    except Exception:
        continue

    price = format_price(price)
    if not price:
        continue

    if pair not in pairs:
        pairs[pair] = set()
    pairs[pair].add(float(price))

# Output .pine file per pair
for pair, levels in pairs.items():
    clean_pair = pair.lower()
    filename = f"pine_scripts/{clean_pair}.pine"
    with open(filename, "w") as f:
        f.write(f"//@version=5\nindicator(\"Block Trades - {pair}\", overlay=true)\n\n")
        sorted_levels = sorted(levels, reverse=True)
        f.write("levels = [")
        f.write(", ".join(f"{lvl:.5f}".rstrip('0').rstrip('.') for lvl in sorted_levels))
        f.write("]\n\n")
        f.write("for i = 0 to array.size(levels) - 1\n")
        f.write("    lvl = levels[i]\n")
        f.write("    line.new(bar_index, lvl, bar_index + 1, lvl, color=color.rgb(255, 215, 0), style=line.style_dashed)\n")

print("✅ Pine scripts generated in pine_scripts/")
