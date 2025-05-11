import pdfplumber
import re
import csv
import json
from datetime import datetime

pdf_path = "statement.pdf"  # Make sure this PDF is in the same folder
transactions = []

# Pattern to detect lines that begin a transaction block
date_line_pattern = re.compile(r"^\d{2}/\d{2}/\d{2,4}")

with pdfplumber.open(pdf_path) as pdf:
    current_block = []
    for page in pdf.pages:
        lines = page.extract_text().split('\n')
        for line in lines:
            if date_line_pattern.match(line.strip()):
                if current_block:
                    transactions.append("\n".join(current_block))
                current_block = [line.strip()]
            else:
                if current_block:
                    current_block.append(line.strip())
    if current_block:
        transactions.append("\n".join(current_block))

parsed_transactions = []
previous_balance = None

for block in transactions:
    lines = block.split('\n')
    try:
        first_line = lines[0]
        parts = first_line.split()

        # Extract Date
        date_str = parts[0]
        date = datetime.strptime(date_str, "%d/%m/%y").date().isoformat()

        # Extract Value Date
        value_date = None
        for part in reversed(parts):
            if re.match(r"\d{2}/\d{2}/\d{2,4}", part):
                value_date = datetime.strptime(part, "%d/%m/%y").date().isoformat()
                break

        # Extract Closing Balance
        closing_balance = float(parts[-1].replace(",", ""))

        # Compute Deposit/Withdrawal based on balance difference
        if previous_balance is not None:
            delta = closing_balance - previous_balance
            if delta < 0:
                withdrawal = abs(delta)
                deposit = 0.0
            else:
                deposit = delta
                withdrawal = 0.0
        else:
            withdrawal = deposit = 0.0

        previous_balance = closing_balance

        # Extract Transaction ID (long number-like string)
        txn_id = ""
        for p in parts:
            if re.match(r"^\d{10,}$", p):
                txn_id = p
                break

        # Combine narration lines
        narration_lines = lines.copy()
        narration_lines[0] = first_line.replace(date_str, '').strip()
        narration = " ".join(narration_lines).strip()

        parsed_transactions.append({
            "Date": date,
            "Narration": narration,
            "TransactionID": txn_id,
            "ValueDate": value_date or "",
            "Withdrawal": round(withdrawal, 2),
            "Deposit": round(deposit, 2),
            "Balance": closing_balance
        })

    except Exception as e:
        import traceback
        print(f"[!] Error: {e}")
        traceback.print_exc()
        print("Block that caused error:\n", block)

# Write to CSV
csv_fields = ["Date", "Narration", "TransactionID", "ValueDate", "Withdrawal", "Deposit", "Balance"]
with open("transactions.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=csv_fields, quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()
    writer.writerows(parsed_transactions)

# Write to JSON
with open("transactions.json", "w") as f:
    json.dump(parsed_transactions, f, indent=4)

print(f"✅ Extraction complete. {len(parsed_transactions)} transactions saved.")