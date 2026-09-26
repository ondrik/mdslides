# Handoff

A snapshot for picking this up elsewhere, written 17 September 2026 and
refreshed on 26 September 2026 at commit `cca0e6d`. It records what the other
three documents deliberately do not:

- **`README.md`** — how to install it, how to use it, and the input format in
  full, for whoever wants to use the tool. The front door, and the most
  recently checked of the four.
- **`CLAUDE.md`** — how it is built, and why. Claude Code loads it
  automatically.
- **`TODO.md`** — what is missing, wrong, or undecided.
- **this file** — where things stand, what lives outside the repository, and
  what has already been decided against.

Everything of substance is in the repository and pushed. There is no work in
progress and nothing uncommitted.

## Where to pick it up

    git clone git@github.com:ondrik/mdslides.git
    cd mdslides
    pytest                      # the suite; all of it should pass

Installing the two dependencies, the PEP 668 `externally-managed-environment`
refusal that stops `pip install -r requirements.txt` on Debian and Ubuntu,
putting the script on your `PATH`, and building a PDF are all in `README.md`.

Branch is `master`, level with `origin/master`.

`git log` is the detailed record — the commit messages explain why each thing
is the way it is, and several record what was deliberately left undone. When
something looks arbitrary, the commit that introduced it probably says why.

## What this was built on

| | version |
|---|---|
| Python | 3.14.7 (syntax checked back to 3.9) |
| marko | 2.2.3 |
| PyYAML | 6.0.3 |
| pytest | 9.1.1 |
| pandoc | 3.11 (only for comparison, never a dependency) |
| TeX | TeX Live 2026, pdfTeX 1.40.29 |

marko is the row to watch — `README.md`, "Developing", says why — so run the
suite after upgrading it.

## What lives outside the repository

The deck is not in the repository — `README.md` and `CLAUDE.md` both say why,
and what `EXAMPLE` in `tests/conftest.py` does in its place. It can still be
recovered from history if it is wanted:

    git show 2d20d16:simplified.md    # as first committed, before the @ syntax
    git show fad2063:simplified.md    # converted to @columns/@column
    git show 3c59e82:simplified.md    # self-contained, the last version here

Two things are referenced but not present. Both sit in the author's teaching
repository, wherever that is checked out, so no path to them belongs here:

- **The pandoc reference build** of the symbolic execution lecture — the same
  Markdown, its `macros.tex`, `stylesheet.tex` and `filter.py3`, and the PDF
  built from them. It is what the comparison in `CLAUDE.md` is run against.
  Nothing depends on it, and on another machine it will simply be absent.
- **A second deck, converted from prosper** (there is a `prosper2beamer.py`
  beside it), which is what prompted the section separator slides. It has
  never been run through this converter and may well use constructs it has
  not met. Converting and compiling it is the obvious next real test.

## Already decided against

Recorded so they are not proposed again. None of these is an oversight.

- **`%%` as a second comment syntax**, for notes that never reach the `.tex`.
  Proposed and declined — `%` on a line of its own already does exactly that.
- **A standalone document about section separator slides.** Started, then
  superseded: `{.section}` made the instructions unnecessary, and the syntax is
  documented in `README.md` with the rest of the input format.
- **Pandoc's `beamer-template.tex` kept in the repository.** It was there at
  the start, deliberately never committed, and has since been deleted.
- **Fenced divs (`::: {.column}`) for environments.** Rejected in favour of
  the `@` directives after discussion; commit `3746e12` has the argument in
  full, and `CLAUDE.md` keeps the half that survives as design — the syntax is
  what says whether the contents are Markdown or LaTeX, so no
  name-to-environment table is needed. The original pandoc source is no longer
  valid input as a result, which was the accepted cost (`README.md`, "Coming
  from pandoc").

## A habit worth keeping

**Check that a fix did not corrupt what it fixed.** Escaping a URL can make a
document compile while breaking the link; the check for that pulled the `/URI`
back out of the built PDF and compared it with the source — by hand, at
`c6b68bc`. The suite only ever sees the `.tex`, and the compile test would
pass a link corrupted into something that still typesets. "It compiles" is
weaker evidence than it looks.

Reading the built PDF is the other half of that, and is in `CLAUDE.md` under
"Verification".
