import re

from config import MAX_HISTORY_TURNS, TOP_K
from rag.client import chat, chat_stream
from rag.retrieve import format_context, retrieve

RAG_SYSTEM = (
    "You are a helpful assistant for company internal policies. "
    "Use the conversation so far for context, especially follow-ups like 'elaborate more' or 'what about that'. "
    "Answer using the passages below. Ground every claim in those passages. "
    "If a passage includes a Form link or Links with URLs, include the relevant URL in your answer. "
    "If the passages do not cover the question, say clearly that it is not in your documents."
)

CHAT_SYSTEM = (
    "You are a friendly company policy assistant. "
    "Reply naturally to greetings and casual messages. "
    "Briefly explain that you can answer questions about the user's policy documents. "
    "Do not invent policy facts."
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
                f"PASSAGES:\n{context}\n\n"
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
