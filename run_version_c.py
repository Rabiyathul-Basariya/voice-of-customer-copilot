import os, json, time
import pandas as pd
from google import genai

MODEL = "gemini-3.1-flash-lite"

THEMES = ["payment failure", "login/OTP", "app crash/bug", "refund",
          "order/delivery", "customer support", "pricing/offers", "other"]

# Corrections decided after the failure analysis (review_id: final theme)
FIXES = {
    12: "other", 16: "other", 18: "other", 19: "app crash/bug", 25: "other",
    36: "other", 37: "app crash/bug", 38: "other", 39: "other",
    41: "order/delivery", 53: "refund", 56: "other", 59: "payment failure",
    60: "payment failure", 61: "order/delivery", 62: "app crash/bug",
    64: "other", 70: "customer support", 74: "other", 76: "other",
    80: "refund", 84: "other", 85: "app crash/bug", 88: "other",
    91: "refund", 95: "other",
}

# ---------- 1. Build the corrected answer key ----------
gold = pd.read_excel("gold_set_labeled.xlsx")
gold["theme"] = gold.apply(lambda r: FIXES.get(r["review_id"], r["theme"]), axis=1)
gold.to_excel("gold_set_final.xlsx", index=False)
print("Saved gold_set_final.xlsx (", len(FIXES), "themes corrected )")
gold = gold[gold["language_type"].isin(["English", "Hinglish"])].copy()

# ---------- 2. Re-score Versions A and B on the corrected key ----------
def rescore(path):
    df = pd.read_csv(path).drop(columns=["gold_theme"])
    df = df.merge(gold[["review_id", "theme"]], on="review_id")
    df["theme_correct"] = df["theme"] == df["ai_theme"]
    return df

scores = {}
for name, path in (("A", "results_A.csv"), ("B", "results_B.csv")):
    scores[name] = rescore(path).groupby("language_type")["theme_correct"].mean()

# ---------- 3. Version C ----------
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PROMPT = """You analyse app-store reviews written by Indian users. Reviews may be in
English or Hinglish (Hindi words written in English letters, informal spelling).
Read the whole review in its original language and find the ONE main pain point.

Themes and when to use them:
- payment failure: money deducted or stuck, payment or transfer fails, payment takes too long, wrong amount charged.
- login/OTP: cannot log in, OTP not received, account will not open, password or reset problems.
- app crash/bug: app is slow, hangs, will not open, errors, or booking/ordering is impossible because the app or server fails (for example "high load").
- refund: the user wants money back, a refund or return is refused, delayed or not completed.
- order/delivery: order or product not delivered, late, wrong or missing items, order cancelled.
- customer support: the main complaint is that support does not reply, does not help or is rude.
- pricing/offers: fees, charges, taxes, prices, cashback or offers.
- other: use this when the review has no specific problem (only anger, insults or general praise or complaint such as "worst app"), when it is a question or a feature request, or when the problem fits none of the themes above.

Rules:
1. Judge the whole complaint, not a single word. The word "delivery" in a request, or "login" in a sentence about slowness, does not decide the theme.
2. If the review has no specific, concrete problem, choose "other". Do not guess a theme.
3. If several problems are mentioned, choose the one the user stresses most or mentions first.

Severity: high = money lost, app unusable, or an order/booking failed;
medium = repeated or very annoying problem; low = small annoyance, vague complaint or request.

Return only JSON with these keys:
"theme": one of {themes}
"severity": one of low, medium, high
"quote": exact words copied from the review, without changing spelling or translating
         (empty string if the theme is "other" and there is no specific problem)

Review: {review}"""

def ask(review):
    for attempt in range(2):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=PROMPT.format(themes=THEMES, review=review),
                config={"response_mime_type": "application/json"},
            )
            out = json.loads(resp.text)
            if isinstance(out, list) and out:
                out = out[0]
            return out
        except Exception as e:
            print("ERROR:", e)
            time.sleep(8)
    return {"theme": "ERROR", "severity": "", "quote": ""}

rows = []
for _, r in gold.iterrows():
    out = ask(r["content"])
    q = str(out.get("quote", "")).strip()
    rows.append({
        "review_id": r["review_id"],
        "language_type": r["language_type"],
        "gold_theme": r["theme"],
        "ai_theme": out.get("theme", ""),
        "gold_severity": r["severity"],
        "ai_severity": out.get("severity", ""),
        "ai_quote": q,
        "quote_valid": (q in str(r["content"])) if q else True,
    })
    print("done", r["review_id"])
    time.sleep(4)

res = pd.DataFrame(rows)
res["theme_correct"] = res["gold_theme"] == res["ai_theme"]
res.to_csv("results_C.csv", index=False)
scores["C"] = res.groupby("language_type")["theme_correct"].mean()

# ---------- 4. Final comparison ----------
table = pd.DataFrame(scores).round(2)
table["gap (English - Hinglish)"] = None
print("\nTheme accuracy on the corrected answer key")
print(pd.DataFrame(scores).round(2))
print("\nVersion C quote validity:")
print(res.groupby("language_type")["quote_valid"].mean().round(2))
print("Version C errors:", (res["ai_theme"] == "ERROR").sum())