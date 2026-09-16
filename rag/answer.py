import re

from config import MAX_HISTORY_TURNS, TOP_K
from rag.client import chat, chat_stream
from rag.retrieve import format_context, retrieve

RAG_SYSTEM = (
    "You are a warm, friendly company policy assistant — like a helpful HR or IT colleague who knows the policies well. "
    "Use the conversation so far for context, especially follow-ups like 'elaborate more' or 'what about that'. "
    "Answer using the policy details provided below. Ground every claim in that info — never invent policy details. "
    "Write in plain, conversational language, as if you're chatting with a coworker. "
    "Start with a brief friendly lead-in when it fits (e.g. 'Sure!', 'Good question!', 'Happy to help!'). "
    "NEVER use meta or document-referencing language in your reply. Banned words/phrases include: "
    "'passages', 'provided passages', 'the documents', 'according to the policy documents', "
    "'I found in the documents', 'the text states', 'it is not specified in'. "
    "Instead speak directly: 'The hardware policy covers laptops for upgrades and replacements' "
    "not 'The passages mention laptops'. "
    "When something isn't covered, say it naturally: "
    "'I don't have a full list of devices in the policy, but I can tell you...' or "
    "'That's not spelled out in the hardware policy — what I do know is...'. "
    "If the user asks multiple questions, answer each one clearly (short bullets or numbered points). "
    "If policy info includes a form link or URL, include it in your answer. "
    "End with a brief helpful closing only on longer answers — skip it on short one-liners. "
    "Keep answers concise but complete."
)

CHAT_SYSTEM = (
    "You are a warm, friendly company policy assistant — like a helpful colleague. "
    "Reply naturally to greetings, thanks, and casual messages. "
    "Be brief, upbeat, and human. Use the user's role when helpful. "
    "Explain that you can answer questions about their policy documents (leave, loans, laptops, trips, etc.). "
    "Do not invent policy facts. "
    "End with a gentle invitation to ask a question when it feels natural."
)

SMALL_TALK = re.compile(
    r"^(?:hi|hello|hey|hiya|yo|sup|thanks?|thank you|ok(?:ay)?|cool|great|nice|"
    r"bye|goodbye|good (?:morning|afternoon|evening)|how are you(?: doing)?|"
    r"what(?:'s| is) up|help)[\s!.?,]*$",
    re.IGNORECASE,
)

FOLLOWUP_HINTS = re.compile(
    r"\b(elaborate|more details?|tell me more|explain (?:more|further|that|it|this)|"
    r"what about|how about|and that|same (?:one|thing)|go on|continue|"
    r"can you expand|please expand|more on that|more on this)\b",
    re.IGNORECASE,
)

POLICY_HINTS = re.compile(
    r"\b(policy|policies|leave|loan|medical|laptop|hardware|trip|reimburs|"
    r"eligible|benefit|form|submit|apply|request|deadline|days?|amount|salary)\b",
    re.IGNORECASE,
)

REWRITE_SYSTEM = (
    "Rewrite the user's latest message into one standalone search query for company policy documents. "
    "Use the conversation when the message is a follow-up (e.g. 'elaborate more', 'what about that'). "
    "Return only the search query, nothing else."
)


def _api_history(history: list[dict]) -> list[dict]:
    trimmed = history[-MAX_HISTORY_TURNS * 2 :]
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in trimmed
        if msg.get("role") in ("user", "assistant") and msg.get("content")
    ]


def is_small_talk(question: str) -> bool:
    text = question.strip()
    if not text:
        return True
    if POLICY_HINTS.search(text):
        return False
    if "?" in text and len(text.split()) > 2:
        return False
    return bool(SMALL_TALK.match(text))


def _needs_rewrite(question: str, history: list[dict]) -> bool:
    if not history:
        return False
    if FOLLOWUP_HINTS.search(question):
        return True
    return len(question.split()) <= 8


def _rewrite_query(question: str, history: list[dict]) -> str:
    rewritten = chat(
        [
            {"role": "system", "content": REWRITE_SYSTEM},
            *_api_history(history),
            {"role": "user", "content": question},
        ],
        max_tokens=80,
    )
    return rewritten.strip() or question


def _answer_messages(role: str, question: str, history: list[dict], hits: list[dict]) -> list[dict]:
    context = format_context(hits)
    return [
        {"role": "system", "content": RAG_SYSTEM},
        *_api_history(history),
        {
            "role": "user",
            "content": (
                f"User role: {role}\n\n"
                f"Policy details:\n{context}\n\n"
                f"Question: {question}"
            ),
        },
    ]


def _small_talk_messages(question: str, history: list[dict], role: str) -> list[dict]:
    return [
        {"role": "system", "content": f"{CHAT_SYSTEM}\nUser role: {role}"},
        *_api_history(history),
        {"role": "user", "content": question},
    ]


def answer_question(role: str, question: str, history: list[dict] | None = None) -> dict:
    prepared = prepare_answer_stream(role, question, history)
    answer = "".join(prepared["stream"])
    return {
        "answer": answer,
        "sources": prepared["sources"],
        "hits": prepared["hits"],
        "used_rag": prepared["used_rag"],
    }


def prepare_answer_stream(role: str, question: str, history: list[dict] | None = None) -> dict:
    """Retrieve context synchronously, then stream the final LLM reply."""
    history = history or []

    if is_small_talk(question):
        return {
            "sources": [],
            "hits": [],
            "used_rag": False,
            "stream": chat_stream(_small_talk_messages(question, history, role)),
        }

    search_query = _rewrite_query(question, history) if _needs_rewrite(question, history) else question
    top_k = TOP_K + 2 if _needs_rewrite(question, history) else TOP_K
    hits = retrieve(role, search_query, top_k=top_k)
    sources = sorted({h["label"] for h in hits})
    return {
        "sources": sources,
        "hits": hits,
        "used_rag": True,
        "stream": chat_stream(_answer_messages(role, question, history, hits)),
    }
