

# CS:GO / CS2 Case History Logger

This script tracks your case openings in CS:GO and CS2 and prints stats about skins, rarities, and special drops (Classified, Covert, Contraband, Extraordinary gloves).  

It generates a CSV log (`case_openings.csv`) and prints colorful output in the terminal.

<!-- SCREENSHOT PLACEHOLDER -->
![Example Output](https://raw.githubusercontent.com/cryptodescriptor/cs-case-logger/refs/heads/master/images/ss.png)

---

## ⚠️ Important Notes

- **Windows Users:** Use **Command Prompt**, not PowerShell. PowerShell does not handle ANSI colors correctly.  
- **Steam Cookies:** You need your `sessionid` and `steamLoginSecure` cookies.  
- **Steam ID:** Put your SteamID `steam_config.json` file (the one in your profile url):

```json
{
  "steamid": "<your steam id>",
  "sessionid": "<your sessionid here>",
  "steamLoginSecure": "<your steamLoginSecure here>"
}
```

---

## How to Get Steam Cookies

### Chrome

1. Open Steam Community in Chrome.
2. Press `F12` → `Application` → `Cookies`.
3. Copy `sessionid` and `steamLoginSecure`.

### Firefox

1. Open Steam Community in Firefox.
2. Press `F12` → `Storage` → `Cookies`.
3. Copy `sessionid` and `steamLoginSecure`.

> ⚠️ If cookies are wrong, or if Steam temporarily blocks your IP, you will see:

```
Attempt {attempt}/{retries} failed: {e}. Retrying in {delay}s...
```


#### ⚠️ If your case history is sizeable you may run into temporary IP blocks

To avoid future IP blocks, open `case_logger.py` in your favorite text editor and change `time.sleep(1)` to `time.sleep(3)

---

## Usage

1. Install dependencies:

```bash
pip install requests beautifulsoup4
```

2. Update `steam_config.json` with your cookies and SteamID.
3. Run the script:

```bash
python case_logger.py
```

---

## Features

- Tracks all case openings.
- Counts StatTrak™ items.
- Shows cumulative rarity stats.
- Shows cumulative case opening stats.
- Top 3 opened skins.
- Tracks last knife and glove openings.
- **Special drops:** Classified, Covert, Contraband, Extraordinary gloves.
- Generates `case_openings.csv`.

---
