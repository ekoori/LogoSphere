# LogoSphere

> An economy that remembers *why*.

Every system that scales human cooperation must compress what people care about into something it can move around. Money does it with price. Platforms do it with clicks. Each translation is lossy — and what leaks away is the meaning. **LogoSphere is an attempt to keep it.**

## The problem: value collapses under measurement

Tell a community its worth is a number, and it will manufacture the number. This is Goodhart's trap: *when a measure becomes a target, it stops being a good measure.* Likes, daily-active-users, reputation points — thin proxies are easy to optimise precisely because they've already discarded the reasons underneath them.

A meaning-centric platform inherits a sharper version of the same risk. The moment meaning can be cashed in, people optimise for *appearing* meaningful. The proxy doesn't just mislead — it crowds out the thing it was meant to stand for.

## The idea: Thick Models of Value

A **Thick Model of Value (TMV)** is a representation rich enough to survive being optimised. Where a preference records *what* you chose, and a written rule records *what's allowed*, a TMV carries the *why* — and the texture around it:

- **Reasons** — the "because" behind a choice, not only the choice itself
- **Endorsement** — what you'd still choose after reflection, told apart from impulse
- **Context & roles** — the promises, boundaries, and obligations a situation carries
- **Trade-offs** — priorities, thresholds, and the lines you will not cross
- **Collective goods** — trust, legitimacy, the commons no single person holds
- **Endorsed change** — growth you would affirm, distinguished from drift and capture

To be usable by humans, a thick value compresses into a **Value Card** — a small, honest artefact, readable in ten seconds, that you'd recognise as your own. Each card is **CLEAR**: **C**oncrete behaviours, **L**evers & limits, **E**ndorsement, **A**nti-signals (what drift looks like), **R**eview (revisited on a cadence).

Meaning itself isn't pleasure, and it isn't status. Following Viktor Frankl, it arrives by three routes, and a healthy ledger can tell them apart:

| Mode | What it captures |
|---|---|
| **Creative** | what you make and give |
| **Experiential** | what you receive and encounter |
| **Attitudinal** | the stance you take under constraint |

The whole design turns on one distinction: **endorsed meaning** is what holds up under reflection; **performed meaning** is status play wearing meaning's clothes. Every mechanism in LogoSphere — receipts over points, reasons over scores, drift clauses over leaderboards — exists to keep the first from collapsing into the second.

Read the full argument on the app's **About** page (`frontend/src/pages/About.js`), or see **[MANIFESTO.md](MANIFESTO.md)** for the canonical vocabulary.

## How the philosophy is woven into the platform

None of this is a rewrite of how people already give — it's a structure for naming it honestly.

| Primitive | Carries |
|---|---|
| **Meaning Graph** | A profile's handful of Value Cards — what it cares about, and why — instead of a tag cloud. |
| **Receipt** (Meaning Receipt) | A record of an exchange that names the value it expressed, what it cost, and the receiver's endorsement. |
| **Acknowledgement** | Public thanks stays lightweight — warmth, not currency. The weight-bearing work belongs to Receipts. |
| **Sphere & Alliance** | A community or federation declares its shared values — and a "we're drifting if…" clause to catch its own slide. |
| **Openings** | Offers and Needs carry the values they serve; matching favours overlaps that are endorsed and evidenced. |
| **Interaction** | The real human event between people that a Receipt or Acknowledgement attests to. |
| **Meaning Trail** | The living trace of a profile's or alliance's Receipts and Acknowledgements over time. |
| **Governance / Decisions** | Liquid democracy: delegated, revisable decision-making, in the open. |

## Technologies Used

- **React** — frontend
- **Flask** — RESTful APIs
- **Cassandra** — database

## Requirements

- Python 3.7+
- Node.js 14.0+
- Cassandra

## Installation and Setup

1. Clone the repository:

```
git clone https://github.com/ekoori/LogoSphere
cd LogoSphere
```

2. Install Python dependencies:

```
pip install -r ./backend/requirements.txt
```

3. Install JavaScript dependencies:

```
cd frontend
npm install
```

4. Run the Cassandra service and load the schema (`database/schema.cql`) and demo seed data (`database/dummy_data/`).
5. Run the backend server:

```
cd backend
python run_local.py
```

6. Run the frontend:

```
cd frontend
npm start
```

## Contributing

If you'd rather your contributions be remembered for what they meant than counted for what they scored, you belong here. Fork the repository, make your changes, and submit a pull request.

## License

LogoSphere is open-source software licensed under the MIT license.
