# Handoff

A snapshot for picking this up elsewhere, written 17 September 2026 at commit
`c6b68bc`. It records what the other two documents deliberately do not:

- **`CLAUDE.md`** — what the tool does, how it is built, and why. Read it first;
  Claude Code loads it automatically.
- **`TODO.md`** — what is missing, wrong, or undecided.
- **this file** — where things stand, what lives outside the repository, and
  what has already been decided against.

Everything of substance is in the repository and pushed. There is no work in
progress and nothing uncommitted.

## Where to pick it up

    git clone git@github.com:ondrik/mdslides.git
    cd mdslides
    pip install -r requirements.txt
    pytest                      # 377 tests, all passing at c6b68bc
    ./mdslides --pdf deck.md    # needs a TeX installation

Branch is `master`, 38 commits, level with `origin/master`.

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

marko is the one to watch: the converter registers custom block and inline
elements against its parser internals, and `parse_one_block()` reimplements
one turn of its block loop. A marko upgrade is the change most likely to
break something quietly, so run the suite after one.

## What lives outside the repository

There is **no presentation in the repository** — the lecture it was written
for is content, not part of the converter. `EXAMPLE` in `tests/conftest.py`
stands in for one and is what the invariant tests run against.

The deck can be recovered from history if it is wanted:

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

`klee.png`, an image the old deck referenced, was removed along with it.

## Already decided against

Recorded so they are not proposed again. None of these is an oversight.

- **`%%` as a second comment syntax**, for notes that never reach the `.tex`.
  Proposed and declined — `%` on a line of its own already does exactly that.
- **A standalone document about section separator slides.** Started, then
  superseded: `{.section}` made the instructions unnecessary, and the syntax is
  documented in `CLAUDE.md` with the rest of the input format.
- **Pandoc's `beamer-template.tex` kept in the repository.** It was there at
  the start, deliberately never committed, and has since been deleted.
- **Fenced divs (`::: {.column}`) for environments.** Rejected in favour of the
  `@` directives after discussion; the reasoning is in `CLAUDE.md` under design
  decisions and in commit `3746e12`. The original pandoc source is no longer
  valid input as a result, which was the accepted cost.

## Two habits worth keeping

**Read the built PDF, not just the `.tex`.** `pdftotext -layout` found three
faults on the code slides that no unit test could see, and rendering a page
with `pdftoppm` and looking at it found a column misalignment and a footline
that had gone blue on blue. Several bugs in this repository were invisible
until someone looked at the output.

**Check that a fix did not corrupt what it fixed.** Escaping a URL can make a
document compile while breaking the link; the test for that pulled the `/URI`
back out of the PDF and compared it with the source. "It compiles" is weaker
evidence than it looks.
