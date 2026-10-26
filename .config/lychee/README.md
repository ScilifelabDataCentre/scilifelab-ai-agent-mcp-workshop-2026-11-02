# Lychee Link Checker

In this template, links are checked and verified to work with lychee (via `lychee-action`). This guide explains how link checking is configured, how it works and how to use it in another repository.

[lychee tool (`lychee`)](https://github.com/lycheeverse/lychee) ·
[lychee GitHub Action (`lychee-action`)](https://github.com/lycheeverse/lychee-action) ·
[lychee Configuration Guide](https://lychee.cli.rs/guides/config/)

> [!NOTE]
> **Jump straight to setting it up?**
>
> Go to [How to use this in your repository](#how-to-use-this-in-your-repository).

## Why?

It's impossible to keep track of all links in a repository and manually make sure that all internal and external links continue to work. Without an automated link checker, we rely on others finding and reporting broken links.

There are a number of different link checkers and we cannot look into all of them. In this case, the choice stood mostly between the currently used (in `development-guidelines` repository at the time of writing) `markdown-link-check` and lychee - lychee was chosen.

In this repository, lychee (via `lychee-action`) is configured to run when a Pull Request (PR) is opened or updated, on a schedule (once a day), and when manually triggered.

**lychee was chosen because:**

- Open Source, dual-licensed MIT / Apache-2.0 &rarr; no restrictions for us to use it.
- Actively maintained by the [lycheeverse GitHub Organisation](https://github.com/lycheeverse).
- Fast - written in Rust.
- Can check links in a variety of different formats, and both internal and external links.
- Configurable, e.g. via our `lychee-config.toml`: Can exclude URL patterns, add accepted status codes, enable scanning internal link anchors, add timeouts and retries, etc.
- Allows caching of results.
- `lychee` can be installed and run locally before pushing to the remote branch.

## Files in this setup

This template uses two GitHub Actions workflow files and one lychee configuration file ([`.config/lychee/lychee-config.toml`](lychee-config.toml)).

```text
.
├── .github/
│   └── workflows/
│       ├── lychee-main.yml
│       └── lychee-pr.yml
└── .config/
    └── lychee/
        ├── README.md
        └── lychee-config.toml
```

| File                                | Purpose                                                                   |
| ----------------------------------- | ------------------------------------------------------------------------- |
| `.github/workflows/lychee-main.yml` | Runs the lychee link checker once a day and when manually triggered. [^1] |
| `.github/workflows/lychee-pr.yml`   | Runs the lychee link checker when a PR is opened or updated [^2]          |
| `.config/lychee/lychee-config.toml` | lychee configuration file used by the workflows                           |
| `.config/lychee/README.md`          | This guide                                                                |

[^1]: Even if we use the most optimal link checker, external links can break without any changes to our repository

[^2]: We want to verify the links before merging

## What do the workflows do?

The two workflows run on different events as described in the table above, and they also behave differently:

| When                                       | lychee <br> run?   | Result uploaded to <br> GitHub issue? | Result is saved to cache? |
| ------------------------------------------ | ------------------ | ------------------------------------- | ------------------------- |
| PR is opened / updated                     | :white_check_mark: | :x:                                   | :white_check_mark:        |
| Scheduled run: Every day at midnight (UTC) | :white_check_mark: | :white_check_mark:                    | :x:                       |
| On manual trigger                          | :white_check_mark: | :white_check_mark:                    | :x:                       |

## Configuration options

lychee has a number of defaults (subject to change) and a wide variety of different configuration options, impossible for us to keep up to date in this type of document. For information on the different options, see the link to the "lychee Configuration Guide" at the top of this file.

The configuration file in this setup includes the following options:

- `cache` to enable caching of the results
- `cache_exclude_status` to exclude failing links from cache
- `exclude` to be able to exclude some URLs from the link checker
- `extensions` to expand link checking to more file types.
- `hidden = true` to also check links within hidden files (e.g. `.config/`, `.github/`...)
- `include_fragments` to also check headers (e.g. we could link to `#configuration-options` in this file and it would catch potential issues in that URL)
- `no_progress = true` to disable interactive progress bar during CI
- `root_dir` to make sure future absolute local links are found
- `verbose = "info"` to get INFO level logging output during runs

Regarding `no_progress` and `verbose`: These values are normally passed into `lychee` automatically by the `lychee-action`, but it is overridden when `args` is passed in by our workflow file. Instead of keeping all args in the workflow file, we specify all of them in the configuration file.

## How to use this in your repository

1. Recreate the file and folder structure shown in the [Files in this setup](#files-in-this-setup) section in your repository, including the exact contents of each file.

   - **Only want to run lychee manually / on schedule?** Skip the `lychee-pr.yml` file - only copy `lychee-main.yml`.
   - **Only want to run lychee on PR?** Skip the `lychee-main.yml` file - only copy `lychee-pr.yml`.

2. Add `.lycheecache` to your `.gitignore` so that you don't accidentally push it to your remote branch after potential local lychee runs.
3. Verify that the configuration file seems reasonable for your repository; Add and remove options when needed.
4. In the configuration file, replace the regular expressions within the `exclude`. Either keep it empty or add URLs that you already know should be ignored during the link checking. See the [lychee.example.toml](https://github.com/lycheeverse/lychee/blob/54f8bf47ffbd35973b8eb016ccbc67221c75ba5f/lychee.example.toml#L161) for examples.
5. Push to your remote branch and open a PR. Adjust your configuration depending on the workflow results.
   - No issue should be created. Issue only created during manual or scheduled run after merge of PR.

## Notes regarding this setup

- If we only want to check files changed in a PR, we have to configure this ourselves. This means that a link breaking anywhere blocks unrelated PRs. This is not covered in this setup. If it becomes a problem, we can have another look, and hopefully there will be an existing tool or solution for it that feels less hacky than what would be needed at the moment.
- lychee does not allow us to add any inline-ignores like markdown-link-check does.
- After the first scheduled / manual run there will always be an open issue with the latest link checker results
- Instead of using the `.config/lychee/lychee-config.toml`, we could have used the `.lycheeignore` as described in the actions documentation. However, we wanted to be able to set more configuration options and:
  - `.lycheeignore` doesn't allow that
  - `lychee-config.toml` allows both ignoring patterns and configuring args.
  - `.lycheeignore` would have to be placed in the directory root, which we are trying to avoid
- We pin versions in the workflow instead of specific SHAs. While it's recommended to pin the SHA, and this repository has Renovate configured to handle digest updates, this template is intended for copy-paste into other repositories (which might not have that Renovate configuration set).
