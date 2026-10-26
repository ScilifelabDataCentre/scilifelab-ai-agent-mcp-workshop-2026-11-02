# Template Repository for the SciLifeLab Data Centre

![Status: Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow)
[![Lychee Link Checker](https://github.com/ScilifelabDataCentre/data-centre-template/actions/workflows/lychee-main.yml/badge.svg?branch=main)](https://github.com/ScilifelabDataCentre/data-centre-template/actions/workflows/lychee-main.yml)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.22706806-blue)](https://doi.org/10.5281/zenodo.22706806)

This repository provides example configurations for a set of different tools. When creating a new repository with this as a template, remember to update the information to fit **your** repository, and delete any files that only apply to the data-centre-template repository. Each directory / file contains information on how to adopt a template into an already existing repository.

The end goal is for this repository to be populated with examples implementing guidelines detailed in the [SciLifeLab Data Centre's development guidelines repository](https://github.com/ScilifelabDataCentre/development-guidelines).

## Repository structure

```text
.
├── .github/        # GitHub-specific config, e.g. workflows and templates
│   ├── pull_request_template.md
│   ├── CODEOWNERS
│   └── workflows/
│       └── ...
├── .config/        # Tool config, one subdirectory per tool
│   ├── cspell/
│   ├── lychee/
│   └── renovate/
├── docs/architecture/decisions/     # Architecture Decision Record (ADR) template
├── instructions/   # Templates for instructions, e.g. user-facing
├── .development-guidelines-version  # Version of the development-guidelines repository that this template aligns with
├── CITATION.cff            # This repo's CITATION.cff file
├── CITATION.template.cff   # Template CITATION.cff file
└── README.md
```

## Repository contents

| Configuration                                                        | Purpose                                                                                                                                                                                                                                                                | Related guidelines                                                                                                                                   |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`.development-guidelines-version`](.development-guidelines-version) | Allows us to automatically keep track of when there's a change in the development-guidelines repository that **might** require a change in this repository. See [ADR 0001](docs/architecture/decisions/0001-track-the-development-guidelines-version-with-renovate.md) | -                                                                                                                                                    |
| [ADR template](docs/architecture/decisions/)                         | Template to use when starting with Architecture Decision Records and adding a new decision.                                                                                                                                                                            | [Architecture Decision Records](https://github.com/ScilifelabDataCentre/development-guidelines/tree/main/adrs)                                       |
| [`CITATION.cff`](CITATION.cff)                                       | Tells others how to cite **this** repository. Also enables the `Cite this repository` link in the repository side bar.                                                                                                                                                 | [Citing and Citability](https://github.com/ScilifelabDataCentre/development-guidelines/tree/main/citing_and_citability)                              |
| [`CITATION.template.cff`](CITATION.template.cff)                     | Template CITATION.cff file to copy-paste and adjust to another repository.                                                                                                                                                                                             | [Citing and Citability](https://github.com/ScilifelabDataCentre/development-guidelines/tree/main/citing_and_citability)                              |
| [`CODEOWNERS` file](.github/CODEOWNERS)                              | Defines which individuals or teams that are responsible for the contents of this repository.                                                                                                                                                                           | -                                                                                                                                                    |
| [CSpell](.config/cspell/README.md)                                   | Allows spell checking for files changed in a PR                                                                                                                                                                                                                        | -                                                                                                                                                    |
| [Citation instruction template](instructions/citing.template.md)     | Template for user-facing instructions on how to cite our services and code.                                                                                                                                                                                            | [Making Services and Code Citable](https://github.com/ScilifelabDataCentre/development-guidelines/blob/main/citing_and_citability/making-citable.md) |
| [Lychee](.config/lychee/README.md)                                   | Verifying that all links in the repository work                                                                                                                                                                                                                        | -                                                                                                                                                    |
| [Pull request template](.github/pull_request_template.md)            | When a PR is opened, the description is automatically filled with the contents of this file. It helps make pull requests easier to prepare and review.                                                                                                                 | [Pull Request Guidelines](https://github.com/ScilifelabDataCentre/development-guidelines/tree/main/pull_requests)                                    |
| [Renovate](.config/renovate/README.md)                               | Allows repositories in ScilifelabDataCentre GitHub Organisation to use a custom Renovate preset in their Renovate configuration instead of teams building their own completely from scratch.                                                                           | -                                                                                                                                                    |

> Links pointing to PRs will be replaced once PRs in `development-guidelines` repository are merged.
