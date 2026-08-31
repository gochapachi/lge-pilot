#!/usr/bin/env python3
"""chatflow.py — the LGE relationship-manager engine (CHAtFLOW.md implementation).

Pure decision layer: given a lead + recent history, returns the next turn
(bubbles + state deltas + logging hints). No I/O. bridge.py applies the actions.
LLM is used ONLY to phrase the turn warmly in Hinglish; every turn has a canned
fallback so the engine never dead-ends.

Design contract (CHATFLOW.md):
- discovery before pitch, never 2 questions in a row, mirror their words,
  empathy line before any counter, one small next step per turn,
  demo = blank assets, log every delta.
"""
import json, re

# ---------- discovery ----------
DQS = {
    1: "Aapke customers abhi aate kaise hain — Google, walk-in, ya jaan-pehchaan se?",
    2: "Aur Google listing/reviews ka dhyan abhi kaun rakhta hai — aap khud ya koi staff?",
    3: "Sabse zyada dikkat kis cheez me lagti hai — naye customer, reviews ka jawab, ya online dikhna?",
    4: "In sab ke liye time nikal pate hain aap, ya din to patients/customers hi nikaal dete hain? 😅",
    5: "Aap results kaise check karte hain — koi system hai ya andaza?",
    6: "Agar ye sab automatic ho jaye to monthly kitna kharcha sahi lagega — ₹5k, ₹10k, ₹15k+?",
}
DQ_ORDER = [1, 2, 3, 4, 5, 6]  # 5-6 only after 1-4 answered

OBJECTIONS = [
    (r"(website|site).*(banw|hai|wala|guy)", "existing_web"),
    (r"(mehng|mahng|expensive|price|daam|₹| Paisa|kharch|budget nahi|paise)", "price"),
    (r"(baad me|soch|next year|gli|faisla|discuss)", "think"),
    (r"(demo|dikhao|dikha do|sample|preview)", "want_demo"),
    (r"(already|pehle se|koi (handle|dekh|sambhal)|agency|kaam karta)", "already_have"),
    (r"(result|guarantee|dikhega|assek|proof|kamaya)", "results"),
    (r"(chat\s?bot|bot ho|insaan|real human|aap ai|机器|robot)", "ai_suspect"),
    (r"(number kahan|kahan se (mila|aaya)|source)", "number_source"),
]
OPT_OUT = ("nahi chahiye", "mat bhejo", "stop", "not interested", "no thanks",
           "remove karo", "unsubscribe", "pareshan", "bhejna band", "block kar")

BLANK_DEMO = {
    "dentist": "https://pilot-staging.anagataitsolutions.in/demo_dentist.png",
    "salon": "https://pilot-staging.anagataitsolutions.in/demo_salon.png",
    "default": "https://pilot-staging.anagataitsolutions.in/demo_default.png",
}
DEMO_VIDEO_NOTE = "(video demo bhi bana hua hai — us se pehle ye quick dekh lijiye)"


def answered_dqs(tags):
    out = {}
    for t in tags or []:
        m = re.match(r"dq(\d)=(.+)", t)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def tag_kv(tags, key):
    for t in tags or []:
        if t.startswith(key + "="):
            return t[len(key) + 1:]
    return None


def set_tag(tags, key, val):
    tags = [t for t in (tags or []) if not t.startswith(key + "=")]
    tags.append(f"{key}={val}")
    return tags


def detect_objection(text):
    low = (text or "").lower()
    for pat, key in OBJECTIONS:
        if re.search(pat, low, re.I):
            return key
    return None


def is_opt_out(text):
    low = (text or "").lower()
    return any(p in low for p in OPT_OUT)


def fu_count(lead):
    return int(tag_kv(lead.get("tags"), "fu") or 0)


# ---------- the turn builder ----------

PHASES = ["opening", "rapport", "probing", "need_gen", "solutions", "urgency", "sales"]
PHASE_TO_STAGE = {"opening": "contacted", "rapport": "replied", "probing": "probing",
                  "need_gen": "probing", "solutions": "demo_sent",
                  "urgency": "negotiating", "sales": "negotiating"}
STAGE_TO_PHASE = {v: k for k, v in PHASE_TO_STAGE.items()}


def phase_of(lead):
    """Phase lives in tags['phase']; default from DB stage for old leads."""
    p = tag_kv(lead.get("tags"), "phase")
    if p in PHASES:
        return p
    return STAGE_TO_PHASE.get(lead.get("stage") or "contacted", "opening")


