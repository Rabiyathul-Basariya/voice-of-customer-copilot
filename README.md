# Voice of Customer Copilot

A small AI tool that reads app reviews written in **English or Hinglish** (Hindi words in English letters), finds the main problem in each review, and highlights the **exact words** it based that on, so a product manager can check every result against the source.

![Languages found and main problems](screenshots/languages.png)
![Result cards with highlighted proof](screenshots/results.png)

## Why I built it

Many Indian app users write reviews in Hinglish ("paisa kat gaya lekin order confirm nahi hua"). I wanted to test one question: **is an AI model less accurate on Hinglish reviews than on English ones, and can a better prompt close the gap?**

## What the tool does

1. Paste reviews or upload a CSV.
2. For each review it returns the **theme** (payment failure, login/OTP, app crash/bug, refund, order/delivery, customer support, pricing/offers, other), a **severity**, the **language**, and a **proof quote**.
3. It checks that every proof quote really appears in the review, and flags it if not.
4. It reports the share of reviews by language. Languages I did not test (Hindi script, Bengali and others) are listed separately and marked "check by hand".

## How I tested it

- **Data:** about 8,000 Play Store reviews from Swiggy, IRCTC, PhonePe and Meesho. I kept low-star reviews with at least 6 words. A keyword check found no Tanglish (Tamil-English) reviews, so I narrowed the project to English vs Hinglish.
- **Answer key:** 100 reviews labeled for language, theme, severity and key quote. The labels were drafted with AI help and reviewed by me. 97 were English or Hinglish and were scored.
- **Three prompt versions**, all run with Gemini on the same 97 reviews:
  - **A:** a basic prompt.
  - **B:** a prompt that explains Hinglish and asks the model to translate first.
  - **C:** a prompt with clear definitions for each theme and a firm rule for when to use "other".

## Results

| Theme accuracy (97 labeled reviews) | English | Hinglish |
|---|---|---|
| A: basic prompt | 90% | 78% |
| B: Hinglish-aware prompt | 88% | 73% |
| C: clear theme rules | 96% | 90% |

Proof quotes found word for word in the review (version C): English 100%, Hinglish 98%.

**Pilot on new reviews.** I ran version C on 50 new Meesho reviews it had never seen. 47 were English or Hinglish. The results were checked by Claude (an AI) and reviewed by me.

| Pilot (new reviews) | English | Hinglish |
|---|---|---|
| Theme right | 18 of 22 (82%) | 21 of 25 (84%) |

The language tag was right for 49 of 50 reviews, and every proof quote was found in its review.

## What I learned

- **Telling the model about Hinglish (B) did not help.** It scored lower than the basic prompt.
- **Clear theme rules (C) helped most.** Most mistakes came from vague or multi-issue reviews and from single words that misled the model (for example "delivery" or "login" appearing in a sentence about something else), not from the language itself.
- **The first result was too good.** I wrote the rules for C after studying its mistakes on the same reviews, so 96% and 90% are optimistic. On new reviews the numbers were 82% and 84%. I report both.
- **In the pilot, Hinglish was not worse than English.** The difference is within noise on about 25 reviews per group.

## Limits

- Small samples: 97 labeled reviews and a 47-review pilot, so a difference of a few points is about 2 or 3 reviews.
- The labels were drafted with AI help, and the pilot was checked by an AI before my review. A fully independent human label set would be stronger.
- Version C was tuned on the set it was scored on.
- The pilot uses one app (Meesho).
- Hindi script and other languages are not tested. The tool flags them but I cannot vouch for their accuracy.
- The theme list has gaps: returns and wrong items, seat or berth allocation, and reviews that do not go live had no clean home and often ended up in "other".

## Run it yourself

You need Python and a free Gemini API key from Google AI Studio.

```
pip install -r requirements.txt
set GEMINI_API_KEY=your_key        (Windows Command Prompt)
streamlit run app.py
```

In PowerShell use `$env:GEMINI_API_KEY="your_key"` instead of `set`. Never commit your key to GitHub.

## Files

- `app.py`: the Streamlit tool
- `run_version_a.py`, `run_version_b.py`, `run_version_c.py`: the three prompt tests
- `requirements.txt`: Python packages

## Privacy

Reviews you paste are sent to Google's Gemini API for analysis. Do not paste private or personal data.
