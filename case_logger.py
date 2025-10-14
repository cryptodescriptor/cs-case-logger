import requests
from bs4 import BeautifulSoup
from datetime import datetime
import csv
import time
from collections import Counter
import os
import sys
import json

# --- Detect if ANSI colors are supported ---
def supports_ansi():
    if sys.platform != "win32":
        return True
    try:
        return os.system("") == 0
    except Exception:
        return False

USE_COLOR = supports_ansi()

# --- Colors ---
RESET = "\033[0m" if USE_COLOR else ""
YELLOW = "\033[93m" if USE_COLOR else ""
GREEN = "\033[32m" if USE_COLOR else ""
DARK_RED = "\033[31m" if USE_COLOR else ""

# --- Load Steam config from JSON ---
CONFIG_FILE = "steam_config.json"
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    steam_config = json.load(f)

steamid = steam_config.get("steamid", "defaultid")
cookies = {
    "sessionid": steam_config.get("sessionid", ""),
    "steamLoginSecure": steam_config.get("steamLoginSecure", "")
}

# --- Helpers ---
def print_heading(text):
    print(f"{GREEN}{text}{RESET}")

def highlight_stattrak(item_name, rarity_color):
    if "StatTrak™" in item_name and USE_COLOR:
        return item_name.replace(
            "StatTrak™",
            f"{YELLOW}StatTrak™{rarity_color}"
        )
    return f"{rarity_color}{item_name}"

def highlight_case_name(case_name):
    return f"{GREEN}{case_name}{RESET}" if USE_COLOR else case_name

def print_item_history(item_name, last_dt, all_cases):
    if last_dt:
        cases_since = sum(1 for _, dt_obj, *_ in all_cases if dt_obj and dt_obj > last_dt)
        msg = f"{YELLOW}Cases opened since last {item_name} ({last_dt.strftime('%Y-%m-%d %H:%M:%S')}): {cases_since}{RESET}"
        print(f"\n{msg}")
    else:
        msg = f"{DARK_RED}No {item_name.lower()} found in history.{RESET}"
        print(f"\n{msg}")

def normalize_name(name):
    if name.startswith("StatTrak™ "):
        name = name[len("StatTrak™ "):]
    return name.strip().lower()

def is_stattrak(item_name):
    return item_name.startswith("StatTrak™ ")