def next_turn(lead, history):
    """history oldest→newest. Returns {bubbles, fallback, stage, tags, phase,
    kind, ask_dq, echo, objection, next_action_at_days, meta}."""
    phase = phase_of(lead)
    tags = list(lead.get("tags") or [])
    answered = answered_dqs(tags)
    last_in = next((h for h in reversed(history) if h["dir"] == "in"), None)
    text = (last_in or {}).get("text", "")
    low = text.lower()
    business = (lead.get("business") or lead.get("name") or "aapka business").split()[0]
    intent_words = ("haan", "ha", "yes", "ok", "theek", "chalo", "karo", "shuru",
                    "bhejo", "bhej do", "kaise milega", "kya karte")

    # opt-out & unknown-number questions: handled in ANY phase
    if is_opt_out(text):
        return {"bubbles": ["theek hai ji, aage koi message nahi aayega 🙏 shubhkamnayein!"],
                "stage": "closed_lost", "tags": tags, "phase": "closed_lost",
                "kind": "optout_ack", "next_action_at_days": None, "meta": {"optout": True}}
    if detect_objection(text) == "number_source":
        t = objection_turn("number_source", business, lead, answered)
        t["phase"] = phase
        return t

    # ---------- PHASE LADDER (strict order, guards) ----------

    # OPENING: crack the ice. warm ack + one soft HUMAN question. no business, no pitch.
    if phase == "opening":
        if _substantive(text):
            # their first substantive reply → advance to rapport, mirror + human q
            return _phased(None,
                [mirror(text), "waise aaj ka din kaisa gaya — kaam mein maza aa raha hai ya routine chal raha hai? 🙂"],
                "rapport", tags, "opening_ack", echo=text)
        return _phased(None,
            ["namaste 🙏 main Sanjeev ji ki team se — aapka business Google pe dekha, achha lag raha hai",
             "bas aapka din kaisa ja raha hai?"],
            "opening", tags, "opening_re", echo=text)

    # RAPPORT: human exchange. exit when warm exchange done → weave DQ1
    if phase == "rapport":
        if re.search(r"(achha|theek|badhiya|maza|busy|thik|thik hai|chalt[aā])", low):
            return _phased(None,
                [mirror(text, 70), "sunno, ek kaam ka sawaal poochhoon? aapke customers abhi aate kaise hain — Google, walk-in, ya jaan-pehchaan se?"],
                "probing", tags, "rapport_to_probing", echo=text, ask_dq=1)
        return _phased(None,
            [mirror(text, 70), "aur aap? sab badhiya? 🙂"],
            "rapport", tags, "rapport_warm")

    # PROBING: DQ loop, one per turn
    if phase == "probing":
        if all(d in answered for d in (1, 2, 3, 4)):
            return _need_gen_turn(text, business, tags, echo=text)
        nxt = next((d for d in DQ_ORDER if d not in answered), None)
        return _phased(None, [mirror(text), DQS[nxt]], "probing",
                       set_tag(tags, f"dq{nxt}", "asked"), "discovery",
                       echo=text, ask_dq=nxt)

    # NEED_GEN: reflect + quantify + agreement check (no demo, no price)
    if phase == "need_gen":
        if re.search(r"\b(haan|sahi|ha|bilkul|theek|yes|done|ok)\b", low):
            return _phased(None,
                ["to chaliye, pehle aapke kaam ka ek chhota sa proof dikhata hoon — blank template abhi, final aapke naam pe",
                 "dekhiye ye 👇 " + BLANK_DEMO.get(lead.get("niche"), BLANK_DEMO["default"])],
                "solutions", tags, "need_to_solutions")
        return _phased(None,
            ["dekh rahe hain — " + (tag_kv(tags, "pain") or "jo bataya aapne") + ", aur time bhi nahi — ye combo hi asli dikkat hai",
             "sach kahun? ye gap har mahine kuch na kuch cost karta hai — naye customer, unreplied reviews, purani listing",
             "sahi kah raha hoon main? 🙂"],
            "need_gen", tags, "need_gen")

    # SOLUTIONS: pitch mapped to their pains + blank demo + walkthrough
    if phase == "solutions":
        if re.search(r"\b(kaise|kab|milega|chalu|shuru|price|kitn|pasand|achha|acha|theek|badhiya|sahi|dekha|dek liya|dekh liya)\b", low):
            return _phased(None,
                ["aapke jo pains bataye the — usi ke hisaab se: reviews ka same-day reply, bura review pehle aapke paas private, weekly blogs + posts, aur ye WhatsApp brain",
                 "system aapke naaam pe chalta hai, aapka time zero",
                 "ab ek baat — is mahine main sirf 4 clinics onboard kar raha hoon, 2 seats bachi hain — aage badhein? 🙂"],
                "urgency", tags, "sol_to_urgency")
        return _phased(None,
            ["demo dekh ke kaisa laga — kaunsa hisaab aapke kaam ka laga?",
             "jo hisaab pasand aaya wahi aapke business ke naam pe har hafte automatic chalega"],
            "solutions", tags, "solutions_follow")

    # URGENCY: seats/gap/founding framing + A/B choices (NO link)
    if phase == "urgency":
        if re.search(r"\b(haan|ha|chalo|karo|shuru|kar do|bhej|link|payment|kaise (milega|pay))\b", low):
            return _phased(None,
                ["badhiya 🙏 phir ab bas ek kaam — payment link isi chat pe bhej deta hoon, 2 min ka kaam",
                 "link aa raha hai…"],
                "sales", tags, "urgency_to_sales")
        return _phased(None,
            ["ek smart choice dena chahta hoon 🙂 (a) trial month ₹15,000 sab setup included, ya (b) pehle 15 din ka dekh lena, pasand na aaye to seedha boliye",
             "aur seats is mahine sirf 2 bachi hain — jo clinic pehle le, Google pe wahi pehle dikhega"],
            "urgency", tags, "urgency")

    # SALES: link + confirmation
    if phase == "sales":
        return _phased(None,
            ["link ready: trial ₹15,000 (test mode in drill — real paisa nahi katenga)",
             "payment hone ke baad hi 'won' mark hota hai aur prod pe sab live 🚀"],
            "sales", tags, "sales_link")

    if phase == "closed_lost":
        return {"bubbles": ["theek hai ji 🙏"], "stage": "closed_lost", "tags": tags,
                "phase": "closed_lost", "kind": "muted", "next_action_at_days": None}

    if phase == "closed_won":
        return _phased(None,
            ["badhai ho — {b} family me swagat 🎉 day 1 me sab live".format(b=business)],
            "closed_won", tags, "onboard")

    # fallback: stay in phase
    return _phased(None, ["ji boliye, main hoon 🙂"], phase, tags, "clarify")


