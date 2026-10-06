import os, json, time
import pandas as pd
import streamlit as st
from google import genai

MODEL = "gemini-3.1-flash-lite"
MAX_REVIEWS = 50

THEMES = ["payment failure", "login/OTP", "app crash/bug", "refund",
          "order/delivery", "customer support", "pricing/offers", "other"]
LANGUAGES = ["English", "Hinglish", "Hindi script", "Bengali", "Tamil",
             "Telugu", "Marathi", "Other language"]
TESTED = ["English", "Hinglish"]

PROMPT = """You analyse app-store reviews written by Indian users. Reviews may be in
English, Hinglish (Hindi words written in English letters), or other languages.
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

Language: choose the language of the review from {languages}.
"Hinglish" means Hindi words written in English letters (mixed with English or alone).
"Hindi script" means Hindi written in Devanagari letters.
Bengali, Tamil, Telugu and Marathi count in any script, including English letters.

Return only JSON with these keys:
"language": one of {languages}
"theme": one of {themes}
"severity": one of low, medium, high
"quote": exact words copied from the review, without changing spelling or translating
         (empty string if the theme is "other" and there is no specific problem)

Review: {review}"""


def analyse(client, review):
    for attempt in range(2):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=PROMPT.format(languages=LANGUAGES, themes=THEMES, review=review),
                config={"response_mime_type": "application/json"},
            )
            out = json.loads(resp.text)
            if isinstance(out, list) and out:
                out = out[0]
            return out
        except Exception:
            time.sleep(6)
    return {"language": "", "theme": "ERROR", "severity": "", "quote": ""}


def clean(text):
    for ch in "[]*_`":
        text = text.replace(ch, " ")
    return text


st.set_page_config(page_title="Voice of customer copilot", layout="centered")
st.title("Voice of customer copilot")
st.write("Paste app reviews in English or Hinglish. Get the main problem in each one, "
         "with the exact words as proof. Other languages are detected and reported separately.")

key = os.environ.get("GEMINI_API_KEY")
if not key:
    st.error("No Gemini key found. Set GEMINI_API_KEY and start the app again.")
    st.stop()

text = st.text_area("Paste reviews, one per line", height=180,
                    placeholder="Paisa kat gaya lekin order confirm nahi hua\nApp is very slow at night")
upload = st.file_uploader("Or upload a CSV (uses a column named content, or the first column)", type="csv")

if st.button("Analyse reviews"):
    reviews = [l.strip() for l in text.splitlines() if l.strip()]
    if upload is not None:
        df_in = pd.read_csv(upload)
        col = "content" if "content" in df_in.columns else df_in.columns[0]
        reviews += [str(x).strip() for x in df_in[col].dropna() if str(x).strip()]

    if not reviews:
        st.error("Paste at least one review first.")
        st.stop()
    if len(reviews) > MAX_REVIEWS:
        st.warning(f"Only the first {MAX_REVIEWS} reviews are analysed in one run.")
        reviews = reviews[:MAX_REVIEWS]

    client = genai.Client(api_key=key)
    rows = []
    bar = st.progress(0.0, text="Reading reviews")
    for i, rev in enumerate(reviews):
        out = analyse(client, rev)
        quote = str(out.get("quote", "")).strip()
        rows.append({
            "review": rev,
            "language": out.get("language", ""),
            "theme": out.get("theme", ""),
            "severity": out.get("severity", ""),
            "quote": quote,
            "quote_found": (quote in rev) if quote else True,
        })
        bar.progress((i + 1) / len(reviews), text=f"Read {i + 1} of {len(reviews)}")
        time.sleep(2)
    bar.empty()
    st.session_state["results"] = pd.DataFrame(rows)

if "results" in st.session_state:
    res = st.session_state["results"]
    total = len(res)

    st.subheader("Languages found")
    lang = res["language"].replace("", "Not detected").value_counts().rename_axis("language").reset_index(name="reviews")
    lang["share"] = (lang["reviews"] / total * 100).round(0).astype(int).astype(str) + "%"
    lang["tested"] = lang["language"].apply(lambda x: "yes" if x in TESTED else "no")
    st.dataframe(lang, hide_index=True, width="stretch")

    untested = res[~res["language"].isin(TESTED)]
    if len(untested):
        pct = round(len(untested) / total * 100)
        st.warning(f"{len(untested)} of {total} reviews ({pct}%) are outside the tested languages "
                   "(English and Hinglish). Check those results by hand.")

    st.subheader("Main problems (English and Hinglish reviews)")
    tested = res[res["language"].isin(TESTED) & (res["theme"] != "ERROR")]
    if len(tested):
        th = tested["theme"].value_counts().rename_axis("theme").reset_index(name="reviews")
        st.dataframe(th, hide_index=True, width="stretch")
    else:
        st.write("No English or Hinglish reviews in this run.")

    st.subheader("Each review")
    for _, r in res.iterrows():
        with st.container(border=True):
            st.markdown(f"**{r['theme']}**  ·  {r['severity']}  ·  {r['language'] or 'language not detected'}")
            st.write(r["review"])
            if r["quote"]:
                if r["quote_found"]:
                    st.markdown(f"Proof: :orange-background[{clean(r['quote'])}]")
                else:
                    st.caption("The AI's quote was not found word for word in the review. Check it by hand.")
            if r["language"] not in TESTED:
                st.caption("Language outside the tested range. Check this result by hand.")

    st.download_button("Download results as CSV", res.to_csv(index=False).encode("utf-8-sig"),
                       file_name="voc_results.csv", mime="text/csv")