def fetch_steam_data(url, cookies, retries=5, delay=5):
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, cookies=cookies, timeout=10)
            data = resp.json()
            if data is None or "html" not in data:
                raise ValueError("Empty or invalid response")
            return data
        except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
            print(f"Attempt {attempt}/{retries} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
    print("Failed to fetch data after multiple attempts. Exiting.")
    return None

# --- Extract item info from page descriptions ---
def get_item_category(tags):
    if not tags:
        return "Unknown"
    type_name = tags[0].get("name", "").lower()
    if "knife" in type_name:
        return "Knife"
    elif "glove" in type_name:
        return "Glove"
    else:
        return type_name.title()

def get_item_info(descriptions_json, classid, instanceid):
    if not classid or not instanceid:
        return "Unknown", "Unknown", "Unknown"
    key = f"{classid}_{instanceid}"
    item = descriptions_json.get("730", {}).get(key, {})
    tags = item.get("tags", [])
    rarity = tags[4]["name"]
    wear = tags[5]["name"]
    category = get_item_category(tags)
    return rarity, wear, category

def parse_timestamp(entry):
    date_div = entry.find("div", class_="tradehistory_date")
    ts_div = entry.find("div", class_="tradehistory_timestamp")
    if date_div and ts_div:
        date_str = date_div.contents[0].strip()
        time_str = ts_div.get_text(strip=True)
        combined = f"{date_str} {time_str}"
        try:
            dt_obj = datetime.strptime(combined, "%d %b, %Y %I:%M%p")
            readable_time = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            dt_obj = None
            readable_time = combined
    else:
        dt_obj = None
        readable_time = "Unknown"
    return readable_time, dt_obj

def extract_item_and_case(entry):
    item_name = None
    case_name = None
    item_classid = None
    item_instanceid = None

    items_blocks = entry.find_all("div", class_="tradehistory_items")
    for block in items_blocks:
        plusminus_div = block.find("div", class_="tradehistory_items_plusminus")
        group_div = block.find("div", class_="tradehistory_items_group")
        if not plusminus_div or not group_div:
            continue

        sign = plusminus_div.get_text(strip=True)
        history_items = group_div.find_all(class_="history_item")
        if not history_items:
            continue

        if sign == "+":
            h = history_items[0]
            item_name = h.get_text(strip=True)
            item_classid = h.get("data-classid")
            item_instanceid = h.get("data-instanceid")
        elif sign == "-":
            h = history_items[-1]
            case_name = h.get_text(strip=True)

            # Sometimes case_name is the first item in the lsit
            if 'Key' in case_name:
                case_name = case_name.replace(' Key', '')

    if not case_name:
        case_name = "Unknown Case"

    return item_name, case_name, item_classid, item_instanceid

def parse_cases(html):
    soup = BeautifulSoup(html, "html.parser")
    cases = []

    for entry in soup.find_all("div", class_="tradehistoryrow"):
        text = entry.get_text(" ", strip=True)
        if "Unlocked a container" not in text or "Genesis Terminal" in text:
            continue

        readable_time, dt_obj = parse_timestamp(entry)
        item_name, case_name, item_classid, item_instanceid = extract_item_and_case(entry)

        if not item_name:
            continue

        cases.append(
            (readable_time, dt_obj, item_name, case_name, text, item_classid, item_instanceid)
        )

    return cases

def get_color(rarity):
    if not USE_COLOR:
        return ""
    if "Mil-Spec" in rarity:
        return "\033[94m"
    elif "Restricted" in rarity:
        return "\033[95m"
    elif "Classified" in rarity:
        return "\033[35m"
    elif "Covert" in rarity:
        return "\033[91m"
    elif "Consumer" in rarity or "Industrial" in rarity:
        return "\033[37m"
    elif "Contraband" in rarity:
        return "\033[93m"
    else:
        return "\033[90m"

def process_case(case, writer, all_cases, descriptions_json,
                 stattrak_count, last_knife_dt, last_gloves_dt, skin_counter,
                 rarity_counter, case_counter, special_drops):
    readable_time, dt_obj, item_name, case_name, desc, classid, instanceid = case
    all_cases.append(case)

    rarity, wear, category = get_item_info(descriptions_json, classid, instanceid)

    if "Knife" in category and dt_obj:
        last_knife_dt = dt_obj
    if "Glove" in category and dt_obj:
        last_gloves_dt = dt_obj

    stattrak_flag = "Yes" if is_stattrak(item_name) else "No"
    rarity_color = get_color(rarity)
    display_name = highlight_stattrak(item_name, rarity_color)
    case_name_colored = highlight_case_name(case_name)

    print(f"[{readable_time}] {case_name_colored}{RESET} → {display_name} → Rarity: {rarity}{RESET} → Wear: {wear}")

    writer.writerow([readable_time, item_name, case_name, desc, rarity, wear, stattrak_flag])

    stattrak_count += 1 if stattrak_flag == "Yes" else 0
    skin_counter[normalize_name(item_name)] += 1
    rarity_counter[rarity] += 1
    case_counter[case_name] += 1

    # --- Track special drops including gloves (Extraordinary) ---
    if rarity in ["Classified", "Covert", "Contraband", "Extraordinary"]:
        special_drops.append((readable_time, item_name, rarity, wear, case_name, stattrak_flag))

    return stattrak_count, last_knife_dt, last_gloves_dt

def paginate_inventory(url, cookies):
    total = 0
    stattrak_count = 0
    last_knife_dt = None
    last_gloves_dt = None
    all_cases = []
    skin_counter = Counter()
    rarity_counter = Counter()
    case_counter = Counter()
    special_drops = []

    with open("case_openings.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Item Name", "Case Name", "Description", "Rarity", "Wear", "StatTrak"])

        while True:
            data = fetch_steam_data(url, cookies)
            if data is None:
                break

            cases = parse_cases(data.get("html", ""))
            descriptions_json = data.get("descriptions", {})

            for case in cases:
                stattrak_count, last_knife_dt, last_gloves_dt = process_case(
                    case, writer, all_cases, descriptions_json,
                    stattrak_count, last_knife_dt, last_gloves_dt, skin_counter,
                    rarity_counter, case_counter, special_drops
                )
                total += 1

            cursor = data.get("cursor")
            if not cursor:
                break

            url = (
                f"https://steamcommunity.com/id/{steamid}/inventoryhistory/?ajax=1"
                f"&cursor[time]={cursor['time']}"
                f"&cursor[time_frac]={cursor['time_frac']}"
                f"&cursor[s]={cursor['s']}"
            )
            time.sleep(3)

    return total, stattrak_count, last_knife_dt, last_gloves_dt, all_cases, skin_counter, rarity_counter, case_counter, special_drops

def count_case_openings():
    url = f"https://steamcommunity.com/id/{steamid}/inventoryhistory/?ajax=1"
    total, stattrak_count, last_knife_dt, last_gloves_dt, all_cases, skin_counter, rarity_counter, case_counter, special_drops = paginate_inventory(url, cookies)

    print(f"\n{YELLOW}Total Cases Opened: {total}{RESET}")
    print(f"{YELLOW}Total StatTrak™ Items: {stattrak_count}{RESET}")

    print_heading("\n--- Cumulative Rarity Stats ---")
    for rarity, count in rarity_counter.items():
        pct = (count / total * 100) if total else 0
        color = get_color(rarity)
        print(f"{color}{rarity}: {count} ({pct:.2f}%){RESET}")

    print_heading("\n--- Cumulative Case Opening Stats ---")
    for case, count in case_counter.items():
        pct = (count / total * 100) if total else 0
        print(f"{case} → {count} ({pct:.2f}%){RESET}")

    print_heading("\n--- Top 3 Opened Skins ---")
    for skin, count in Counter(skin_counter).most_common(3):
        print(f"{skin.title()}: {count}")

    # --- Print all special drops ---
    print_heading("\n--- Special Drops (Classified, Covert, Contraband, Extraordinary) ---")
    if special_drops:
        for readable_time, item_name, rarity, wear, case_name, stattrak_flag in special_drops:
            rarity_color = get_color(rarity)
            display_name = highlight_stattrak(item_name, rarity_color)
            case_name_colored = highlight_case_name(case_name)
            print(f"[{readable_time}] {case_name_colored}{RESET} → {display_name} → Rarity: {rarity}{RESET} → Wear: {wear} → StatTrak: {stattrak_flag}")

    else:
        print(f"{DARK_RED}No special drops found.{RESET}")

    print_item_history("knife", last_knife_dt, all_cases)
    print_item_history("gloves", last_gloves_dt, all_cases)

if __name__ == "__main__":
    count_case_openings()
