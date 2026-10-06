import os, json, time
import pandas as pd
from google import genai

MODEL = "gemini-3.1-flash-lite"

THEMES = ["payment failure", "login/OTP", "app crash/bug", "refund",
          "order/delivery", "customer support", "pricing/offers", "other"]

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

gold = pd.read_excel("gold_set_labeled.xlsx")
gold = gold[gold["language_type"].isin(["English", "Hinglish"])].copy()

PROMPT = """You analyse app-store reviews from Indian users.
Many reviews are Hinglish: Hindi words written in English letters, often mixed
with English, with informal spelling (for example nahi/nhi = not, paisa/paise = money,
wapas = back, bekar/ghatiya = bad, order nahi aaya = order did not arrive).

Work in two steps:
1. Translate the review into plain English (keep the meaning, do not add anything).
2. Pick the main pain point from the review.

Return only JSON with these keys:
"english": the plain-English translation
"theme": one of {themes}
"severity": one of low, medium, high
"quote": the exact words copied from the ORIGINAL review (not the translation),
         without changing spelling or translating

Severity rule: high = money lost, app unusable, or booking/order failed;
medium = repeated or very annoying problem; low = small annoyance or vague complaint.

Examples:
Review: "paisa kat gaya lekin order confirm nahi hua"
{{"english": "Money was deducted but the order was not confirmed", "theme": "payment failure", "severity": "high", "quote": "paisa kat gaya lekin order confirm nahi hua"}}

Review: "app bahut slow hai, login me time lagta hai"
{{"english": "The app is very slow and login takes time", "theme": "login/OTP", "severity": "medium", "quote": "login me time lagta hai"}}

Review: "delivery boy ne call nahi kiya aur order wapas bhej diya"
{{"english": "The delivery person did not call and sent the order back", "theme": "order/delivery", "severity": "high", "quote": "order wapas bhej diya"}}

Review: {review}"""

def ask(review):
    for attempt in range(2):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=PROMPT.format(themes=THEMES, review=review),
                config={"response_mime_type": "application/json"},
            )
            return json.loads(resp.text)
        except Exception as e:
            print("ERROR:", e)
            time.sleep(8)
    return {"theme": "ERROR", "severity": "", "quote": ""}

rows = []
for _, r in gold.iterrows():
    out = ask(r["content"])
    if isinstance(out, list) and out:
        out = out[0]
    rows.append({
        "review_id": r["review_id"],
        "language_type": r["language_type"],
        "gold_theme": r["theme"],
        "ai_theme": out.get("theme", ""),
        "gold_severity": r["severity"],
        "ai_severity": out.get("severity", ""),
        "ai_english": out.get("english", ""),
        "ai_quote": out.get("quote", ""),
        "quote_valid": str(out.get("quote", "")).strip() in str(r["content"]),
    })
    print("done", r["review_id"])
    time.sleep(4)

res = pd.DataFrame(rows)
res["theme_correct"] = res["gold_theme"] == res["ai_theme"]
res.to_csv("results_B.csv", index=False)

print("\nVersion B results")
print(res.groupby("language_type")[["theme_correct", "quote_valid"]].mean().round(2))
print("Errors:", (res["ai_theme"] == "ERROR").sum())