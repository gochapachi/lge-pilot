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

def next_turn(lead, history):
    """history: oldest→newest [{dir:'in'|'out', text:str}]. Returns dict:
    {bubbles, stage, tags, notes, next_action_at_days, kind, meta}"""
    stage = lead.get("stage") or "contacted"
    tags = list(lead.get("tags") or [])
    answered = answered_dqs(tags)
    last_in = next((h for h in reversed(history) if h["dir"] == "in"), None)
    text = (last_in or {}).get("text", "")
    low = text.lower()
    business = (lead.get("business") or lead.get("name") or "aapka business").split()[0]
    niche = lead.get("niche") or "default"

    # 0) opt-out anywhere → ack + mute (never pitch)
    if is_opt_out(text):
        return {"bubbles": ["theek hai ji, aage koi message nahi aayega 🙏 sab theek — shubhkamnayein!"],
                "stage": "closed_lost", "tags": tags, "kind": "optout_ack",
                "next_action_at_days": None, "meta": {"optout": True}}

    # 1) objections override flow
    obj = detect_objection(text)
    answered_all = all(d in answered for d in (1, 2, 3, 4))

    if obj and stage in ("probing", "demo_sent", "negotiating", "replied", "contacted"):
        turn = objection_turn(obj, business, lead, answered)
        if turn:
            return turn

    # 2) discovery loop (one question per turn)
    if not answered_all:
        nxt = next((d for d in DQ_ORDER if d not in answered), None)
        return {"bubbles": None,  # phrased by LLM: warm mirror + DQS[nxt]
                "fallback": [mirror(text), DQS[nxt]],
                "stage": "probing" if stage in ("contacted", "replied") else stage,
                "tags": tags, "kind": "discovery", "ask_dq": nxt, "echo": text[:160],
                "next_action_at_days": 1}

    # 3) discovery done → tailored pitch → demo ask
    if stage in ("contacted", "replied", "probing"):
        pain = tag_kv(tags, "pain") or "Google pe reviews/replies ka gap"
        return {"bubbles": None,
                "fallback": [
                    f"dekh liya aapka setup {business} ka 🙏 — jo aapne bataya ({pain}), wahi sabse pehle fix hota hai",
                    "main aapke liye ek chhota demo bana ke bhejta hoon — blank template abhi, final aapke naam pe banega",
                    f"ye raha demo 👇 {DEMO_VIDEO_NOTE}\n{BLANK_DEMO.get(lead.get('niche'), BLANK_DEMO['default'])}"],
                "stage": "demo_sent", "tags": set_tag(tags, "pain", pain), "kind": "pitch_demo",
                "next_action_at_days": 1}

    # 4) demo sent → reaction/next step
    if stage == "demo_sent":
        return {"bubbles": None,
                "fallback": ["dekha demo? kaisa laga — kaafi simple lagta hai ya kuch aur bhi chahiye?",
                             "jo pasand aaya wo hi aapke business ke naam pe har hafte automatic chalega"],
                "stage": "demo_sent", "tags": tags, "kind": "demo_follow",
                "next_action_at_days": 1}

    # 5) negotiating → close ladder (tier choice → link confirmation)
    if stage == "negotiating":
        return {"bubbles": None,
                "fallback": ["to pakka karein? trial month ₹15,000 (sab setup included) — 'haan' likhiye, link isi chat pe aa jayega",
                             "ya phir 15 din ka dekh lena, pasand na aaye to seedha bolt dena 🙏"],
                "stage": "negotiating", "tags": tags, "kind": "close",
                "next_action_at_days": 1}

    # 6) won → onboarding
    if stage == "closed_won":
        return {"bubbles": ["badhai ho {b} family me swagat 🎉 kal se setup shuru — day 1 me sab live, review ka pehla AI reply aapke dashboard me dikhega".format(b=business)],
                "stage": "closed_won", "tags": tags, "kind": "onboard",
                "next_action_at_days": 1}

    # fallback: keep thread alive politely
    return {"bubbles": None,
            "fallback": ["ji boliye, main hoon 🙂"],
            "stage": stage, "tags": tags, "kind": "clarify", "next_action_at_days": 1}


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