
# AI Stock Advisor

Personal AI advisory tool for NSE equities. Single-user, no automated execution.
The tool generates daily pre-market briefings, intraday alerts, and post-market reviews
based on portfolio holdings, news, and macro signals.

> ⚠️ **Single-user only.** Sharing recommendations with others would trigger SEBI
> Registered Investment Advisor (RIA) registration requirements. Don't.

---

## Stack

| Layer | Tech |
|---|---|
| Compute | AWS EC2 t3.small in `ap-south-1` (Mumbai), Ubuntu 24.04 LTS |
| Network | Tailscale (private SSH/dashboard) + Tailscale Funnel (public ntfy reachability) |
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js (Phase 1) |
| Database | MongoDB Atlas M0 (Mumbai) |
| LLM | Anthropic Claude Sonnet 4.5 (reasoning) + Haiku 4.5 (bulk) |
| Search | Tavily |
| Notifications | Hybrid: self-hosted ntfy.sh (private) + public ntfy.sh (instant) + Resend (email) |
| Scheduler | APScheduler (Phase 2+) |
| Agent framework | LangGraph (Phase 2+) |
| Package manager | `uv` |
| Embeddings (Phase 4) | Voyage AI |
| Backtesting (Phase 4) | backtrader |

**Monthly cost:** ~$30 (Anthropic + Tavily). Infra is $0 via AWS credits.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                      EC2 t3.small (Mumbai)                       │
│                                                                   │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│  │  Next.js   │   │  FastAPI     │   │  Scheduler           │  │
│  │  Dashboard │◄──┤  Backend     │◄──┤  (APScheduler)       │  │
│  │  :3000     │   │  :8000       │   │  Pre/post-market     │  │
│  └────────────┘   └──────┬───────┘   │  intraday checks     │  │
│                          ▼           └──────────────────────┘  │
│                  ┌───────────────┐                              │
│                  │  Agent Layer  │                              │
│                  │  (LangGraph)  │                              │
│                  └───────┬───────┘                              │
│                          │                                       │
│                  ┌───────┴────────┐                              │
│                  ▼                ▼                              │
│           ┌──────────┐     ┌──────────────┐                     │
│           │ ntfy     │     │ Resend       │                     │
│           │ :8080    │     │ (email)      │                     │
│           │(localhost)│    └──────────────┘                     │
│           └────┬─────┘                                          │
│                │                                                │
│           ┌────┴──────┐                                         │
│           │ Tailscale │                                         │
│           │ Funnel    │                                         │
│           │ :443      │                                         │
│           └────┬──────┘                                         │
└────────────────┼───────────────────────────────────────────────┘
                 │
   *.ts.net HTTPS → APNs → iPhone (private notifications)
   ntfy.sh → APNs → iPhone (public, full-content notifications)
```

**Two notification paths:**
- **Private** (`push_private`) — sensitive content (digests, errors). Routed through your self-hosted ntfy via Tailscale Funnel. iOS shows "ntfy: new message" placeholder until the app polls your server for content.
- **Public** (`push_public`) — time-critical alerts (price, news). Routed through public `ntfy.sh` with random unguessable topic names. iOS shows full content instantly.

---

## Repository Layout

```text
ai-stock-advisor/
├── app/
│   ├── config/        # Settings loader (pydantic-settings)
│   ├── db/            # MongoDB clients (Phase 1)
│   ├── models/        # Pydantic models for collections (Phase 1)
│   ├── routers/       # FastAPI routes (Phase 1)
│   ├── services/      # External-service wrappers (notify.py done)
│   ├── agents/        # LangGraph agents (Phase 2+)
│   └── scheduler/     # APScheduler jobs (Phase 2+)
├── scripts/
│   └── smoke_test.py  # End-to-end check of all 5 services
├── tests/
├── pyproject.toml
└── README.md
```

---

## Local Development (macOS)

### Prerequisites
- Python 3.12+ (`uv` manages this automatically)
- `uv` package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Tailscale running and connected to your tailnet
- Mac's public IP allowlisted in MongoDB Atlas Network Access

### Setup

```bash
git clone git@github.com:YOUR-USERNAME/ai-stock-advisor.git
cd ai-stock-advisor
uv sync
```

Create `.env` in the project root (chmod 600, gitignored). Use the same values as EC2's `/etc/portfolio-advisor/secrets.env`:

```text
# Anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...

# Tavily
TAVILY_API_KEY=tvly-...

# MongoDB Atlas
MONGODB_URI=mongodb+srv://...

# Self-hosted ntfy (Tailscale Funnel)
NTFY_URL=https://portfolio-advisor.tailXXXXXX.ts.net
NTFY_USER=sahil
NTFY_PASS=...

# Public ntfy.sh (random unguessable topics)
NTFY_PUBLIC_TOPIC_PRICE=prtflo-price-...
NTFY_PUBLIC_TOPIC_NEWS=prtflo-news-...

