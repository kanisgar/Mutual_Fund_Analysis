import requests
import pandas as pd
from datetime import datetime, timedelta
from tabulate import tabulate

# Step 1: Ask the user to input the URL for the mutual fund data
url = input("Please enter the URL for the mutual fund data: ")

# Fetch data from the provided URL
response = requests.get(url)
data = response.json()

# Extract the scheme name from the API data
scheme_name = data['meta']['scheme_name']
print(f"\n📊 CAGR Analysis for: \033[1m{scheme_name}\033[0m\n")

# Step 2: Prepare NAV DataFrame
df = pd.DataFrame(data['data'])
df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
df['nav'] = pd.to_numeric(df['nav'])
df = df.sort_values('date').reset_index(drop=True)

# Step 3: Define SIP parameters
investment_amount = 50000
start_date = df['date'].min()
end_date = df['date'].max()
years = (end_date - start_date).days / 365.25

cagr_results = {}

# Step 4: Simulate SIP for each date of the month
for sip_day in range(1, 32):
    sip_investments = []
    current = datetime(start_date.year, start_date.month, 1)

    while current <= end_date:
        try:
            invest_date = current.replace(day=sip_day)
        except ValueError:
            current += timedelta(days=32)
            current = current.replace(day=1)
            continue

        nav_row = df[df['date'] >= invest_date]
        if not nav_row.empty:
            sip_investments.append(nav_row.iloc[0])

        # Move to next month
        next_month = current.month + 1 if current.month < 12 else 1
        next_year = current.year if current.month < 12 else current.year + 1
        current = datetime(next_year, next_month, 1)

    if len(sip_investments) < 24:
        continue

    sip_df = pd.DataFrame(sip_investments)
    total_units = (investment_amount / sip_df['nav']).sum()
    total_invested = len(sip_df) * investment_amount
    final_value = total_units * df.iloc[-1]['nav']
    cagr = (final_value / total_invested) ** (1 / years) - 1

    cagr_results[sip_day] = {
        'Day': f"{sip_day:02d}",
        'CAGR (%)': round(cagr * 100, 2),
        'Final Value (₹)': f"{final_value:,.2f}",
        'Total Invested (₹)': f"{total_invested:,.2f}"
    }

# Step 5: User choice for top 5 or all
choice = input("Do you want to see [1] Top 5 dates or [2] CAGR for all dates? Enter 1 or 2: ")

if choice.strip() == '1':
    result_list = sorted(cagr_results.values(), key=lambda x: float(x['CAGR (%)']), reverse=True)[:5]
else:
    result_list = sorted(cagr_results.values(), key=lambda x: int(x['Day']))

# Step 6: Display table for SIP dates
print("\n" + tabulate(result_list, headers="keys", tablefmt="fancy_grid"))

# Step 7: Calculate Advertised CAGR for 1-year, 5-years, and 10-years
current_date = datetime.now()
one_year_ago = current_date - timedelta(days=365)
five_years_ago = current_date - timedelta(days=365*5)
ten_years_ago = current_date - timedelta(days=365*10)

def calculate_cagr(start_nav, end_nav, years):
    return (end_nav / start_nav) ** (1 / years) - 1

# Get the NAV for the respective dates
nav_1_year_ago = df[df['date'] <= one_year_ago].iloc[-1]['nav']
nav_5_years_ago = df[df['date'] <= five_years_ago].iloc[-1]['nav']
nav_10_years_ago = df[df['date'] <= ten_years_ago].iloc[-1]['nav']

# Calculate the CAGR for each period
cagr_1_year = calculate_cagr(nav_1_year_ago, df.iloc[-1]['nav'], 1)
cagr_5_year = calculate_cagr(nav_5_years_ago, df.iloc[-1]['nav'], 5)
cagr_10_year = calculate_cagr(nav_10_years_ago, df.iloc[-1]['nav'], 10)

# Function to calculate estimated amount based on CAGR
def calculate_estimated_amount(cagr, years, initial_investment):
    return initial_investment * (1 + cagr) ** years

# Calculate the estimated amounts
initial_investment = 500000  # ₹5,00,000 investment
estimated_1_year = calculate_estimated_amount(cagr_1_year, 1, initial_investment)
estimated_5_year = calculate_estimated_amount(cagr_5_year, 5, initial_investment)
estimated_10_year = calculate_estimated_amount(cagr_10_year, 10, initial_investment)

# Calculate CAGR from the earliest available date (e.g., 2013)
earliest_date = df['date'].min()
nav_earliest = df[df['date'] == earliest_date].iloc[0]['nav']
cagr_from_earliest = calculate_cagr(nav_earliest, df.iloc[-1]['nav'], years)

# Calculate the estimated amount for ₹5,00,000 investment from earliest date
estimated_from_earliest = calculate_estimated_amount(cagr_from_earliest, years, initial_investment)

# Print the advertised CAGR values, estimated amounts, and CAGR from the earliest available date
print("\n📊 Advertised CAGR based on Historical NAVs and Estimated Amounts:")
print(f"1-Year CAGR: {cagr_1_year * 100:.2f}% → Estimated Amount for ₹5,00,000: ₹{estimated_1_year:,.2f}")
print(f"5-Year CAGR: {cagr_5_year * 100:.2f}% → Estimated Amount for ₹5,00,000: ₹{estimated_5_year:,.2f}")
print(f"10-Year CAGR: {cagr_10_year * 100:.2f}% → Estimated Amount for ₹5,00,000: ₹{estimated_10_year:,.2f}")
print(f"\nCAGR from Earliest Available Date ({earliest_date.date()}): {cagr_from_earliest * 100:.2f}% → Estimated Amount for ₹5,00,000: ₹{estimated_from_earliest:,.2f}")
