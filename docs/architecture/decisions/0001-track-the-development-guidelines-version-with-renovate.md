# 1. Track the development-guidelines version with Renovate

Date: 2026-09-21

## Status

Accepted <!-- One of: Accepted, Deprecated, Superseded -->
<!-- If Superseded, add: Superseded by {{ SUPERSEDING_ADR_NUMBER }} -->

## Context

The goal of this repository is to:

- Implement what the `development-guidelines` repository specifies.
- Provide a template for new repositories and copy-pasteable template files / configurations for existing repositories, to simplify day-to-day work for the SciLifeLab Data Centre teams.

This decision was made while implementing the ADR guidelines: The guidelines link to an external template in the "How to use ADRs" section. Any changes to the external template or our guidelines can make this repository unaligned with our own development guidelines since keeping them aligned currently relies on someone remembering to look. This is, of course, not specific to the ADRs. Repositories created from this template inherit whatever state it's in, so this drift spreads across our repositories.

At the time of writing, `development-guidelines` is a private repository. It will, however, soon be changed to public, and it is released with versions.

## Decision

Record the version of the development-guidelines repository in [`.development-guidelines-version`](../../../.development-guidelines-version) **and** use a custom rule in Renovate to notify us when a new version is released.

## Consequences

- **Pros**
  - We automatically find out when there's a new guidelines version available.
  - The pinned version records which guidelines version this repository implements.
- **Cons**
  - The Renovate PR only bumps the `.development-guidelines-version` file. Someone still has to read what changed and apply it to the template(s). We should not be merging the Renovate PRs until this repository aligns with the new development-guidelines version.
  - Downstream repos don't get this unless they also copy the version file and the Renovate rule.

<!-- Optional section.
Uncomment if relevant for decision and fill with sources.

## References

{{ REFERENCES }}
-->
