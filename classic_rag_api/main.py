from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "documents")
LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localai:8080/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")  # or your local model name

app = FastAPI()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[Message]


class ChatResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str = "stop"


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    choices: list[ChatResponseChoice]


async def embed_text(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{LLM_API_BASE}/embeddings",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={"model": EMBEDDING_MODEL, "input": text},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        return data["data"][0]["embedding"]


async def qdrant_search(embedding: list[float], top_k: int = 5) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/search",
            json={
                "vector": embedding,
                "limit": top_k,
                "with_payload": True,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json().get("result", [])


async def build_context_from_results(results: list[dict]) -> str:
    chunks = []
    for res in results:
        payload = res.get("payload", {})
        text = payload.get("text") or payload.get("content") or ""
        source = payload.get("source") or ""
        if text:
            chunks.append(f"Source: {source}\n{text}")
    return "\n\n---\n\n".join(chunks)


async def call_llm_with_context(user_message: str, context: str) -> str:
    system_prompt = (
        "You are a helpful assistant using the provided context. "
        "If the context is insufficient, say so explicitly."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"Context:\n{context}"},
        {"role": "user", "content": user_message},
    ]
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{LLM_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={"model": CHAT_MODEL, "messages": messages},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]


@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(body: ChatRequest):
    user_msg = next((m.content for m in body.messages if m.role == "user"), "")
    if not user_msg:
        return ChatResponse(
            id="classic-rag-empty",
            choices=[ChatResponseChoice(index=0, message=Message(role="assistant", content="No user message provided."))],
        )

    embedding = await embed_text(user_msg)
    results = await qdrant_search(embedding)
    context = await build_context_from_results(results)
    answer = await call_llm_with_context(user_msg, context)

    return ChatResponse(
        id="classic-rag-1",
        choices=[
            ChatResponseChoice(
                index=0,
                message=Message(role="assistant", content=answer),
            )
        ],
    )
