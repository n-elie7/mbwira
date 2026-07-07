# Mbwira

Mbwira is a privacy-first support prototype for people in Rwanda who may need help with sensitive topics such as mental health, gender-based violence, substance use, and unwanted pregnancies.

The project combines a lightweight web chat experience with a USSD-style flow so users can describe their concerns in plain language and receive compassionate, guided support without exposing their identity.

## What the project includes

- A chat endpoint for anonymous conversations in [backend/app/routers/chat.py](backend/app/routers/chat.py)
- A USSD-style callback handler in [backend/app/routers/ussd.py](backend/app/routers/ussd.py)
- Safety scanning and escalation logic in [backend/app/services/safety.py](backend/app/services/safety.py) and [backend/app/services/handoff.py](backend/app/services/handoff.py)
- LLM integration in [backend/app/services/llm.py](backend/app/services/llm.py)
- Session, message, referral, and escalation persistence in [backend/app/models/db.py](backend/app/models/db.py)
- A static landing page and browser-based USSD simulator in [frontend/index.html](frontend/index.html) and [frontend/ussd/ussd_simulator.html](frontend/ussd/ussd_simulator.html)

## Repository structure

```text
mbwira/
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   └── app/
│       ├── config.py
│       ├── content/
│       │   └── system_prompt.py
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
│   ├── style.
|   ├── chat.html
│   └── ussd/
│       ├── ussd_simulator.html
│       ├── ussd_simulator.css
│       └── ussd_simulator.js
└── README.md
```

## How the current implementation works

### Chat flow

The chat route in [backend/app/routers/chat.py](backend/app/routers/chat.py) accepts a session ID and a message, loads recent history, sends the conversation to the LLM layer, and stores the output. Before and after generation, the message is checked for high-risk signals.

### USSD flow

The USSD handler in [backend/app/routers/ussd.py](backend/app/routers/ussd.py) receives form fields such as `sessionId`, `serviceCode`, `phoneNumber`, and `text`. It creates or loads a session, follows the menu logic, and returns a plain-text response suitable for a feature-phone experience.

### Safety and escalation

The safety layer in [backend/app/services/safety.py](backend/app/services/safety.py) scans incoming messages for keywords and patterns in English and Kinyarwanda. It also inspects LLM output for escalation markers such as `[ESCALATE: reason]`. When a risk signal is detected, [backend/app/services/handoff.py](backend/app/services/handoff.py) creates an escalation record for follow-up.

## Setup

1. Move into the backend folder.
2. Create and activate a Python virtual environment.
3. Install the dependencies from [backend/requirements.txt](backend/requirements.txt).
4. Copy [backend/.env.example](backend/.env.example) to `.env` and fill in the values.

Example:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

At minimum, configure the environment values for the LLM provider and database connection.

## Demo and testing

A simple way to explore the prototype is:

1. Open [frontend/index.html](frontend/index.html) for the landing page.
2. Open [frontend/ussd/ussd_simulator.html](frontend/ussd/ussd_simulator.html) to try the USSD simulator.
3. Exercise the chat route with a session created from the chat endpoint and test safety scenarios in both English and Kinyarwanda.

## Tech choices

- Python with an async-friendly backend structure
- SQLAlchemy for persistence
- LLM-based conversational support
- Static HTML/CSS/JavaScript for the demo frontend
- Environment-based configuration for API keys and database settings

## Notes

This repository is an early-stage prototype rather than a fully production-ready service. It is useful for demonstrations, testing, and iteration, but it should be reviewed carefully before any real-world deployment.

## License and context

Built as a social-impact prototype focused on privacy, safety, and access to support in Rwanda. All content and escalation behavior should be reviewed carefully before deployment.