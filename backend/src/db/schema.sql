-- Sessions: the only "identity" a user has, and it's disposable
CREATE TABLE anonymous_sessions (
    session_token UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '24 hours'),
    category VARCHAR(30) -- 'mental_health' | 'gbv' | 'substance_abuse' | 'unwanted_pregnancy' | NULL
);

-- Messages: tied only to session_token, never to a person
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    session_token UUID NOT NULL REFERENCES anonymous_sessions(session_token) ON DELETE CASCADE,
    sender VARCHAR(10) NOT NULL CHECK (sender IN ('user', 'assistant')),
    content TEXT NOT NULL,
    risk_flag VARCHAR(20), -- 'none' | 'moderate' | 'high' — set later by the AI service
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Referral resources: static reference data, not user data
CREATE TABLE referrals (
    id SERIAL PRIMARY KEY,
    category VARCHAR(30) NOT NULL,
    region VARCHAR(50), -- e.g. 'Kigali', 'national'
    name VARCHAR(120) NOT NULL,
    contact_info VARCHAR(200) NOT NULL,
    description TEXT
);
