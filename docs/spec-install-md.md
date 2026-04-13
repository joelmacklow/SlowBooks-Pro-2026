# Spec: INSTALL.md

## Deliverable
- Root-level `INSTALL.md`

## Required sections
- Overview / when to use this guide
- Prerequisites
- Self-contained Docker install
- Docker with external Postgres
- Local Python install
- Environment variable reference (DATABASE_URL + POSTGRES_*)
- Migrate/seed steps
- First-run verification steps
- Backup note
- Common setup pitfalls / troubleshooting basics

## README change
- Add a short pointer directing detailed setup readers to `INSTALL.md`.

## Constraints
- Reflect the repo's current Docker/self-contained default and external Postgres support.
- Do not invent production deployment guidance beyond current repo support.
