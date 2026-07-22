# Mbwira

**Ubuzima bwawe, ibanga ryawe.** *(Your health, your secret.)*

Mbwira is a privacy-first digital support platform for people in Rwanda seeking help with sensitive topics — sexual and reproductive health, mental health, gender-based violence, substance use, and unwanted pregnancies. It combines a USSD channel that works on any phone, a web chat experience, and an automatic escalation pipeline to licensed counsellors, so that no one has to choose between staying anonymous and getting real help.

**Live deployment:** [mbwira.iraelie.tech](https://mbwira.iraelie.tech)

Built by **Team Achievers**, BSc Software Engineering, African Leadership University.

---

## Project status

| Channel / Feature | Status |
|---|---|
| USSD channel (Africa's Talking) | ✅ Implemented |
| Web chat | ✅ Implemented |
| Safety pre-filter and LLM escalation detection | ✅ Implemented |
| Session, message, and escalation persistence (PostgreSQL) | ✅ Implemented |
| CI/CD pipeline (build, push, auto-deploy) | ✅ Implemented |
| WhatsApp channel (Meta Cloud API) | 🔜 Planned — Sprint 2 |
| Counsellor dashboard | 🔜 Planned — Sprint 2 |
| Multi-counsellor accounts with audit logging | 🔜 Planned — Sprint 2 |

This is an active student project under continuous development, not a finished product. See [Notes and limitations](#notes-and-limitations) before relying on it for anything beyond demonstration and testing.

---

## What the project includes

- An anonymous web chat endpoint — [`backend/app/routers/chat.py`](backend/app/routers/chat.py)
- A USSD callback handler compatible with Africa's Talking — [`backend/app/routers/ussd.py`](backend/app/routers/ussd.py)
- A bilingual (Kinyarwanda/English) USSD menu tree — [`backend/app/content/ussd_tree.py`](backend/app/content/ussd_tree.py)
- Safety scanning and escalation logic — [`backend/app/services/safety.py`](backend/app/services/safety.py) and [`backend/app/services/handoff.py`](backend/app/services/handoff.py)
- LLM integration for conversational responses — [`backend/app/services/llm.py`](backend/app/services/llm.py)
- Session, message, referral, and escalation persistence — [`backend/app/models/db.py`](backend/app/models/db.py)
- A static landing page, web chat UI, and browser-based USSD simulator — [`frontend/`](frontend/)
- A Dockerized deployment with an automated CI/CD pipeline — [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml) and [`Dockerfile`](Dockerfile)

---

## Repository structure

```text
mbwira/
├── .github/
│   └── workflows/
│       └── ci.yaml              # Build, push, and auto-deploy pipeline
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   └── app/
│       ├── config.py
│       ├── main.py
│       ├── content/
│       │   ├── system_prompt.py
│       │   └── ussd_tree.py
│       ├── models/
│       │   └── db.py
│       ├── routers/
│       │   ├── chat.py
│       │   └── ussd.py
│       └── services/
│           ├── handoff.py
│           ├── llm.py
│           └── safety.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── chat.html
│   └── ussd/
│       ├── ussd_simulator.html
│       ├── ussd_simulator.css
│       └── ussd_simulator.js
├── .dockerignore
├── .gitignore
├── Dockerfile
└── README.md
```

---

## How the current implementation works

### Chat flow

The chat route in [`backend/app/routers/chat.py`](backend/app/routers/chat.py) accepts a session ID and a message, loads recent conversation history, sends it to the LLM layer, and stores the response. Every incoming and outgoing message is checked for high-risk signals before it reaches the user.

### USSD flow

The USSD handler in [`backend/app/routers/ussd.py`](backend/app/routers/ussd.py) receives standard Africa's Talking form fields (`sessionId`, `serviceCode`, `phoneNumber`, `text`), creates or resumes a session, walks the bilingual menu tree defined in [`backend/app/content/ussd_tree.py`](backend/app/content/ussd_tree.py), and returns a plain-text `CON`/`END` response formatted for feature-phone constraints (182-character screens, no persistent connection between key presses).

### Safety and escalation

The safety layer in [`backend/app/services/safety.py`](backend/app/services/safety.py) runs two checks: a deterministic keyword pre-filter scanning for crisis signals in English and Kinyarwanda, and a post-filter that inspects LLM output for an explicit `[ESCALATE: reason]` marker. When either check fires, [`backend/app/services/handoff.py`](backend/app/services/handoff.py) creates an escalation record for a counsellor to follow up on.

### Data persistence

Conversations, messages, and escalations are persisted in PostgreSQL via an async SQLAlchemy layer defined in [`backend/app/models/db.py`](backend/app/models/db.py). Phone numbers are stored as SHA-256 hashes by default; raw contact numbers are retained only where the channel already provides them (USSD, WhatsApp) and are never exposed without an explicit, logged action.

---

## Architecture

```
   USSD user            Web user
       │                    │
       ▼                    ▼
 Africa's Talking      HTTPS /chat
   gateway
       │                    │
       └─────────┬──────────┘
                  ▼
        ┌───────────────────┐
        │  FastAPI backend  │
        │  (Docker container)│
        └─────────┬─────────┘
                  ▼
        ┌───────────────────┐
        │   Safety layer    │
        │  pre + post filter│
        └─────────┬─────────┘
                  ▼
        ┌───────────────────┐
        │    PostgreSQL     │
        │ sessions/messages/│
        │    escalations    │
        └───────────────────┘
```

The application runs as a single Dockerized FastAPI service, deployed on a DigitalOcean droplet and served at [mbwira.iraelie.tech](https://mbwira.iraelie.tech).

---

## Deployment and CI/CD

Every push to `main` triggers a fully automated pipeline — no manual deployment steps:

1. **GitHub Actions** builds a Docker image from [`Dockerfile`](Dockerfile).
2. The image is pushed to **Docker Hub**.
3. GitHub Actions connects to the production **DigitalOcean droplet** over SSH and runs `docker compose pull && docker compose up -d`, replacing the running container with the new image.

Pipeline definition: [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml)

**Infrastructure:**

- **Hosting:** DigitalOcean droplet (2 GB RAM / 1 vCPU)
- **Domain:** [mbwira.iraelie.tech](https://mbwira.iraelie.tech), pointed at the droplet via an A record
- **Database:** PostgreSQL running alongside the application container
- **Container registry:** Docker Hub
- **Reverse proxy / TLS:** *(document here once configured — e.g. Caddy, Nginx, or Cloudflare)*

To deploy your own instance, provision a droplet, install Docker, create a `docker-compose.yml` pointing at the published image, and configure the `DROPLET_HOST` and `DROPLET_SSH_KEY` secrets in your GitHub repository settings so the workflow can reach it.

---

## Local development setup

1. Move into the backend folder.
2. Create and activate a Python virtual environment.
3. Install dependencies from [`backend/requirements.txt`](backend/requirements.txt).
4. Copy [`backend/.env.example`](backend/.env.example) to `.env` and fill in real values.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

At minimum, configure the LLM provider API key and the database connection string in `.env`. See `.env.example` for the full list of required and optional variables (LLM provider, Africa's Talking credentials, WhatsApp credentials for future use, counsellor dashboard password).

To run the full stack locally with PostgreSQL, use Docker:

```bash
docker compose up --build
```

---

## Demo and testing

1. Visit the landing page at [mbwira.iraelie.tech](https://mbwira.iraelie.tech), or open [`frontend/index.html`](frontend/index.html) locally.
2. Try the web chat at `/chat-ui`, or open [`frontend/chat.html`](frontend/chat.html) directly.
3. Try the USSD flow using the Africa's Talking sandbox simulator against the deployed `/ussd` endpoint, or open the local browser-based simulator at [`frontend/ussd/ussd_simulator.html`](frontend/ussd/ussd_simulator.html).
4. Exercise safety and escalation scenarios in both English and Kinyarwanda to confirm the pre-filter, post-filter, and escalation record creation all behave as expected.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend language | Python 3.11 |
| Web framework | FastAPI (async) |
| ORM / database driver | SQLAlchemy (async) + asyncpg |
| Database | PostgreSQL |
| LLM integration | Configurable provider (OpenAI / Anthropic) via environment variable |
| USSD gateway | Africa's Talking |
| Frontend | Static HTML, CSS, JavaScript |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Container registry | Docker Hub |
| Hosting | DigitalOcean Droplet |

---

## Notes and limitations

This repository is an early-stage prototype under active development, not a production-ready clinical service. Before any real-world deployment beyond demonstration and pilot testing, the following are required:

- Clinical review of all Kinyarwanda content and safety response text by a qualified health professional
- A signed data-processing and privacy compliance review against Rwanda's Law N° 058/2021 on personal data protection
- A staffed counsellor rota with defined response-time commitments for escalations
- Expanded automated test coverage across all channels
- Security review of the deployed infrastructure, including secrets management and rate limiting

Escalation behaviour, safety-layer content, and all user-facing guidance should be treated as demonstration material until that review is complete.

---

## Team

Built by **Team Achievers** — BSc Software Engineering, African Leadership University:

- Niyubwayo Irakoze Elie — Project Lead, Backend Architecture
- Iradukunda Suwafa — Research and Problem Analysis
- Kaliza Sabrina — System Design and Database Architecture
- Dan Gisa — Quality Assurance and Testing
- Uwase Davine — Documentation and Deployment

## License and context

Built as a social-impact academic project focused on privacy, safety, and access to support for young people in Rwanda. All content and escalation behaviour should be reviewed carefully before any deployment beyond demonstration and coursework purposes.