def _substantive(text):
    """More than a bare greeting or lone 'haan/ok'."""
    t = (text or "").strip().lower()
    if len(t) < 4:
        return False
    return not re.fullmatch(r"(ha+|hm+|ok+|yes+|theek|achha|sahi|k)[\s!.]*", t)


def _phased(bubbles, fallback, phase, tags, kind, echo=None, ask_dq=None, objection=None,
            next_action_at_days=1, meta=None):
    return {"bubbles": bubbles, "fallback": fallback, "stage": PHASE_TO_STAGE.get(phase),
            "tags": tags, "phase": phase, "kind": kind, "echo": echo, "ask_dq": ask_dq,
            "objection": objection, "next_action_at_days": next_action_at_days, "meta": meta or {}}


def _need_gen_turn(text, business, tags, echo=None):
    pain = tag_kv(tags, "pain") or tag_kv(tags, "dq3") or "naye customer nahi aa rahe"
    return {"bubbles": None,
            "fallback": [
                'to suno — aapne kaha "' + (tag_kv(tags, "dq3") or "naye customer nahi aa rahe")[:40] + '" aur time bhi nahi hai sab sambhalne ka',
                "Google pe jo gap dikh raha hai — unreplied reviews, purani listing — wahi competitor ko naye customer la raha hai",
                "sahi kah raha hoon main? 🙂"],
            "stage": "probing", "tags": set_tag(tags, "pain", pain[:30]), "phase": "need_gen",
            "kind": "need_gen", "echo": echo, "next_action_at_days": 1}


def mirror(text, limit=90):
    t = re.sub(r"\s+", " ", (text or "").strip())
    frag = t[: int(limit)] + ("…" if len(t) > int(limit) else "")
    if not t:
        return "achha 🙂"
    return f'aapne kaha — "{frag}" — theek, samajh gaya 🙏'


