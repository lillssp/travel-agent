"""Tool: convert_currency. Frankfurter and the NBU for UAH."""

import requests

from .common import get_json

FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"
NBU_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange"

def uah_rate(code):
    data = get_json(NBU_URL, {"valcode": code, "json": ""})
    if not data:
        raise ValueError(f"Currency {code} is not supported.")
    return data[0]["rate"]

def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    src, dst = from_currency.upper().strip(), to_currency.upper().strip()
    if src == dst:
        return {"amount": amount, "from": src, "to": dst, "converted": amount, "rate": 1.0}

    try:
        if "UAH" in (src, dst):
            if src == "UAH":
                rate = 1 / uah_rate(dst)
            elif dst == "UAH":
                rate = uah_rate(src)
            source = "National Bank of Ukraine"
        else:
            data = get_json(FRANKFURTER_URL, {"base": src, "symbols": dst})
            rate = data["rates"][dst]
            source = "Frankfurter (ECB)"
    except (requests.RequestException, ValueError, KeyError) as e:
        return {"error": f"Could not convert {src} to {dst}: {e}"}

    return {
        "amount": amount,
        "from": src,
        "to": dst,
        "converted": round(amount * rate, 2),
        "rate": round(rate, 4),
        "source": source,
    }