from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "graph_nodes")
LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localai:8080/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

app = FastAPI()
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


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


async def qdrant_search_nodes(embedding: list[float], top_k: int = 10) -> list[dict]:
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


def fetch_subgraph(node_ids: list[str]) -> list[dict]:
    if not node_ids:
        return []
    cypher = """
    MATCH (n)-[r]-(m)
    WHERE n.id IN $ids
    RETURN n, r, m
    LIMIT 200
    """
    with driver.session() as session:
        result = session.run(cypher, ids=node_ids)
        triples = []
        for record in result:
            n = record["n"]
            r = record["r"]
            m = record["m"]
            triples.append(
                {
                    "source": n.get("id"),
                    "source_label": list(n.labels)[0] if n.labels else "",
                    "rel_type": r.type,
                    "target": m.get("id"),
                    "target_label": list(m.labels)[0] if m.labels else "",
                }
            )
        return triples


def format_graph_context(triples: list[dict]) -> str:
    if not triples:
        return "No relevant graph context found."
    lines = []
    for t in triples:
        lines.append(
            f"{t['source_label']}({t['source']}) -[{t['rel_type']}]-> {t['target_label']}({t['target']})"
        )
    return "Graph relationships:\n" + "\n".join(lines)


async def call_llm_with_graph(user_message: str, graph_context: str) -> str:
    system_prompt = (
        "You are a reasoning assistant that uses the provided knowledge graph context "
        "to answer multi-hop, relationship-heavy questions. If the graph context is "
        "insufficient, say so explicitly."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"Graph context:\n{graph_context}"},
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
            id="graphrag-empty",
            choices=[ChatResponseChoice(index=0, message=Message(role="assistant", content="No user message provided."))],
        )

    embedding = await embed_text(user_msg)
    node_results = await qdrant_search_nodes(embedding)
    node_ids = [res["payload"].get("node_id") for res in node_results if res.get("payload")]
    node_ids = [nid for nid in node_ids if nid]

    triples = fetch_subgraph(node_ids)
    graph_context = format_graph_context(triples)
    answer = await call_llm_with_graph(user_msg, graph_context)

    return ChatResponse(
        id="graphrag-1",
        choices=[
            ChatResponseChoice(
                index=0,
                message=Message(role="assistant", content=answer),
            )
        ],
    )