def objection_turn(obj, business, lead, answered):
    """Empathy line → counter (BYJU'S rehearsed) → small next step. Returns dict or None."""
    P = None
    if obj == "existing_web":
        P = ["perfect — website wale ko rakhiye, wo site banata hai; hum wo karte hain jo site nahi karti: reviews ka same-day reply, weekly blogs/posts, aur isi chat jaisi WhatsApp presence",
             "aap bas dekh lijiye 15 din — {'haan' agar interesting lage 🙂'}"]
    elif obj == "price":
        P = ["bilkul sahi sawaal 🙏 ek comparison dete hain: ek staff hire karo ₹12k+/mahina (fixed, aur training bhi aapki) — ye system ₹15k trial me sab automatic + aapka time zero",
             "aur ek naya customer hi isko cover kar deta hai — ye kharcha nahi, investment hai",
             "15 din me koi fark na dikhe to seedha bol dena — band kar dungen 🙏 chalen aage?"]
    elif obj == "think":
        P = ["ji soch lijiye 🙏 ek hi cheez yaad rakhiyega — jo Google ka gap aaj dikh raha hai, wahi gap aapke paas wale competitor ko naye customer la raha hai",
             "demo ek baar dekh lijiye, nahi pasand aaya to bas boliye — koi zabardasti nahi"]
    elif obj == "want_demo":
        demo = BLANK_DEMO.get(lead.get("niche"), BLANK_DEMO["default"])
        P = ["ye lijiye 👇 (blank template abhi — final aapke business ke naam pe banta hai)",
             f"{demo}\n{DEMO_VIDEO_NOTE}",
             "dekho batana — kaunsa hisaab aapke kaam ka laga?"]
        return {"bubbles": None, "fallback": P, "stage": "demo_sent",
                "tags": set_tag(lead.get("tags") or [], "demo", "sent"),
                "kind": "demo", "next_action_at_days": 1}
    elif obj == "already_have":
        P = ["achha, that's fine — hum kisi ko replace nahi karte; jo wo nahi karte wahi hum karte hain: reviews, blogs, posts, WhatsApp — 30 min/din ka fark padta hai",
             "ek chhota demo bhejoon? dekh ke hi bata dijiyega 🙂"]
    elif obj == "results":
        P = ["sahi baat — numbers se hi pata chalega: is mahine ke reply-rate, naye reviews, calls ka difference sab aapke client dashboard pe dikhega (login code isi chat pe milega)",
             "trial month me hi dikh jayega ki Google se log aa rahe hain ya nahi 🙏"]
    elif obj == "ai_suspect":
        P = ["100% sach: main Sanjeev ji ka AI relationship manager hoon — aapse wahi karta hoon jo promise hota hai aur background me system reviews/blogs/posts handle karta hai",
             "koi jaali baat nahi — jo nahi ho sakta wo promise nahi karta 🙂"]
    elif obj == "number_source":
        P = ["aapka number aapke business ki public Google listing se aaya — jo bhi business public me hai wo sab dekh sakte hain",
             "agar ye kaam ka nahi lagta to bas bata dijiye, main aage nahi pareshan karunga 🙏"]
    if not P:
        return None
    return {"bubbles": None, "fallback": P, "stage": "negotiating" if obj == "price" else None,
            "tags": set_tag(lead.get("tags") or [], "objection", obj),
            "kind": "objection", "objection": obj, "next_action_at_days": 1}


def followup_turn(lead, n):
    """n = 1-based follow-up number for this lead (D2/D3/D5 cadence)."""
    business = (lead.get("business") or lead.get("name") or "aapka business").split()[0]
    if n == 1:
        return ["{b} ji, chhota follow-up 🙏 Kakadeo ke ek clinic ne isse mahine kaafi naye patients dekhe — aapki listing me bhi wahi chamak aa sakti hai",
                "aapka call kab rakhhein — aaj ya kal?"].replace("{b}", business)
    if n == 2:
        return ["ek choice dena chahta hoon 🙂 — (a) 2-min demo WhatsApp pe hi dekh lijiye, ya (b) main 10-min me aapke business ka plan bana ke bhej doon — kya pasand?",
                "dono me se jo aasan ho bas reply kar dijiye"]
    if n >= 3:
        return ["aakhri message ji 🙏 agar abhi time nahi hai to 'later' likh dein — main 2 hafte baad yaad dila dunga",
                "demo: " + BLANK_DEMO.get(lead.get("niche"), BLANK_DEMO["default"])]
    return []


# ---------- LLM phrasing (optional; canned fallback always exists) ----------

PHRASE_SYS = """You are the WhatsApp relationship manager for Local Growth Engine (Kanpur).
Rewrite the GIVEN fallback bubbles into warm, natural Hinglish — SAME meaning, same number of
bubbles, each <=25 words, light emoji. Never add new promises, numbers, or links. If the turn
contains a question, keep EXACTLY that one question. Never use the word 'scheme' or 'offer'.
Output only the bubbles separated by a blank line."""


def phrase_with_llm(turn, lead, llm_call):
    """llm_call(system, user) -> str or raises. Returns bubbles list."""
    user = json.dumps({
        "lead": {"business": lead.get("business"), "niche": lead.get("niche")},
        "intent": turn["kind"], "must_ask": DQS.get(turn.get("ask_dq")),
        "fallback_bubbles": turn["fallback"] or [],
        "last_customer_msg": turn.get("echo", ""),
    }, ensure_ascii=False)
    txt = llm_call(PHRASE_SYS, user)
    bubbles = [b.strip() for b in re.split(r"\n\s*\n", txt) if b.strip()]
    return bubbles[:3] if bubbles else None


# for import ergonomics
turn = None  # placeholder to avoid linter complaint about use-before-def in docstring example