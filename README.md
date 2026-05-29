# Robo-CFO Brazil

> ⚠️ **AVISO LEGAL:** Este é um **simulador educacional**. Não constitui assessoria financeira.
> Os números são ilustrativos. Consulte um profissional habilitado antes de tomar decisões financeiras.

An educational personal-finance decision simulator for Brazilian taxpayers. Given a person's full financial picture, it evaluates candidate strategies via Monte Carlo simulation and explains the reasoning.

**Core questions answered:**
- Should I pay down debt or invest?
- Am I on track to retire at age X?
- What is the most tax-efficient order to redeem my investments?

---

## Quick start

```bash
# Copy and fill in your API key (optional — powers the "Explicar mais" button)
cp .env.example .env

docker compose up --build
```

Open **http://localhost** in your browser.

---

## Architecture

```
contracts.py  (frozen — the single source of truth for all components)
     │
     ▼
Domain model → Tax engine → Monte Carlo → Optimizer → Explanation layer
                (4 regimes)   (path-based)  (brute-force  (Jinja2 + LLM)
                               IPCA BRL)     evaluation)
                     │
                     ▼
              FastAPI backend  ←→  React + TypeScript frontend
```

### Tax engine — four parallel Brazilian federal regimes

Brazil does **not** stack capital gains on top of ordinary income. Each regime is independent:

| Regime | Scope | Rate |
|---|---|---|
| IRPF | Salary, pró-labore, rent | Progressive up to 27.5% + Lei 15.270/2025 reducer |
| Variable income | Stocks/ETFs (monthly) | 15% swing, 20% day trade; R$20k/month exemption |
| Fixed income / funds | Tesouro, CDB, funds | Regressive 22.5% → 15% by holding period |
| IRPFM | High earners (> R$600k/year) | Progressive 0–10% top-up |

All brackets and rates live in `backend/app/data/tax_tables/<year>.json` — a new year means new data, never new logic.

### Monte Carlo

Samples 10,000 return **paths** (not a single mean) to capture sequence-of-returns risk. All values in BRL; inflation modeled via stochastic IPCA. Per-asset-class return assumptions supported.

### Contracts-first parallelization

`contracts.py` was written first and frozen. The tax engine, Monte Carlo, optimizer, API, and frontend were all built in parallel worktrees against these contracts as the shared interface. The `TaxFn` Protocol allows the simulator to be tested with a stub before the real engine is available.

---

## Development

```bash
# Backend (from backend/)
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000

# Frontend (from frontend/)
npm install
npm run dev          # http://localhost:5173

# Tests
cd backend && uv run pytest --cov=app
cd frontend && npm test
```

### LLM explanation path

The "Explicar mais" button calls DeepSeek (or Anthropic) to elaborate on the structured `Explanation` result. Configure via `.env`:

```
LLM_PROVIDER=deepseek          # or: anthropic / none
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

The LLM only **renders** — it receives structured numbers and may not recompute them.

---

## Out of scope (v1)

- State taxes (ICMS, ISS, ITCMD)
- PGBL / VGBL private pension (phase 2)
- Open Finance / Pluggy integration (phase 2)
- Authentication / multi-user
- Cloud deployment
