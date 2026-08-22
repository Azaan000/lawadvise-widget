import asyncio
import json
import os
import re
import sys
from typing import AsyncGenerator, Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WIDGET_SHARED_SECRET = os.getenv("WIDGET_SHARED_SECRET")  # optional but recommended
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")  # used in the OpenRouter HTTP-Referer header

# Fail fast at startup instead of silently sending "Authorization: Bearer None"
# on every request and only finding out via a confusing 502 later.
if not OPENROUTER_API_KEY:
    sys.exit(
        "FATAL: OPENROUTER_API_KEY is not set. Add it to your .env file "
        "(or environment) before starting the server."
    )

if not WIDGET_SHARED_SECRET:
    print(
        "WARNING: WIDGET_SHARED_SECRET is not set — /chat is unauthenticated and "
        "anyone who finds the endpoint can use it. Set WIDGET_SHARED_SECRET in your "
        ".env and widgetKey in widget.html to lock it down.",
        file=sys.stderr,
    )

# Comma-separated list of domains allowed to call this API, e.g.
# "https://lawadvise.com,https://www.lawadvise.com". Falls back to "*" (any
# origin) if unset, so local dev/testing still works — but that also means
# any site can call /chat and burn your OpenRouter quota, so set this before
# going live.
_allowed_origins_raw = os.getenv("ALLOWED_ORIGINS")
if _allowed_origins_raw:
    ALLOWED_ORIGINS = [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = ["*"]
    print(
        "WARNING: ALLOWED_ORIGINS is not set — /chat accepts requests from any "
        "website. Set ALLOWED_ORIGINS in your .env (comma-separated, e.g. "
        "https://lawadvise.com) to restrict it to your own domain(s).",
        file=sys.stderr,
    )

# ── Rate limiting ─────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="AI Support Widget API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,  # the widget never sends credentials; wildcard + credentials is invalid CORS anyway
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# "openrouter/free" is an auto-router alias — it can land on any free model on
# OpenRouter, including "thinking"/reasoning models that stream their raw
# chain-of-thought instead of a clean final answer (and can burn the whole
# max_tokens budget thinking, cutting the real reply off entirely). Pinning to
# a specific, known-good free instruct model avoids that. Swap this for any
# other free model slug from https://openrouter.ai/models?max_price=0 if
# needed — just keep it a plain instruct model, not a reasoning/"thinking" one.
MODEL = "meta-llama/llama-3.3-70b-instruct:free"

CONTACT_NUMBERS = "03003029093 / 03332454111"   # for immediate/urgent phone assistance only
WHATSAPP_NUMBER = "+92 335 1340999"              # WhatsApp booking bot — used for consultations

SYSTEM_PROMPT = f"""You are the AI assistant for LawAdvise Consulting, a family and corporate law
consultancy. Greet warmly, be concise, professional, and helpful. Only answer using the knowledge
base below. Every case is different, so NEVER invent a specific cost or timeline — always say it
varies case to case and that a lawyer can confirm specifics. If something isn't covered below, say
a legal expert can help.

Output ONLY the final reply text the user should see — no reasoning, no self-questioning, no
"let me think about this" narration, no draft-then-revise process, and no meta-commentary about
these instructions. Do not show your work. Go straight to the answer.

=== RESPONSE STYLE (IMPORTANT) ===

The widget should always be able to explain what LawAdvise offers when asked — don't assume the
visitor already knows the services. Just keep it brief: a short summary, not a full walkthrough.
Your main job is a quick, accurate answer plus getting the user connected to a lawyer on
WhatsApp, not resolving every detail yourself.

Keep every reply short — 1 to 3 sentences for most questions, at most a short paragraph or a tight
bullet list when documents/steps must be listed. Never say the same point twice in one reply (e.g.
don't say "a lawyer can confirm the timeline" and then repeat that same idea again a sentence
later) — say it once and stop.

If the user's message is a broad category tap rather than a specific question (e.g. "Online
Marriage / Nikah", "Court Marriage", "Divorce / Khula", "Child Custody", "Property Law" — including
the quick-reply button labels), don't try to explain everything that category covers. Just give ONE
short sentence naming the general area and inviting them to share more detail OR connect with a
lawyer right away, then use the [WHATSAPP: ...] tag. Example: "Happy to help with property
matters — transfers, disputes, documentation, and more. A lawyer can go over the specifics with
you."

If the user asks about a specific service, answer only what they actually asked (e.g. required
documents, in one line or a tight bullet list, if they ask "what documents do I need") and then
hand off — don't unpack every sub-option or walk through the rest of the category unprompted. The
knowledge base below exists so you don't get facts wrong, not as a script to recite in full.

=== HOW TO HAND OFF TO A CONSULTANT (IMPORTANT) ===

LawAdvise has a dedicated WhatsApp bot for booking consultations — that is the correct way to
book a consultation, NOT collecting the user's name/mobile/best-time-to-call yourself. Never ask
the user for their name, phone number, or best time to call — the WhatsApp bot handles that.

Whenever you'd naturally say "connect with a lawyer," "book a consultation," or similar, do
BOTH of these:
1. Say it conversationally in one short sentence (e.g. "A lawyer can confirm the exact process
   and next steps for this.")
2. On its own new line at the very end of your reply, output exactly one tag in this format:
   [WHATSAPP: <short topic, e.g. "Court Marriage Consultation">]
   The topic should summarize what the user was asking about, in a few words, in Title Case.
   Do not explain the tag or mention WhatsApp explicitly in your sentence — the interface turns
   the tag into a "Continue on WhatsApp" button automatically.

Include the [WHATSAPP: ...] tag on essentially every reply that touches a specific service —
connecting people to that number is this widget's main purpose, not a fallback for when you can't
answer. Skip it only for pure greetings/small talk, or when you already tagged the exact same
topic in your immediately preceding reply and the user hasn't indicated they're ready to move
forward. Include at most one tag per reply.

Reserve the direct phone numbers ({CONTACT_NUMBERS}) ONLY for matters the user describes as urgent
(e.g. a court deadline, an urgent notice, or explicitly asking to speak to someone right now) —
give the phone number directly in those cases instead of, or in addition to, the WhatsApp tag.

=== KNOWLEDGE BASE ===

COMPANY: LawAdvise Consulting
URGENT PHONE ASSISTANCE (time-sensitive matters only): {CONTACT_NUMBERS}
CONSULTATION BOOKING: via WhatsApp (see handoff instructions above)

--- MAIN SERVICE CATEGORIES ---
1. Online Marriage / Online Nikah
2. Court Marriage
3. Divorce / Khula
4. Child Custody / Guardianship
5. Maintenance (Nafaqa) / Dowry
6. Property Law
7. Inheritance
8. Corporate Law
9. Legal Documentation
10. Talk to a Lawyer / Book Consultation

=== 1. ONLINE MARRIAGE / ONLINE NIKAH ===

Procedure: At least one of the parties must be residing outside Pakistan. The legal process and
documentation remain identical to a conventional Nikah — the only difference is that one party
participates remotely through a secure online platform.

Required documents (from both parties): valid CNIC/NICOP or passport, recent passport-size
photographs, 2 witnesses (CNIC of both witnesses).

Time required: varies case to case — a lawyer can give a more accurate estimate.

=== 2. COURT MARRIAGE ===

Procedure: Both parties must be present in person to fulfill the legal requirements. All legal
requirements and formalities remain the same as a conventional Nikah.

Required documents (from both parties): valid CNIC/NICOP or passport, recent passport-size
photographs, 2 witnesses (CNIC of both witnesses).

Time required: each case is unique, so the estimated timeline may vary.

=== 3. DIVORCE / KHULA ===

Procedure: every case is different — a lawyer should review the specifics of the situation before
advising on next steps.

Timeline: varies depending on the nature and complexity of the case.

=== 4. CHILD CUSTODY / GUARDIANSHIP ===

This issue cannot be accurately assessed through the chatbot — our legal team will assess it
directly. Timeline: each case is unique, so the estimated timeline may vary.

=== 5. MAINTENANCE (NAFAQA) / DOWRY ===

This issue cannot be accurately assessed through the chatbot — our legal team will assess it
directly. Timeline: each case is unique, so the estimated timeline may vary.

=== 6. PROPERTY LAW ===

This requires a detailed legal consultation — connect the user with one of our lawyers.
Timeline: depends on the legal process and the circumstances of the case.

=== 7. INHERITANCE ===

This requires a detailed legal consultation — connect the user with one of our lawyers.
Timeline: depends on the legal process and the circumstances of the case.

=== 8. CORPORATE LAW ===

This requires a detailed legal consultation — connect the user with one of our lawyers.
Timeline: depends on the legal process and the circumstances of the case.

=== 9. LEGAL DOCUMENTATION ===

This requires a detailed legal consultation — connect the user with one of our lawyers.
Timeline: depends on the legal process and the circumstances of the case.

=== BOOKING A CONSULTATION ===

When the user has shown genuine interest in a service (not on generic greetings), offer to
connect them with a lawyer and use the [WHATSAPP: ...] tag as described above — do NOT ask
for their name, mobile number, or best time to call yourself; the WhatsApp bot collects that.

=== END KNOWLEDGE BASE ===

Always end a response that involves case-specific timelines or legal specifics by either
(a) appending a [WHATSAPP: ...] tag to offer a consultation, per the handoff instructions
above, or (b) for genuinely urgent matters only, giving the direct phone number
({CONTACT_NUMBERS})."""


# Some OpenRouter free-tier providers route this model behind a Llama-Guard-style
# safety classifier. Occasionally the classifier's own output ("User Safety: safe",
# "Response Safety: safe", etc.) leaks into `content` instead of a real reply. This
# has nothing to do with our prompt — it happens upstream — so we detect it and
# retry, then fall back to a clean message rather than showing it to the user.
_GUARD_LEAK_RE = re.compile(
    r"^\s*(user safety|response safety|safety categories)\s*:",
    re.IGNORECASE,
)


def _looks_like_guard_leak(text: str) -> bool:
    return bool(_GUARD_LEAK_RE.match(text.strip())) or (
        "user safety" in text.lower() and "response safety" in text.lower() and len(text) < 200
    )


# Some free-tier models occasionally stream their raw internal reasoning
# ("Wait, let me re-read the instruction... Let me refine the sentence...")
# instead of — or before — a clean final answer, especially if they run out
# of max_tokens mid-thought. This is heuristic, not exhaustive: it looks for
# the self-talk phrasing and question-then-answer scaffolding ("X? Yes. -")
# that this failure mode reliably produces, so real replies won't false-match.
_REASONING_LEAK_RE = re.compile(
    r"\b(wait,? let me|let me (re-?read|refine|reconsider)|wait,? (i|that)|"
    r"hold on,? (let me|i)|actually,? let me reconsider)\b",
    re.IGNORECASE,
)
_REASONING_SCAFFOLD_RE = re.compile(r"\?\s*(Yes|No)\.\s*-", re.IGNORECASE)


def _looks_like_reasoning_leak(text: str) -> bool:
    return bool(_REASONING_LEAK_RE.search(text)) or bool(_REASONING_SCAFFOLD_RE.search(text))


FALLBACK_REPLY = (
    "Sorry, I had trouble putting together a reply just now. Could you try asking "
    "that again, or rephrase it slightly?"
)


# ── Fast-path canned replies ────────────────────────────────────────────────
# The six quick-reply buttons in widget.html cover the large majority of first
# messages. Answering those from a fixed dict — instead of a round-trip to the
# OpenRouter free tier — is instant and 100% consistent, and only falls through
# to the LLM for actual free-text questions. Same pattern as the canned-reply
# layer in the WhatsApp bot webhook.

CANNED_REPLIES: dict[str, tuple[str, str]] = {
    "online marriage nikah": (
        "Online Nikah requires at least one party residing outside Pakistan — the process and "
        "documents are the same as a conventional Nikah, just with one party joining remotely. "
        "A lawyer can confirm the timeline for your case.",
        "Online Marriage / Nikah",
    ),
    "court marriage": (
        "Court Marriage requires both parties to be present in person, with the same legal "
        "requirements as a conventional Nikah. A lawyer can confirm the documents and timeline "
        "for your case.",
        "Court Marriage",
    ),
    "divorce khula": (
        "Every Divorce/Khula case is different. A lawyer can review your situation and advise "
        "on the right process and timeline.",
        "Divorce / Khula",
    ),
    "child custody": (
        "Child custody and guardianship matters need to be reviewed directly by our legal team "
        "to give you accurate guidance.",
        "Child Custody",
    ),
    "property law": (
        "Property matters — transfers, disputes, documentation, and more — need a detailed "
        "legal consultation. A lawyer can go over the specifics with you.",
        "Property Law",
    ),
    "talk to a lawyer": (
        "Sure — a lawyer can go over your situation and next steps directly.",
        "Talk to a Lawyer",
    ),
}


def _normalize(text: str) -> str:
    # Strips the leading emoji on the button labels ("🚀 Start a New Business")
    # along with punctuation/case, so both the button tap and a user retyping
    # the same phrase match the same entry.
    return re.sub(r"[^\w\s]", "", text).strip().lower()


def _match_canned_reply(user_text: str) -> tuple[str, str] | None:
    return CANNED_REPLIES.get(_normalize(user_text))


# Genuinely off-topic messages (not just a business question we lack a canned
# answer for) get an instant, fixed redirect instead of letting the free-tier
# model improvise a reply to something outside the knowledge base.
OFF_TOPIC_FALLBACK = (
    "I'm the LawAdvise assistant, so I can only help with marriage, divorce, custody, "
    "property, inheritance, corporate law, or legal documentation questions. Ask me about "
    "any of those, or tap 'Talk to a Lawyer' to reach a consultant."
)

# Matched as PATTERNS (request shapes), not single keywords — "write me a poem about
# X" and "write me a poem about Y" both match without listing every X/Y. This still
# doesn't understand intent — it's pinned to phrasings we can reliably predict are
# off-topic, so anything ambiguous falls through to the LLM by design rather than
# risk misfiring on a real business question that happens not to use our vocabulary.
_OFF_TOPIC_PATTERNS = [
    # Creative-writing / general-knowledge requests: "write me a <thing>",
    # "tell me a joke/story", "give me a recipe for <thing>"
    re.compile(r"\bwrite (me |us )?(a |an |some )?(poem|song|story|joke|lyrics|essay|code)\b", re.IGNORECASE),
    re.compile(r"\btell me (a |an )?(joke|story|riddle)\b", re.IGNORECASE),
    re.compile(r"\b(recipe|how (do|to) (i |you )?(cook|bake))\b", re.IGNORECASE),
    # Live/general facts unrelated to LawAdvise: weather, sports scores, translation,
    # "who is <public figure>", math homework
    re.compile(r"\bweather (in|today|tomorrow|forecast)\b", re.IGNORECASE),
    re.compile(r"\b(football|cricket|nba|match) (score|scores|result)\b", re.IGNORECASE),
    re.compile(r"\btranslate (this|that|the following)\b", re.IGNORECASE),
    re.compile(r"\bsolve (this|the) (equation|math|problem)\b", re.IGNORECASE),
    re.compile(r"\bwho (is|was) the (president|prime minister|king|ceo of)\b", re.IGNORECASE),
    # Meta questions about the bot itself rather than about LawAdvise's services
    re.compile(r"\bare you (a |an )?(human|robot|real|ai|bot)\b", re.IGNORECASE),
    re.compile(r"\bwho (made|built|created) you\b", re.IGNORECASE),
    re.compile(r"\bwhat('?s| is) your name\b", re.IGNORECASE),
]


_WHATSAPP_TAG_RE = re.compile(r"\[WHATSAPP:\s*(.*?)\]", re.IGNORECASE)


def _extract_whatsapp_tag(text: str) -> tuple[str, str | None]:
    """Split a reply into (display_text, topic). The [WHATSAPP: ...] tag itself
    is never sent to the client as visible text — it's carried separately as an
    SSE "whatsapp" event so the frontend can render the CTA button instead of
    showing the raw tag."""
    match = _WHATSAPP_TAG_RE.search(text)
    if not match:
        return text.strip(), None
    display_text = (text[: match.start()] + text[match.end() :]).strip()
    topic = match.group(1).strip()
    return display_text, topic


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_text(display_text: str, topic: str | None) -> AsyncGenerator[str, None]:
    """Yield a finished reply as SSE chunk events (small pieces, for a progressive
    typing effect on the frontend), then a whatsapp event if there's a topic,
    then done."""
    chunk_size = 24
    for i in range(0, len(display_text), chunk_size):
        yield _sse("chunk", {"text": display_text[i : i + chunk_size]})
        await asyncio.sleep(0.015)
    if topic:
        yield _sse("whatsapp", {"topic": topic})
    yield _sse("done", {})


def _looks_off_topic(text: str) -> bool:
    return any(pattern.search(text) for pattern in _OFF_TOPIC_PATTERNS)


class Message(BaseModel):
    # Only user/assistant may come from the client — otherwise a client could pass
    # role: "system" and try to override SYSTEM_PROMPT.
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    reply: str


def verify_widget_key(request: Request) -> None:
    """Shared-secret check. No-op (open) if WIDGET_SHARED_SECRET isn't configured,
    so the app still runs during local dev — but a warning is printed at startup."""
    if not WIDGET_SHARED_SECRET:
        return
    provided = request.headers.get("X-Widget-Key")
    if provided != WIDGET_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing widget key")


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL}


