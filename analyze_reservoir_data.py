import pandas as pd
import json

# Read the Excel file, skipping the header row
df = pd.read_excel('水库信息.xlsx', header=0)

# The actual column names based on first row
# 水库地点 = Province, Unnamed: 3 = City, Unnamed: 4 = County

print("=" * 80)
print("ANALYZING EXCEL DATA")
print("=" * 80)

# Get province data (column index 2, which is '水库地点')
provinces = df['水库地点'].dropna().unique()
print(f"\nTotal unique provinces in Excel: {len(provinces)}")
print("\nProvinces in Excel:")
for province in sorted(provinces):
    if province != '所在省份':  # Skip header
        count = len(df[df['水库地点'] == province])
        print(f"  {province}: {count}")

# Check for Taiwan
taiwan_count = df[df['水库地点'].str.contains('台湾', na=False)]
print(f"\n台湾 (Taiwan) reservoirs in Excel: {len(taiwan_count)}")

# Read JSON data
print("\n" + "=" * 80)
print("ANALYZING JSON DATA")
print("=" * 80)

with open('web/src/data/reservoirs.json', 'r', encoding='utf-8') as f:
    json_data = json.load(f)

# Check for Taiwan in JSON
taiwan_json = [r for r in json_data if '台湾' in r.get('province', '')]
print(f"\n台湾 (Taiwan) reservoirs in JSON: {len(taiwan_json)}")

if taiwan_json:
    print("\n⚠️ PROBLEM FOUND: Taiwan reservoirs in JSON but NOT in Excel!")
    print("\nTaiwan reservoirs in JSON:")
    for r in taiwan_json:
        print(f"  {r['id']}: {r['name']} - {r.get('location', 'N/A')}")

# Also check for data inconsistencies
print("\n" + "=" * 80)
print("DATA COMPARISON")
print("=" * 80)
print(f"Excel rows (excluding header): {len(df) - 1}")
print(f"JSON entries: {len(json_data)}")
print(f"Difference: {len(json_data) - (len(df) - 1)}")

# Check province name issues (trailing spaces)
print("\n" + "=" * 80)
print("PROVINCE NAME ISSUES IN JSON")
print("=" * 80)
province_issues = {}
for reservoir in json_data:
    province = reservoir.get('province', '')
    if province.strip() != province:
        if province not in province_issues:
            province_issues[province] = 0
        province_issues[province] += 1

if province_issues:
    print("\nProvinces with trailing/leading spaces:")
    for province, count in province_issues.items():
        print(f"  '{province}' ({count} reservoirs)")
