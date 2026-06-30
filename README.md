# LogoSphere

> A sphere of shared meaning, reason, and value.

## Introduction

LogoSphere is a social platform designed to foster stronger connections within communities. It's built on the principles of the gift economy and liquid democracy. The goal of LogoSphere is to empower individuals and communities to share resources and make collective decisions in a transparent and engaged manner.

Our purpose is to redefine how we engage with the economy and democracy. LogoSphere seeks to promote an alternative to money-driven society — a culture of giving, where goods and services are offered without any explicit agreement for immediate or future reward. By incorporating liquid democracy, we aim to make decision-making more accessible and representative.

See **[MANIFESTO.md](MANIFESTO.md)** for the vocabulary and philosophy behind the platform.

## Key Focus

- **Trust-Based Interactions**: Encouraging interactions based on trust, respect, and mutual support.
- **Gift Economy**: Promoting a culture of giving, where goods and services are given without any explicit agreement for immediate or future reward.
- **Liquid Democracy**: Striving for a democratic system where power rests with the many — the contributors — not the few.
- **Transparency**: Ensuring that all interactions and decisions are visible, fostering accountability and trust among members.
- **Community Empowerment**: Giving communities the tools they need to organize, share resources, and make collective decisions that benefit all members.

## High-Level Concepts

- **Meaning Receipt** (or **Receipt**) — an endorsed record of what happened and why it mattered: a specific interaction between parties. It is the trust-affirming artifact that captures and preserves a moment of meaning.
- **Acknowledgement** — a lightweight appreciation, less formal than a Receipt, that can be publicly linked to a member's profile. A simple yet powerful way to recognize others and enhance reputation and visibility.
- **Meaning Trail** — the living trace of Receipts and Acknowledgements over time. It functions as a historical ledger of a member's or alliance's interactions, providing a transparent backstory of trust.
- **Profile** — at the centre of LogoSphere. Whether it belongs to an individual member or an alliance, it centralises basic information, a Meaning Trail, and details about offers, needs, and projects.
- **Alliance** — a federation or partnership: a group of members who come together for a common purpose or to govern collective activity. Alliance profiles support delegated management.
- **Sphere** — a broader community or context with shared norms and meaning, which may contain individual members, alliances, and projects bound by shared values or geography.
- **Project** — a mission-driven collaboration. Each project is led by a mission and governed by a set of policies that can be dynamically adjusted by members with the appropriate authority.
- **Meaning Graph** — a structured representation of the values associated with a profile, alliance, or project. It drives matching across the network and underpins the platform's statistics.
- **Offers / Needs** — members and alliances can post what they can contribute (an **Offer**) or what they are asking for (a **Need**), enabling efficient resource matching within the community.
- **Openings** — the place where possibilities for contribution are posted: the central hub where Offers and Needs meet.
- **Governance & Decisions** — LogoSphere supports delegation of voting rights and decision-making power. Issues can be democratically decided, with results able to influence project direction or organizational structure.

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

We welcome contributions from the community. To contribute, please fork the repository, make your changes, and submit a pull request.

## License

LogoSphere is open-source software licensed under the MIT license.
