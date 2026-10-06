import os, json, time
import pandas as pd
from google import genai

MODEL = "gemini-3.1-flash-lite"

THEMES = ["payment failure", "login/OTP", "app crash/bug", "refund",
          "order/delivery", "customer support", "pricing/offers", "other"]

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

gold = pd.read_excel("gold_set_labeled.xlsx")
gold = gold[gold["language_type"].isin(["English", "Hinglish"])].copy()

PROMPT = """Find the main pain point in this customer review.
Return only JSON with these keys:
"theme": one of {themes}
"severity": one of low, medium, high
"quote": the exact words from the review that show the problem

Review: {review}"""

rows = []
for _, r in gold.iterrows():
    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=PROMPT.format(themes=THEMES, review=r["content"]),
            config={"response_mime_type": "application/json"},
        )
        out = json.loads(resp.text)
    except Exception as e:
        print("ERROR:", e)
        out = {"theme": "ERROR", "severity": "", "quote": str(e)[:80]}
    rows.append({
        "review_id": r["review_id"],
        "language_type": r["language_type"],
        "gold_theme": r["theme"],
        "ai_theme": out.get("theme", ""),
        "gold_severity": r["severity"],
        "ai_severity": out.get("severity", ""),
        "ai_quote": out.get("quote", ""),
        "quote_valid": str(out.get("quote", "")).strip() in str(r["content"]),
    })
    print("done", r["review_id"])
    time.sleep(4)

res = pd.DataFrame(rows)
res["theme_correct"] = res["gold_theme"] == res["ai_theme"]
res.to_csv("results_A.csv", index=False)

print("\nVersion A results")
print(res.groupby("language_type")[["theme_correct", "quote_valid"]].mean().round(2))
print("Errors:", (res["ai_theme"] == "ERROR").sum())