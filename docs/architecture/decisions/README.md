# Architecture Decision Records (ADRs)

This directory contains a copy-pasteable template for architecture decision records (ADRs), aligned with the SciLifeLab Data Centre [development guidelines](https://github.com/ScilifelabDataCentre/development-guidelines/tree/main/adrs).

> [!IMPORTANT]
> Once it's merged, an ADR is not rewritten. Only the status of an ADR changes. See [Changing the status of an accepted ADR](#changing-the-status-of-an-accepted-adr).

## How to add an ADR

1. Create a copy of the template file `adr-template.md`.
2. Name the file according to the instructions in the template file.
3. Replace the placeholders with information regarding your decision. Read the comments in the file for hints and instructions on what the sections should contain.
4. Push to your remote branch and open a PR to your default branch.

## Changing the status of an accepted ADR

An accepted ADR can change status in two ways:

- **Deprecated** - When a decision no longer applies and nothing replaces it.
- **Superseded** - When there's a new decision taking its place. _Always write the new ADR first_, then point the old ADR at it (see template comments for instructions).
