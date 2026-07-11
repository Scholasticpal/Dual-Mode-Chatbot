# Dual-Mode Corporate Intelligence System

An enterprise-grade, asynchronous AI assistant built to seamlessly route user queries between internal corporate data tools (RAG/Text-to-SQL) and general knowledge models. 

### [► View Live Application (Vercel)](https://dual-mode-chatbot.vercel.app/) | [► View Backend API (Render)](https://dual-mode-chatbot.onrender.com/)

---

## Overview

The Dual-Mode Corporate Intelligence System addresses a critical challenge in enterprise AI: preventing Large Language Models from hallucinating or improperly mixing secure corporate data with general world knowledge. 

This platform moves beyond standard chatbot implementations by establishing a deterministic routing architecture:

* **Strict Dual-Mode Routing:** The LangGraph agent distinguishes between corporate policy/order inquiries (which force strict, single-execution tool usage) and general knowledge questions (which bypass tools entirely). If internal data is missing, the agent deterministicly returns "I don't have that information" rather than guessing.
* **Server-Sent Events (SSE) UI Sync:** The backend intercepts and yields `tool_start` metadata chunks over the SSE stream, allowing the Next.js frontend to render dynamic, non-blocking loading states (e.g., "Querying database...") before text tokens arrive.
* **Resilient Infrastructure:** Containerized via Docker with strict dependency pinning and environment-agnostic routing, ensuring immediate, flawless execution on any reviewer's machine.

---

## Tech Stack & Core Services

This project utilizes a modern, dual-environment architecture (Python Backend / TypeScript Frontend), leveraging specialized tools for vector matching and autonomous routing.

| Technology / Service | Role in Project                                             |
| :------------------- | :---------------------------------------------------------- |
| **Supabase**         | PostgreSQL Database, `pgvector` Store, Transaction Pooler   |
| **Groq (Llama-3)**   | Core LLM (`llama-3.1-8b-instant`) for robust, free-tier tool execution          |
| **Google Gemini**    | Vector Embeddings (`embedding-001` with 768-dim vectors)                  |
| **LangGraph**        | Agent State Management & Deterministic Tool Routing         |
| **FastAPI**          | Asynchronous API Backend & SSE Streaming                    |
| **Next.js 16**       | Frontend Web Framework (React)                              |
| **Tailwind CSS**     | Utility-First Styling                                       |
| **Docker Compose**   | Environment Containerization & Network Orchestration        |
| **react-markdown**   | Client-side rendering for generated SQL tables and lists    |

---

## Getting Started (For Reviewers & Developers)

This section contains everything needed to spin up the containerized architecture locally.

### Prerequisites

* **Docker** and **Docker Compose** installed and running.
* **Google Gemini API Key**
* **Supabase Project** (Configured with standard `orders` table and `documents` vector table).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd Dual-Mode-Chatbot
    ```

2.  **Configure Environment Variables:**
    Duplicate the `.env.example` files in both the `backend/` and `frontend/` directories and rename them to `.env`.

    **backend/.env**
    ```env
    GOOGLE_API_KEY="your_gemini_key_here"
    SUPABASE_URL="[https://your-project.supabase.co](https://your-project.supabase.co)"
    SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"
    DATABASE_URL="postgresql://postgres.[ref]:[password]@aws-0-[region][.pooler.supabase.com:6543/postgres](https://.pooler.supabase.com:6543/postgres)"
    ```

    **frontend/.env**
    ```env
    NEXT_PUBLIC_API_URL="http://localhost:8000"
    ```

### Environment Variables Breakdown

| Variable | Target | Meaning | Where to Retrieve |
| :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | Backend | Authenticates the Groq LLM (Llama-3) for agent routing and tool execution. | console.groq.com. |
| `GOOGLE_API_KEY` | Backend | Authenticates the Gemini Embedding model for vector matching. | Google AI Studio. |
| `SUPABASE_URL` | Backend | The REST URL for Supabase RPC calls (Vector matching). | Supabase > Project Settings > API. |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend | High-privilege key to bypass RLS for internal tool queries. | Supabase > Project Settings > API. |
| `DATABASE_URL` | Backend | PostgreSQL connection for Langchain Text-to-SQL. | Supabase > Database > Connection String. **Must use the Transaction Pooler (IPv4) for Docker compatibility.** |
| `NEXT_PUBLIC_API_URL` | Frontend | Directs the Next.js client to the FastAPI SSE endpoint. | Defaults to `http://localhost:8000`. |

<br>

---

## Deployment & Execution Commands

This application is strictly containerized to prevent Python environment mismatches or Node.js runtime errors (requires Node 20+). 

* **Spin up the entire stack:**
    Execute this from the root `Dual-Mode-Chatbot` directory:
    ```bash
    docker-compose up --build
    ```
    *The Next.js UI will mount at `http://localhost:3000` and the backend will listen on `http://localhost:8000`.*

* **Shut down and clean up:**
    ```bash
    docker-compose down
    ```

---

## Design Decisions & Architectural Trade-offs

To meet production-level engineering standards, several specific design decisions were implemented:

1. **IPv4 Transaction Pooling:** Supabase defaults to IPv6 direct connections, which fail inside Docker's default IPv4 bridge network. The `DATABASE_URL` specifically utilizes a Transaction Pooler (PgBouncer) to guarantee connectivity and manage stateless connection limits efficiently.
2. **Scroll Event Throttling:** The frontend auto-scrolls dynamically as tokens stream. To prevent main-thread blocking when users manually scroll up to read history, the scroll listener is wrapped in a 150ms throttle.
3. **Strict Dependency Pinning:** The Python backend utilizes `python:3.11-slim` for image optimization, explicitly installing `gcc` and `libpq-dev` to compile C-bindings for database drivers. Core libraries like `langchain` are strictly pinned (e.g., `<1.0.0`) to prevent breaking module resolution errors during container rebuilds.
4. **SQL Injection Mitigation:** The Text-to-SQL tool parses and strips raw Markdown code blocks via regex before execution, ensuring the SQLAlchemy driver does not crash on malformed LLM outputs. Read-only permissions are enforced at the database level.
5. **Lazy Initialization Pattern:** To ensure test runner stability during GitHub Actions CI/CD pipelines, all global dependencies (Supabase clients, LangGraph agents, and LLMs) are lazily initialized. This prevents `ValueError` crashes during module import if environment variables are not yet injected.
6. **Enterprise CI/CD & Testing:** A robust 24-test `pytest` suite covers API endpoints, tool logic, agent routing, and SQL extraction. GitHub Actions enforces these tests on every PR, guaranteeing that no breaking changes reach production.