# Resend
RESEND_API_KEY=re_...
RESEND_FROM=onboarding@resend.dev
RESEND_TO=your-personal-gmail@gmail.com
```

### Run smoke test

```bash
PYTHONPATH=. uv run python scripts/smoke_test.py
```

Expected: ✓ Anthropic, ✓ MongoDB, ✓ ntfy private, ✓ ntfy public, ✓ Email — plus notifications on phone and email in Gmail.

---

## Deployment to EC2

### First-time setup (already done)
- EC2 t3.small launched in `ap-south-1`, encrypted EBS, Elastic IP attached
- AWS Security Group: zero inbound rules
- Tailscale installed and joined to tailnet (`tag:server`)
- Tailscale Funnel exposing ntfy on `https://portfolio-advisor.tailXXXXXX.ts.net`
- OS hardened (UFW, SSH config, fail2ban, unattended-upgrades, locked root)
- Secrets at `/etc/portfolio-advisor/secrets.env` (chmod 600)
- ntfy installed with `sahil` admin user, topics: `digests`, `errors`
- GitHub deploy SSH key configured (`~/.ssh/github_ed25519`)

### Day-to-day deploy

```bash
# Author code locally on Mac in VSCode → push to GitHub
git push origin main

# SSH to EC2 (via Tailscale, no .pem keys needed)
ssh ubuntu@portfolio-advisor      # or ssh ubuntu@100.112.20.41

# Pull and install
cd ~/ai-stock-advisor
git pull
uv sync

# (Phase 1+) Restart services
# sudo systemctl restart portfolio-advisor
```

---

## Security Model

| Layer | Defense |
|---|---|
| Network | EC2 has zero AWS inbound rules; Tailscale (WireGuard) is the only path |
| Identity | Tailscale auth via Google + 2FA; Tailnet Lock prevents rogue device joins |
| OS | UFW (allow only `tailscale0`), key-only SSH, locked root, fail2ban, auto-updates |
| App | FastAPI/Next.js bind to Tailscale IP only (Phase 1+) |
| Secrets | `/etc/portfolio-advisor/secrets.env` (chmod 600), never in repo |
| Database | MongoDB Atlas IP allowlist limited to EC2 + Mac |
| Notifications | Private ntfy auth-protected; public ntfy.sh uses 24-char random topic names |
| Storage | EBS encrypted at rest |

---

## Notification Topics

### Self-hosted (`portfolio-advisor.tailXXXXXX.ts.net`)
- **`digests`** — pre-market briefing (8:45 IST), post-market review (16:00 IST)
- **`errors`** — pipeline failures, API quota issues, ingestion errors

### Public (`ntfy.sh`)
- **`prtflo-price-<random>`** — stop-loss/target hits, volume spikes, 52-week extremes
- **`prtflo-news-<random>`** — breaking news affecting a holding, with 1-paragraph LLM analysis

iOS app must subscribe to all 4. Pre-market and post-market full reports also arrive via email.

---

## Roadmap

### Phase 0 — Foundation ✅
EC2, Tailscale, OS hardening, MongoDB, ntfy, Resend, Anthropic, project skeleton, smoke test.

### Phase 1 — Portfolio + Dashboard (next)
- MongoDB schemas: `holdings`, `transactions`, `watchlist`, `alerts_log`
- FastAPI CRUD endpoints
- CSV import for ICICI portfolio statement
- `yfinance` integration for live NSE prices
- Next.js dashboard (Tailscale-only)
- systemd services for FastAPI + Next.js

### Phase 2 — News + Daily Digest
- RSS pullers (Moneycontrol, LiveMint, ET Markets, Reuters India)
- Tavily search for overnight global moves
- Macro fetchers (USD/INR, Brent, FII/DII flows, India VIX)
- Claude Haiku 4.5 summarization → MongoDB
- Pre-market digest agent (Claude Sonnet 4.5) → email + ntfy `digests`

### Phase 3 — Alerts + Intraday
- Price-rules engine (stop-loss, target, 52w high/low, volume spike, gap)
- News-driven alerts → ntfy public `prtflo-news`
- Earnings calendar reminders
- Post-market review at 16:00 IST

### Phase 4 — Edge Features
- Voyage AI embeddings + MongoDB Atlas Vector Search (RAG over historical news)
- Cross-asset signal detection (Brent, DXY, US 10Y, China PMI)
- Sentiment scoring with sector aggregation
- Backtesting with `backtrader`
- Concentration & risk reports
- Earnings-call transcript analysis from BSE/NSE filings

---

## Operational Notes

- **MongoDB Atlas IP allowlist** changes when you switch networks (home/cafe/etc). Re-add your Mac's IP at `cloud.mongodb.com` → Network Access if local dev fails.
- **Anthropic spending cap** set at $75/mo on the dashboard. Hard stop, not advisory.
- **Tailscale Funnel** must be enabled per node in Tailscale admin → Settings → Funnel.
- **iOS notification quirk:** Self-hosted ntfy on iOS shows placeholder banners ("ntfy: new message") until the app polls for content. This is APNs-by-design and the reason for the hybrid public/private split.

---

## License

Personal project. Not for redistribution.
