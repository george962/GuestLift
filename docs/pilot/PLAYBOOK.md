# Restaurant pilot playbook

What to show owners, what to say, and what happens after they say yes. Companion to `docs/PILOT_TRUST_PLAN.md` (the why and the safety gates) and `docs/PRODUCT_PLAN.md`.

**Materials** (open `docs/pilot/pilot-kit.html` in a browser; print it, or show it on a phone):
- **Sample weekly brief:** the Monday email an owner would get. This is what you sell.
- **"What we can see" sheet:** hand this over only once Gate P0 in the trust plan is checked. Until then you're only asking for Level 1 (an export they choose to send), not account access.

## The pitch in one sentence
> "Every Monday you get a short email that tells you what changed at your restaurant last week, whether your promotions are paying off, and how the changes you made turned out — straight from your Square data."

## Your targets
| Stage | Goal | Typical conversion |
|---|---|---|
| Conversations (intro, walk-in, call) | 20 | — |
| Interviews (30 min) | 8 | ~40% of conversations |
| Concierge reviews (they send an export) | 5 | ~60% of interviews |
| Read-only connections (after Gate P0) | 3 | ~60% of concierge reviews |

Track each owner in a spreadsheet: name, restaurant, locations, how you met, stage, next step and date, what they said they care about, and objections.

## 1. Getting the conversation

**Who to look for:** independent restaurants on Square with 1–5 locations, where the owner is reachable and runs promotions or a loyalty program. Look for the Square reader at the counter and loyalty cards or QR codes.

**Best source, warm intros.** Message friends, restaurant accountants or bookkeepers, Square consultants and local restaurant groups:
> "I'm building a tool that turns a restaurant's Square data into a short weekly email: what changed, whether promos paid off, and how changes worked out. I'm looking for 5 owners to try it free and tell me what's useful. Do you know an owner on Square who'd give me 15 minutes?"

**Message to an owner** (text or email after an intro):
> "Hi [name], [connector] suggested I reach out. I'm building a weekly report for Square restaurants. It shows what changed last week and whether your discounts are bringing people in. I'm not selling anything yet. I'd value 15 minutes of your thoughts, and I'll do a free review of your last 3 months in return. Would [two specific times] work?"

**Walk-in** (go 2–4pm on a weekday, never during a rush; buy something first):
> "I'm working on a free weekly report for restaurants on Square. It shows things like whether a discount actually brought people back. Could I leave this with you and follow up next week?" Leave the printed sample brief with your name and number on it.

**Follow-up** (3–4 days later, once):
> "Following up on the sample report I left. I'd love 15 minutes to hear how you decide on promotions today. I'm free [times]."

## 2. The 15-minute first conversation

| Minutes | Do | Say or ask |
|---|---|---|
| 0–2 | Set up | "I want to learn how you run things, then show you one thing. It isn't a sales pitch." |
| 2–6 | Ask, listen | "What decisions do you make each week? How did you decide on your last promotion? How did you know if it worked? What do you look at in Square today?" |
| 6–9 | Show the sample brief | Point to finding 2 (the promo that mostly went to regulars) and the decision readout. "Would knowing this have changed anything for you?" |
| 9–12 | The offer | "If you export your last 3 months from Square, I'll send you a report like this about your restaurant in 2 days. Free, and you don't give me any account access." |
| 12–15 | Agree on next step | Walk them through the export on their phone or laptop right there if you can. Book a 20-minute review call for 2–3 days later. |

**What to listen for:** a specific decision they agonized over, such as a promo, hours, staffing or a menu change. Also money they suspect they're wasting, and things they check in Square more than weekly. Write their exact words down; they shape what the brief shows.

## 3. The concierge review (Level 1, no account access)

**What the owner sends:**
1. In Square Dashboard, go to **Reports → Sales summary**. Set the date range to the last 3 months, choose **Export**, and pick CSV.
2. In **Transactions**, set the same date range, choose **Export**, and pick **Transactions CSV**.
3. Optional: **Reports → Discounts** for the same range.
4. They email the files to you. Ask them to remove customer names if the export includes them, or tell them you'll delete those columns immediately.

**What you do within 48 hours:**
1. Delete any customer name, email or phone columns on receipt.
2. Build their brief, using the sample's format. Claude can turn the export into the brief; see "What Claude does" below.
3. Hold a 20-minute review call: walk through it. Ask: "Is anything wrong? What would you do differently because of this? What's missing?"
4. Delete the export when the review is done, and tell them you did.

**The ask at the end** (only once Gate P0 is checked):
> "Want to get this every Monday automatically? You'd connect Square with read-only access, which you can turn off yourself anytime. In the first week we'll check our numbers against your Square reports together." Hand them the "What we can see" sheet.

## 4. Objections

| They say | You say |
|---|---|
| "Square already shows me this." | "It shows totals. It doesn't tell you that most of your discount went to people who'd have come anyway, or follow up on whether your hours change worked. That's the part we add." Point at finding 2 and the readout. |
| "I don't have time." | "It's one email on Monday, about 2 minutes to read. The setup is a 5-minute export, or a few clicks later." |
| "Is my data safe? What will you do with it?" | "Right now I'm only asking for an export you choose to send. I delete it after the review. If you connect later, it's read-only, I can't touch your menu, payments or customers, and you can switch it off yourself." Show the sheet. |
| "What does it cost?" | "Free during the pilot. After that we're thinking around $99 a month per location, and I'd like your honest view on whether that's worth it." |
| "Are you a real company?" | Give your name, phone number and a written pilot agreement. Don't overstate team size or customer count. |
| "My numbers are different from yours." | "Good. Show me where. Matching Square is the first thing we check, and I'll fix it before you rely on anything." |

## 5. Rules for you
- Never claim a number you haven't checked against their Square report.
- Never say a change *caused* something. Say "after the change, X happened".
- Never ask for their Square login or password. Connections only ever go through Square's approval screen.
- Don't connect real accounts before Gate P0 in `docs/PILOT_TRUST_PLAN.md` is fully checked.
- Write up every conversation the same day.

## 6. What Claude does for you
- **Turns each export into a brief.** Send me the first real export with names removed and I'll build `scripts/concierge_brief.py` against the actual file format. Every later export then takes minutes, and I'll flag anything that doesn't add up.
- **Meeting prep:** paste a restaurant's name, location count and what you know, and I'll give you the questions and examples that fit them.
- **Interview synthesis:** paste your notes and I'll pull out the repeated needs, quotes and objections, and propose changes to what the brief prioritizes (PRODUCT_PLAN M4).
- **Materials:** tailoring the sample brief to a restaurant type (café, quick service, full service), plus a printable one-pager and follow-up emails.
- **The product:** building what the plan says, in order, so the automated brief matches what you showed them.

## 7. To show the live demo on your phone
The public demo isn't hosted yet. Until it is, show it on your laptop (`docker compose up -d`, then http://localhost:3000/workspace) or use the printed sample. Hosting the fictional demo is safe and quick once a Render account exists. It's in M6 of the plan.
