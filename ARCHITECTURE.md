# ai-stack — Architecture Documentation
Comprehensive architecture reference for the self‑hosted AI platform deployed on Unraid using Docker Compose.

This document defines:
- Network topology
- Service roles and responsibilities
- Data flow between components
- Storage layout
- RAG architecture (Classic + GraphRAG)
- Supabase subsystem architecture
- Observability pipeline
- Slot‑based addressing model

# 1. NETWORK MODEL
## Networks
The stack uses two Unraid‑managed networks:

### **frontend**
- Driver: macvlan  
- Subnet: `10.0.0.0/24`  
- Purpose: GUI‑exposed services  
- Static IPs assigned via `.env`  
- Used only by services requiring browser access  

### **backend**
- Driver: ipvlan  
- Subnet: `10.0.83.0/24`  
- Purpose: internal service‑to‑service communication  
- Default network for all services  
- No LAN exposure  

### Network Philosophy
- **Backend is default** for security and simplicity  
- **Frontend is opt‑in** for GUI services only  
- All IPs and MACs are env‑parameterized  
- Slot number is encoded in the IP/MAC value only  

# 2. SLOT‑BASED ADDRESSING MODEL
Each GUI‑exposed service receives a static IP based on its assigned slot:

| Service            | Slot | IP            | MAC Suffix |
|-------------------|------|---------------|------------|
| OpenWebUI         | 73   | 10.0.0.73     | :73        |
| LM Studio         | 74   | 10.0.0.74     | :74        |
| Flowise           | 75   | 10.0.0.75     | :75        |
| n8n               | 76   | 10.0.0.76     | :76        |
| Langfuse          | 77   | 10.0.0.77     | :77        |
| Neo4j             | 78   | 10.0.0.78     | :78        |
| Supabase Studio   | 80   | 10.0.0.80     | :80        |

This ensures:
- Predictable addressing  
- Easy cross‑reference with your Excel workbook  
- Zero ambiguity in `.env`  

# 3. SERVICE OVERVIEW
## 3.1 Core UI Layer
### **OpenWebUI**
- Primary chat interface  
- Connects to LM Studio, LocalAI, Classic RAG API, GraphRAG API  
- Stores user data under `/app/backend/data`  

### **LM Studio**
- High‑performance local LLM runtime  
- Exposes OpenAI‑compatible API  
- Primary inference backend  

### **LocalAI**
- Secondary inference backend  
- Useful for fallback or model diversity  


## 3.2 Workflow Layer
### **Flowise**
- Visual LLM workflow builder  
- Integrates with RAG APIs, LM Studio, Qdrant, Neo4j  

### **n8n**
- General automation engine  
- Handles ingestion, scheduled tasks, API integrations  


## 3.3 Observability Layer
### **Langfuse**
- Centralized tracing for all LLM calls  
- Receives telemetry from:
  - Classic RAG API  
  - GraphRAG API  
  - Flowise  
  - n8n  
  - OpenWebUI (optional)  


## 3.4 Database Layer
### **Qdrant**
- Vector database  
- Used by Classic RAG API  

### **Neo4j**
- Graph database  
- Used by GraphRAG API  


## 3.5 Supabase Subsystem
Supabase is deployed as a coordinated set of services:

- **Postgres** — primary DB  
- **Kong** — API gateway  
- **Auth (GoTrue)** — authentication  
- **REST (PostgREST)** — auto‑generated REST API  
- **Realtime** — WebSocket change feeds  
- **Storage** — object storage  
- **Studio** — GUI (frontend‑exposed)  

All Supabase services run on **backend**, except Studio which also joins **frontend**.


## 3.6 RAG APIs
### **Classic RAG API**
- Vector‑based retrieval  
- Uses Qdrant  
- Uses LM Studio for inference  
- Sends telemetry to Langfuse  

### **GraphRAG API**
- Graph‑based retrieval  
- Uses Neo4j  
- Uses LM Studio for inference  
- Sends telemetry to Langfuse  

# 4. DATA FLOW ARCHITECTURE
## 4.1 Classic RAG Pipeline
Document → n8n / Flowise → Classic RAG API → Qdrant → LM Studio → OpenWebUI

### Steps:
1. Document ingestion (n8n or Flowise)  
2. Chunking + embedding (Classic RAG API)  
3. Vector storage (Qdrant)  
4. Query → vector search → top‑k results  
5. Context passed to LM Studio  
6. Response returned to OpenWebUI  


## 4.2 GraphRAG Pipeline
Document → n8n / Flowise → GraphRAG API → Neo4j → LM Studio → OpenWebUI


### Steps:
1. Document ingestion  
2. Entity + relationship extraction  
3. Graph construction in Neo4j  
4. Cypher‑based retrieval  
5. Context passed to LM Studio  
6. Response returned to OpenWebUI  


## 4.3 Observability Flow
Classic RAG API → Langfuse
GraphRAG API → Langfuse
Flowise → Langfuse
n8n → Langfuse


Langfuse stores:
- Traces  
- Spans  
- Latency metrics  
- Evaluation metadata  

# 5. STORAGE MODEL
All storage paths are env‑parameterized under:
/mnt/user/appdata/ai-stack


### Subsystem Paths
| Subsystem | Path |
|----------|------|
| OpenWebUI | `/openwebui` |
| LM Studio | `/lmstudio` |
| LocalAI | `/localai/models` |
| Flowise | `/flowise` |
| n8n | `/n8n` |
| Langfuse | `/langfuse` |
| Qdrant | `/qdrant` |
| Neo4j | `/neo4j/data`, `/neo4j/logs` |
| Supabase | `/supabase/*` |
| Classic RAG | `/classic-rag` |
| GraphRAG | `/graphrag` |

# 6. DEPLOYMENT MODEL
## Deployment Steps
1. Create `.env` from `.env.example`  
2. Ensure `frontend` and `backend` networks exist in Unraid  
3. Deploy via Portainer or CLI  
4. Validate healthchecks (Postgres, Langfuse, RAG APIs)  
5. Access GUIs via static IPs  

## GUI Entry Points
| Service | URL |
|---------|-----|
| OpenWebUI | `http://10.0.0.73:${AI_STACK_OPENWEBUI_PORT}` |
| LM Studio | `http://10.0.0.74:${AI_STACK_LMSTUDIO_PORT}` |
| Flowise | `http://10.0.0.75:${AI_STACK_FLOWISE_PORT}` |
| n8n | `http://10.0.0.76:${AI_STACK_N8N_PORT}` |
| Langfuse | `http://10.0.0.77:${AI_STACK_LANGFUSE_PORT}` |
| Neo4j Browser | `http://10.0.0.78:${AI_STACK_NEO4J_HTTP_PORT}` |
| Supabase Studio | `http://10.0.0.80:${AI_STACK_SUPABASE_STUDIO_PORT}` |

# 7. SECURITY MODEL
- Backend network is isolated from LAN  
- Only GUI services join frontend  
- All credentials stored in `.env`  
- JWT secrets and service role keys required for Supabase  
- Langfuse secrets required for telemetry  
- Neo4j password required for Bolt access  

# 8. FUTURE EXTENSIONS
- GPU‑accelerated LM Studio  
- Additional RAG pipelines  
- Automated ingestion via watch folders  
- Supabase row‑level security policies  
- Multi‑model routing in OpenWebUI  
- Automated backups for Postgres, Neo4j, Qdrant  

# END OF DOCUMENT