# Headers that prevent proxies (Railway, Vercel, nginx, etc.) from buffering
# the SSE stream, which would defeat the whole point of progressive typing.
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@app.post("/chat")
@limiter.limit("10/minute")  # per-IP cap — tune to taste
async def chat(request: Request, chat_request: ChatRequest):
    verify_widget_key(request)

    if not chat_request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    last_message = chat_request.messages[-1]
    if last_message.role == "user":
        canned = _match_canned_reply(last_message.content)
        if canned:
            reply_text, topic = canned
            return StreamingResponse(
                _stream_text(reply_text, topic), media_type="text/event-stream", headers=_SSE_HEADERS
            )

        if _looks_off_topic(last_message.content):
            return StreamingResponse(
                _stream_text(OFF_TOPIC_FALLBACK, None), media_type="text/event-stream", headers=_SSE_HEADERS
            )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *[{"role": m.role, "content": m.content} for m in chat_request.messages],
        ],
        "max_tokens": 512,
        "temperature": 0.7,
        # Deprioritize (not exclude) the slowest/lowest-quality free endpoints.
        # If you find via your OpenRouter activity log which provider is leaking
        # safety-classifier text, add it under "ignore" here, e.g.
        # "provider": {"sort": "throughput", "ignore": ["deepinfra"]}
        "provider": {"sort": "throughput"},
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": SITE_URL,
        "X-Title": "Customer Support Widget",
        "Content-Type": "application/json",
    }

    async def call_openrouter(client: httpx.AsyncClient) -> str:
        try:
            response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"OpenRouter error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Could not reach OpenRouter: {e}")

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            # OpenRouter can return 200 with no "choices" (e.g. moderation/error payloads).
            raise HTTPException(
                status_code=502,
                detail="OpenRouter returned an unexpected response format.",
            )

    async def generate() -> AsyncGenerator[str, None]:
        # Everything inside here runs AFTER headers are already sent, so errors
        # can no longer become an HTTP status code — they must become an
        # "error" SSE event instead, which is what the frontend's
        # streamChat() looks for.
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                reply = await call_openrouter(client)

                if _looks_like_guard_leak(reply) or _looks_like_reasoning_leak(reply):
                    # Retry once — this is usually a one-off routing hiccup.
                    reply = await call_openrouter(client)

                if _looks_like_guard_leak(reply) or _looks_like_reasoning_leak(reply):
                    reply = FALLBACK_REPLY

            display_text, topic = _extract_whatsapp_tag(reply)
            # The LLM picks its own free-text topic (e.g. "Legal Notice", "NTN
            # Registration") for the [WHATSAPP: ...] tag, but the WhatsApp bot on
            # the other end only reliably routes on a fixed set of keywords. An
            # arbitrary AI-generated topic can silently fail to match that logic.
            # The six canned quick-reply buttons above (which return earlier, at
            # the `if canned:` branch) keep their own known-good topics untouched
            # — this override only applies to freeform LLM conversation, so every
            # such handoff uses the one keyword the bot is guaranteed to recognize.
            if topic:
                topic = "lawservices"
            async for event in _stream_text(display_text, topic):
                yield event
        except HTTPException as e:
            yield _sse("error", {"detail": e.detail})
        except Exception:
            yield _sse("error", {"detail": "Unexpected server error"})

    return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)