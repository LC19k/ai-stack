# ai-stack
A fully self‑hosted AI platform running on Unraid, providing:

- Chat UI (OpenWebUI)
- Local model runtimes (LM Studio, LocalAI)
- Workflow automation (Flowise, n8n)
- Observability (Langfuse)
- Databases (Qdrant, Neo4j)
- Supabase (Postgres, Auth, REST, Realtime, Storage, Studio)
- Custom RAG APIs (Classic RAG + GraphRAG)

Everything is deployed via Docker Compose with full environment‑variable control, static IP assignment, and a clean separation between frontend and backend networks.

---

## Features

### 🔹 Core UI
- **OpenWebUI** — primary chat interface  
- **LM Studio** — high‑performance local LLM runtime  
- **LocalAI** — secondary inference backend  

### 🔹 Workflow Automation
- **Flowise** — visual LLM pipeline builder  
- **n8n** — general automation engine  

### 🔹 Observability
- **Langfuse** — traces, spans, metrics for all LLM calls  

### 🔹 Databases
- **Qdrant** — vector database for Classic RAG  
- **Neo4j** — graph database for GraphRAG  

### 🔹 Supabase
- Postgres  
- Auth (GoTrue)  
- REST (PostgREST)  
- Realtime  
- Storage  
- Studio (GUI)  

### 🔹 RAG APIs
- **Classic RAG API** — vector‑based retrieval  
- **GraphRAG API** — graph‑based retrieval  

---

## Network Architecture

The stack uses two Unraid‑managed networks:

### `frontend`
- macvlan  
- GUI‑exposed services  
- Static IPs (slot‑based)  

### `backend`
- ipvlan  
- Internal service‑to‑service traffic  
- Default network for all services  

Only GUI services join `frontend`.  
Everything else stays isolated on `backend`.

---

## Slot‑Based Addressing

Each GUI service receives a static IP based on its slot:

| Service            | Slot | IP        |
|-------------------|------|-----------|
| OpenWebUI         | 73   | 10.0.0.73 |
| LM Studio         | 74   | 10.0.0.74 |
| Flowise           | 75   | 10.0.0.75 |
| n8n               | 76   | 10.0.0.76 |
| Langfuse          | 77   | 10.0.0.77 |
| Neo4j             | 78   | 10.0.0.78 |
| Supabase Studio   | 80   | 10.0.0.80 |

MAC addresses follow the same pattern.

---

## Repository Structure
ai-stack/

├── docker-compose.yml

├── .env.example

├── .env                # (not committed)

├── ARCHITECTURE.md

└── README.md


All persistent data lives under:
/mnt/user/appdata/ai-stack


---

## Deployment

### 1. Copy `.env.example` → `.env`
Fill in:
- Supabase secrets  
- Langfuse keys  
- Neo4j password  
- JWT secrets  

### 2. Ensure networks exist in Unraid
- `frontend` (macvlan)  
- `backend` (ipvlan)  

### 3. Deploy the stack
docker compose up -d


### 4. Validate health
- Postgres ready  
- Langfuse reachable  
- RAG APIs responding  
- OpenWebUI loads  

---

## Accessing Services

| Service | URL |
|---------|-----|
| OpenWebUI | `http://10.0.0.73:3001` |
| LM Studio | `http://10.0.0.74:1234` |
| Flowise | `http://10.0.0.75:3002` |
| n8n | `http://10.0.0.76:3003` |
| Langfuse | `http://10.0.0.77:3004` |
| Neo4j Browser | `http://10.0.0.78:7474` |
| Supabase Studio | `http://10.0.0.80:3005` |

---

## RAG Architecture

### Classic RAG
- Chunking + embeddings  
- Vector search via Qdrant  
- LM Studio for inference  

### GraphRAG
- Entity + relationship extraction  
- Graph storage in Neo4j  
- Cypher‑based retrieval  
- LM Studio for inference  

Both send telemetry to Langfuse.

---

## Backups

Recommended:
- Postgres: `pg_dump`  
- Neo4j: `neo4j-admin dump`  
- Qdrant: filesystem snapshot  
- Supabase Storage: filesystem snapshot  

A Makefile can automate these (optional).

---

## Troubleshooting

### Containers not resolving each other
Ensure:
- `backend` network exists  
- Containers are attached to it  

### GUI not reachable
Check:
- Static IP not conflicting  
- MAC address unique  
- macvlan parent interface correct  

### Supabase errors
Verify:
- JWT secret  
- Service role key  
- Postgres password  
- Kong URL  

---

## License
This repository is for personal homelab use.
