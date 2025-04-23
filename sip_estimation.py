import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from tabulate import tabulate
import os

INPUT_FILE = 'mutual_funds_input.json'

def get_user_input_or_load_file():
    if os.path.exists(INPUT_FILE):
        use_existing = input(f"\n📁 Existing input file '{INPUT_FILE}' found. Use this? (y/n): ").strip().lower()
        if use_existing == 'y':
            with open(INPUT_FILE, 'r') as f:
                return json.load(f)['funds']

    num_funds = int(input("Enter number of mutual funds to analyze: "))
    funds = []
    for i in range(num_funds):
        print(f"\n🔗 Fund {i+1}")
        url = input("  - Enter MFAPI URL: ").strip()
        sip_day = int(input("  - Enter SIP date (1-31): "))
        sip_amount = int(input("  - Enter SIP monthly amount: "))
        years = int(input("  - Enter number of years to analyze: "))
        funds.append({"url": url, "sip_day": sip_day, "sip_amount": sip_amount, "years": years})

    with open(INPUT_FILE, 'w') as f:
        json.dump({"funds": funds}, f, indent=4)

    return funds

def calculate_cagr(start_nav, end_nav, years):
    return (end_nav / start_nav) ** (1 / years) - 1 if years > 0 else 0

def calculate_estimated_amount(cagr, years, initial_investment):
    return initial_investment * (1 + cagr) ** years

def analyze_fund(url, sip_day, sip_amount, years):
    response = requests.get(url)
    data = response.json()
    scheme_name = data['meta']['scheme_name']

    df = pd.DataFrame(data['data'])
    df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
    df['nav'] = pd.to_numeric(df['nav'])
    df = df.sort_values('date').reset_index(drop=True)

    sip_start_date = df['date'].max() - pd.DateOffset(years=years)
    sip_end_date = df['date'].max()

    sip_investments = []
    current = datetime(sip_start_date.year, sip_start_date.month, 1)
    months_to_invest = years * 12
    months_done = 0

    while months_done < months_to_invest and current <= sip_end_date:
        try:
            invest_date = current.replace(day=sip_day)
        except ValueError:
            current += timedelta(days=32)
            current = current.replace(day=1)
            continue

        nav_row = df[df['date'] >= invest_date]
        if not nav_row.empty:
            sip_investments.append(nav_row.iloc[0])
            months_done += 1

        next_month = current.month + 1 if current.month < 12 else 1
        next_year = current.year if current.month < 12 else current.year + 1
        current = datetime(next_year, next_month, 1)

    if len(sip_investments) < 12:
        print(f"❌ Not enough data to simulate SIP for {scheme_name}")
        return None, None

    sip_df = pd.DataFrame(sip_investments)
    total_units = (sip_amount / sip_df['nav']).sum()
    total_invested = len(sip_df) * sip_amount
    final_value = total_units * df.iloc[-1]['nav']
    actual_years = (df.iloc[-1]['date'] - sip_df.iloc[0]['date']).days / 365.25
    cagr = calculate_cagr(total_invested, final_value, actual_years)

    return {
        'Fund': scheme_name,
        'CAGR (%)': round(cagr * 100, 2),
        'Final Value (₹)': f"{final_value:,.2f}",
        'Total Invested (₹)': f"{total_invested:,.2f}"
    }, (df, final_value)

def apply_resting_period(df, invested_amount, years):
    if years <= 0:
        return invested_amount, 0

    df = df.sort_values('date')
    end_date = df['date'].max()
    start_date = end_date - pd.DateOffset(years=years)
    resting_df = df[df['date'] >= start_date]

    if resting_df.empty:
        return invested_amount, 0

    start_nav = resting_df.iloc[0]['nav']
    end_nav = resting_df.iloc[-1]['nav']
    cagr = calculate_cagr(start_nav, end_nav, years)
    rested_value = calculate_estimated_amount(cagr, years, invested_amount)
    return rested_value, round(cagr * 100, 2)

def main():
    funds = get_user_input_or_load_file()
    results = []
    resting_results = []
    total_invested = 0
    total_final_value = 0.0
    total_rested_value = 0.0

    for fund in funds:
        print(f"\n🔍 Analyzing fund...")
        result, meta = analyze_fund(fund['url'], fund['sip_day'], fund['sip_amount'], fund['years'])
        if result:
            results.append(result)
            total_invested += float(result['Total Invested (₹)'].replace(',', ''))
            total_final_value += float(result['Final Value (₹)'].replace(',', ''))

            resting_years = int(input(f"Enter resting period (years) for '{result['Fund']}' (0 for none): "))
            if resting_years > 0:
                df, final_value = meta
                rested_value, resting_cagr = apply_resting_period(df, final_value, resting_years)
                resting_results.append({
                    'Fund': result['Fund'],
                    'Invested Amount (₹)': f"{final_value:,.2f}",
                    'Rested Value (₹)': f"{rested_value:,.2f}",
                    'Resting Period CAGR (%)': resting_cagr
                })
                total_rested_value += rested_value

    print("\n📊 SIP Fund Results:")
    print(tabulate(results, headers="keys", tablefmt="fancy_grid"))

    if resting_results:
        print("\n📊 Resting Period Fund Results:")
        print(tabulate(resting_results, headers="keys", tablefmt="fancy_grid"))

    if results:
        total_cagr = calculate_cagr(total_invested, total_final_value, funds[0]['years'])
        print("\n📈 Aggregated Summary:")
        print(f"Total Invested: ₹{total_invested:,.2f}")
        print(f"Total Final Value: ₹{total_final_value:,.2f}")
        print(f"Aggregate CAGR over {funds[0]['years']} years: {total_cagr * 100:.2f}%")

    if resting_results:
        resting_years_set = set([int(input(f"\n🔁 Please re-confirm resting period used for aggregate CAGR calculation: "))])
        if len(resting_years_set) == 1:
            resting_years = resting_years_set.pop()
            overall_cagr = calculate_cagr(total_final_value, total_rested_value, resting_years)
            print(f"Aggregate Resting Period Value: ₹{total_rested_value:,.2f}")
            print(f"Aggregate Resting Period CAGR over {resting_years} years: {overall_cagr * 100:.2f}%")

if __name__ == '__main__':
    main()