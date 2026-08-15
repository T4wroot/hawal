import urllib.request
import json
import socket

# In-memory cache for IP lookups
GEOIP_CACHE = {}

COUNTRY_FLAGS = {
    "IR": "🇮🇷",
    "DE": "🇩🇪",
    "NL": "🇳🇱",
    "FI": "🇫🇮",
    "FR": "🇫🇷",
    "US": "🇺🇸",
    "GB": "🇬🇧",
    "TR": "🇹🇷",
    "AE": "🇦🇪",
    "SG": "🇸🇬",
    "CA": "🇨🇦",
    "SE": "🇸🇪",
    "CH": "🇨🇭",
    "RU": "🇷🇺",
    "IT": "🇮🇹",
    "ES": "🇪🇸",
    "PL": "🇵🇱",
    "AT": "🇦🇹"
}

COUNTRY_NAMES_FA = {
    "IR": "ایران",
    "DE": "آلمان",
    "NL": "هلند",
    "FI": "فنلاند",
    "FR": "فرانسه",
    "US": "آمریکا",
    "GB": "انگلستان",
    "TR": "ترکیه",
    "AE": "امارات",
    "SG": "سنگاپور",
    "CA": "کانادا",
    "SE": "سوئد",
    "CH": "سوئیس",
    "RU": "روسیه",
    "IT": "ایتالیا",
    "ES": "اسپانیا",
    "PL": "لهستان",
    "AT": "اتریش"
}

def get_country_flag(country_code):
    if not country_code:
        return "🌐"
    return COUNTRY_FLAGS.get(country_code.upper(), "🌐")

def resolve_geoip(ip):
    """
    Resolves public IP to country code, Persian country name, flag emoji, and city.
    """
    if not ip or ip in ["127.0.0.1", "localhost", "0.0.0.0"]:
        return {
            "country_code": "LOCAL",
            "country_name": "لوکال / آزمایشی",
            "flag": "💻",
            "city": "Localhost"
        }

    if ip in GEOIP_CACHE:
        return GEOIP_CACHE[ip]

    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city"
        req = urllib.request.Request(url, headers={"User-Agent": "HawalTunnel/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("status") == "success":
                cc = data.get("countryCode", "").upper()
                name_fa = COUNTRY_NAMES_FA.get(cc, data.get("country", "خارج"))
                flag = get_country_flag(cc)
                res = {
                    "country_code": cc,
                    "country_name": name_fa,
                    "flag": flag,
                    "city": data.get("city", "")
                }
                GEOIP_CACHE[ip] = res
                return res
    except Exception as e:
        pass

    # Fallback heuristic for Iran IPs if offline
    if ip.startswith("5.202.") or ip.startswith("185.") or ip.startswith("91.98.") or ip.startswith("94.182."):
        res = {"country_code": "IR", "country_name": "ایران", "flag": "🇮🇷", "city": "تهران"}
    else:
        res = {"country_code": "GLOBAL", "country_name": "خارج", "flag": "🌐", "city": ""}
    
    GEOIP_CACHE[ip] = res
    return res
