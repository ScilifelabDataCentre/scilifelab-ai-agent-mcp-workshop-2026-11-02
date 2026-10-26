# Spell checking with CSpell

This guide explains how spell checking is configured in this template, how the setup works, how to use it in another repository and what to do when it incorrectly flags words.

<p>
  <a href="https://github.com/streetsidesoftware/cspell-action">CSpell GitHub Action</a> ·
  <a href="https://cspell.org/">CSpell docs</a> ·
  <a href="https://github.com/streetsidesoftware/cspell-dicts#cspell-dicts">CSpell Dictionaries</a>
</p>

> [!NOTE]
> **Want to cut to the chase?**
>
> Go to [How to use this in your repository](#how-to-use-this-in-your-repository).

## What is CSpell?

CSpell is a spell checker for code and documentation. It scans repository files and flags words that are not recognised by the configured languages, dictionaries, ignore patterns, or project-specific word lists.

In this template, CSpell runs automatically on pull requests to help catch spelling mistakes before changes are merged.

### Why CSpell?

CSpell is designed for spell checking code repositories, not only documentation. It can check documentation, comments, configuration files, and other repository content, while allowing us to configure it for specific projects and repositories.

CSpell has an official GitHub Action and a large set of dictionaries that can be enabled when needed. Other tools may be better for specific use cases, for example:

<!-- cspell:ignore Codespell -->

- [Vale](https://github.com/vale-cli/vale-action) is a style and writing-rule linter. It is better suited for enforcing style guides, preferred terminology, tone, and wording conventions in documentation and other written text. Vale could be added alongside CSpell if stricter writing-style checks are needed.
- [Codespell](https://github.com/marketplace/actions/codespell-with-annotations) checks code for common misspellings. It is better suited for catching known typo patterns than for dictionary-based spell checking against full language and technical dictionaries.

At the time of writing this template, CSpell gives the best balance between useful typo detection, configurability, and ease of use in the GitHub Actions.

## Files in this setup

This template uses one GitHub Actions workflow file and one CSpell configuration directory. The configuration files are kept in `.config/cspell` instead of the repository root to keep the repository structured and make the template as easy as possible to use out of the box.

```text
.
├── .github/
│   └── workflows/
│       └── cspell.yml
└── .config/
    └── cspell/
        ├── custom-dicts/
        │   ├── approved-acronyms.txt
        │   ├── approved-names.txt
        │   ├── forbidden-words.txt
        │   └── project-specific-words.txt
        ├── README.md
        ├── cspell-config.yml
        ├── package-lock.json
        └── package.json
```

| File                                                               | Purpose                                                                                                                            |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `.github/workflows/cspell.yml`                                     | Runs CSpell                                                                                                                        |
| `.config/cspell/cspell-config.yml`                                 | CSpell configuration file used by the workflow. Defines languages, dictionaries, ignored patterns and project-specific word lists. |
| `.config/cspell/custom-dicts/approved-acronyms.txt`                | Acronyms used across the repository. Enabled globally.                                                                             |
| `.config/cspell/custom-dicts/approved-names.txt`                   | Personal and organisation names. Enabled globally.                                                                                 |
| `.config/cspell/custom-dicts/project-specific-words.txt`           | List of valid repository-specific words that are not covered by any available CSpell dictionaries but that CSpell should allow     |
| `.config/cspell/custom-dicts/forbidden-words.txt`                  | List of words that should be flagged by CSpell but that are allowed by one or more enabled dictionaries                            |
| `.config/cspell/custom-dicts/{...}-words.txt`                      | Words valid only in one content directory. Enabled per directory under overrides.                                                  |
| `.config/cspell/package.json` / `.config/cspell/package-lock.json` | Define and lock the npm dependencies required by the CSpell configuration, such as additional dictionaries.                        |
| `.config/cspell/README.md`                                         | This guide                                                                                                                         |

## How this setup works

The workflow explicitly includes some default action settings. The workflow would work the same way without these settings being present in the file, but including them increases clarity and reduces the risk of confusion.

- The spell check runs when a PR is opened or updated
- The workflow is configured to check changed files in the PR
  - `incremental_files_only: true` tells CSpell to only check the PR diff, meaning files changed in the PR. It does not check the rest of the repository.
  - `check_dot_files: true` makes sure that dotfiles are scanned. This includes files under `.github/` and `.config/`. If some dot files should not be scanned, add them to a `ignorePaths:` list in `.config/cspell/cspell-config.yml`.
  - `files: ''` tells CSpell to check all file types selected by the action. This is the _default_.
- The CSpell action uses `.config/cspell/cspell-config.yml` for language, dictionary, ignored patterns, and project-specific-word settings.
  - `language` configures the languages used during the spell check, here British English and Swedish
  - `import` imports dictionaries that need to be installed in the workflow before CSpell runs, in this case Swedish and People Names
  - `caseSensitive` allows CSpell to distinguish between different casing, e.g. GitHub and github.
  - `useGitignore` tells CSpell to ignore any files that are listed in the `.gitignore`.
  - `dictionaries` list dictionaries from the [`cspell-dicts` repository](https://github.com/streetsidesoftware/cspell-dicts#cspell-dicts) that do not require installation before use. They are bundled with CSpell and are enabled when listed under the `dictionaries` section
  - `dictionaryDefinitions` imports the two custom files as dictionaries:
    - `custom-dicts/project-specific-words.txt` contains words that are not included in any other [CSpell-available dictionary](https://github.com/streetsidesoftware/cspell-dicts#cspell-dicts) but that we consider correct and CSpell should not flag.
    - `custom-dicts/forbidden-words.txt` contains words that are allowed in an enabled CSpell dictionary, but that we want to flag as incorrect, e.g. US English spellings.
  - `ignoreRegExpList` tells CSpell to ignore specific patterns.
  - `ignorePaths` tells CSpell to ignore specific files in your repository.
  - `languageSettings` specifies some configuration to apply to only specific languages, incl. code languages. Note that CSpell has its own name for each file type: Markdown files are `markdown`, even when they contain HTML.
  - `overrides` contains rules, dictionaries, and single words that should only be enabled in specific files and directories, not globally. Prefer `languageSettings` when a rule applies to a whole file type, and `overrides` only when it applies to a specific folder or file.
- If CSpell finds spelling issues, the workflow fails. Spelling issues are reported as GitHub annotations, and suggestions are shown when available.

## How to use this in your repository

> [!NOTE]
> **You do not need to install CSpell on your machine in order to follow the guides in this README.** However, [the CSpell docs](https://cspell.org/docs/installation) have information on what the requirements are, and also instructions on how to install locally if needed / wanted.
>
> **Most of the files in this setup have instructions at the top.**
> Follow the instructions when altering the files.

### Initial setup

> [!IMPORTANT]
> Your repository's `.gitignore` should contain `node_modules/`. Do not push the `node_modules/` to your remote branch.

1. Recreate the file and folder structure shown in the [Files in this setup](#files-in-this-setup) section in your repository, including the exact contents of each file. You can and will alter the contents later, but initially the files should be exact copies. While this README is not technically needed, we do recommend that your repository includes this as well since the information is intended to help you with flagged words and store information you might not remember in the future.
2. Install the initial CSpell dictionaries specified in `package.json` by running the following command in your repository root:

   ```bash
   npm ci --prefix .config/cspell --ignore-scripts
   ```

3. _Optional (Recommended):_ Remove words from the `custom-dicts/project-specific-words.txt` and `custom-dicts/forbidden-words.txt` files. You can also start from scratch completely by removing the example entires.
   1. Does `custom-dicts/project-specific-words.txt` include any words that should be considered incorrect and flagged by the spell checking? If so, remove the words from the file.
   2. Does `custom-dicts/forbidden-words.txt` include any words that should be considered correct in your repository? If so, remove the words from the file.

4. Push all changes to your remote branch.

After these four steps, you're good to go and have 2 options:

1. Open a PR in your repository and let the workflow run an initial spell check. Then fix the misspelled words, or follow the guide in [What to do when CSpell flags a correct word](#what-to-do-when-cspell-flags-a-correct-word).
2. [Run the initial spell check locally](#run-the-spell-check-locally)

### Run the spell check locally

1. Run a spell check from your repository root:

   ```bash
   npx cspell -c .config/cspell/cspell-config.yml --dot --exclude ".git/**" .
   ```

> [!NOTE]
> The config file is not auto-discovered; you must use the `-c` option or change the config path to `.config/cspell.config.yaml` and update the workflow input.

2. Fix the misspelled words or follow the guide in the section [What to do when CSpell flags a correct word](#what-to-do-when-cspell-flags-a-correct-word) below.

## What to do when CSpell flags a correct word

If CSpell flags a word that you know is correct, **first** check whether it's already covered by a CSpell dictionary. **Do not** immediately add it to `custom-dicts/project-specific-words.txt`.

The flowchart below shows what to do in different scenarios. These map to specific subsections (found after the flowchart).

```mermaid
---
config:
  themeVariables:
    edgeLabelBackground: transparent
---
flowchart TD
    A([CSpell flags a word]) ==> B{Should the word<br/>be accepted?}

    B ==>|"`**No**`"| C[Fix the typo]
    B ==>|"`**Yes**`"| D["`Run **cspell trace**`"]

    D ==> E{"`Word found by **cspell trace**?`"}

    E ==>|"`**No**`"| I["`Search the </br> **cspell-dicts** repo`"]
    E ==>|"`**Yes**`"| F{"`Is that dictionary<br/>_enabled_?`"}

    F ==>|"`**No**`"| H[Enable the dictionary<br/>if relevant]
    F ==>|"`**Yes**`"| G[Check spelling,<br/>casing, and config]

    I ==> J{"`Word found in a dictionary in </br> **cspell-dicts** repo?`"}

    J ==>|"`**No**`"| N{"`Is the word a one-off occurrence?`"}
    J ==>|"`**Yes**`"| K{"`Is the dictionary<br/>_bundled_ with CSpell?`"}

    N ==>|"`**No**`"| M["`Add to a <br/> **custom-dict**`"]
    N ==>|"`**Yes**`"| O["`Disable occurrence <br/> with file comment`"]

    K ==>|"`**No**`"| L[Install and import<br/>the dictionary]
    K ==>|"`**Yes**`"| H

    classDef neutral fill:#f6f8fa,stroke:#57606a,color:#24292f,font-size:14px;
    classDef do fill:#ddf4ff,stroke:#0969da,color:#24292f,font-size:14px;
    classDef fallback fill:#ffebe9,stroke:#cf222e,color:#24292f,font-size:14px;

    class A,B,E,F,J,K,N neutral;
    class C,D,G,H,I,L,O do;
    class M fallback;
```

**Jump to:**

- [Run `cspell trace`](#run-cspell-trace)
- [Enable a dictionary](#enable-a-dictionary)
- [Search the `cspell-dicts` repo](#search-the-cspell-dicts-repo)
- [Install and import a dictionary](#install-and-import-a-dictionary)
- [Add word to a custom dictionary](#add-word-to-a-custom-dictionary-configcspellcustom-dicts)
- [Disable word occurrence with file comment (CSpell docs)](https://cspell.org/docs/Configuration/document-settings#enable--disable-checking-sections-of-code)

### Run `cspell trace`

Open a terminal window and run the following command in the repository root:

```bash
npx cspell trace --config .config/cspell/cspell-config.yml [YOUR-WORD]
```

The output is a table with the following headers (`Dictionary Location` column is excluded in examples because it is irrelevant in this case):

- `Word`: The word you searched for
- `F`: `*` if the word is found in the dictionary to the right, `-` if the word is not found
- `Dictionary`: Name of a dictionary that was searched. If there is a `*` next to the name, the dictionary is enabled in your configuration

#### Example outputs

1. `[YOUR-WORD]` was found in a dictionary that **is** enabled by your current CSpell configuration. CSpell should not be flagging `[YOUR-WORD]` as incorrect.

   ```bash
   Word        F   Dictionary
   [...]
   [YOUR-WORD] *   a-dict*         # [YOUR-WORD] was found in 'a-dict', and 'a-dict' is enabled
   [...]
   ```

   **What to do:** Check spelling, casing and config.

2. `[YOUR-WORD]` was found in a dictionary that is **not** enabled by your current CSpell configuration.

   ```bash
   Word         F   Dictionary
   [...]
   [YOUR-WORDS] *   another-dict   # [YOUR-WORD] was found in 'another-dict', but 'another-dict' is not enabled
   [...]
   ```

   **What to do:** [Enable the dictionary](#enable-a-dictionary) **if** a dictionary containing the word is relevant to your project.

3. `[YOUR-WORD]` was **not** found in any of the dictionaries _available_ in your current CSpell configuration.

   ```bash
   Word         F   Dictionary
   [...]
   [YOUR-WORDS] -   some-dict*         # 'some-dict' is enabled, but [YOUR-WORD] was not found in it
   [YOUR-WORDS] -   yet-another-dict   # 'yet-another-dict' is not enabled, and [YOUR-WORD] was not found in it
   [...]
   ```

   **What to do:** [Search the `cspell-dicts` repo](#search-the-cspell-dicts-repo) for a suitable dictionary.

### Enable a dictionary

Open your `.config/cspell/cspell-config.yml` file and add the dictionary to `dictionaries`, in alphabetical order.

Example:

```yml
dictionaries:
  - companies
  - cpp-compound-words
  - fonts
  - some-dict  # some-dict is now enabled in the cspell configuration
  [...]
```

### Search the `cspell-dicts` repo

If [`cspell trace`](#run-cspell-trace) doesn't find the word, search the [`cspell-dicts` repository](https://github.com/streetsidesoftware/cspell-dicts) to check whether the word exists in another CSpell dictionary.

In the GitHub search field, search for:

```text
repo:streetsidesoftware/cspell-dicts [YOUR-WORD]
```

**What to do with the result:**

- If the word is found in a file under `dictionaries/<dictionary-id>/dict/`, the word exists in a CSpell dictionary.
- Use the `<dictionary-id>` from the file path to find the dictionary in the `cspell-dicts` `README`.
- If the dictionary **is** marked as Bundled with CSpell, [enable it](#enable-a-dictionary).
- If the dictionary is **not** marked as `Bundled with CSpell`, [install and import the dictionary package](#install-and-import-a-dictionary).
- If the search has no relevant results, [add the word to a custom dictionary](#add-word-to-a-custom-dictionary-configcspellcustom-dicts).

### Install and import a dictionary

If you find a word in a relevant dictionary available in the `cspell-dicts` repository, first install and import it locally and [run `cspell trace`](#run-cspell-trace) to verify that the word is recognised by your updated CSpell configuration. When you have confirmed that it works as expected, install the dictionary in your workflow.

1. Install the dictionary locally:

   ```bash
   npm install --prefix .config/cspell --save-dev @cspell/dict-<dictionary-id>
   ```

   This will update `.config/cspell/node_modules/`, `.config/cspell/package.json`, and `.config/cspell/package-lock.json`.

   - Commit `package.json` and `package-lock.json` so the dictionary dependency is recorded.
   - Do not commit `node_modules/`; make sure `node_modules/` is listed in the repository root `.gitignore`.

2. Import the dictionary in your `.config/cspell/cspell-config.yml`

   ```yml
   # Example
   import:
     - "@cspell/dict-sv/cspell-ext.json"
     - "@cspell/dict-people-names/cspell-ext.json"
     - "@cspell/dict-<dictionary-id>/cspell-ext.json"
   ```

3. Use [`cspell trace`](#run-cspell-trace) to verify that the updated CSpell configuration recognises the word. We also recommend that you [run CSpell locally](#run-the-spell-check-locally) to verify that it no longer flags the word instead of pushing and letting GitHub Actions handle it for every single word.
4. Push the changes to your remote branch.
5. If you have an open PR, check the `Files changed`. There should **not** be an annotation for the correct word in the PR diff (`Files changed` tab).

#### How to remove a dictionary from the configuration

To undo the changes listed above, uninstall the dictionary package:

```bash
npm uninstall --prefix .config/cspell @cspell/dict-<dictionary-id>
```

Then also remove the dictionary import from `.config/cspell/cspell-config.yml`.

> [!WARNING]
> If you delete a dictionary file from `custom-dicts/` (see the "Add word to a custom dictionary" section below), you must also remove its entry from `dictionaryDefinitions` and `dictionaries`, otherwise CSpell fails on a missing dictionary path.

### Add word to a custom dictionary (`.config/cspell/custom-dicts/`)

The table below shows when to add a word to the different files under `custom-dicts`. Only add a word to one of the custom dictionaries if the word is correct, relevant to your repository / project, and it doesn't exist in an available CSpell dictionary.

| The word is...                                                  | Add it to                        |
| --------------------------------------------------------------- | -------------------------------- |
| an acronym                                                      | `approved-acronyms.txt`          |
| a person's or organisation's name                               | `approved-names.txt`             |
| used across the repository                                      | `project-specific-words.txt`     |
| only used/allowed in one directory, e.g. `<specific-directory>` | `<specific-directory>-words.txt` |

If a word **should** be flagged across all files, add it to `forbidden-words.txt`.

Add one word per line, in alphabetical order.

After adding the word, push the change and check that the PR annotation is gone.

## Notes and limitations

The standard English at the SciLifeLab Data Centre is British English, which is why this CSpell configuration uses `en-gb`.

This does not mean that CSpell will flag every US spelling. Some US spellings may still be accepted because they are included in `en-gb` or in other enabled dictionaries. If a non-British spelling should be avoided in this template but is not flagged by CSpell, add it to the `.config/cspell/custom-dicts/forbidden-words.txt` file.

Entries in `forbidden-words.txt` must start with !, and you need to add each capitalisation variant separately.

```text
!example
!Example
```
