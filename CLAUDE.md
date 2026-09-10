# mdslides

Converts Markdown into LaTeX Beamer slides. A lightweight alternative to
`pandoc -t beamer`, built on [marko](https://github.com/frostming/marko).

The guiding principle is **LaTeX passthrough**: whatever the Markdown parser
does not recognize is assumed to be LaTeX and emitted untouched, so any slide
can fall back to raw LaTeX. Escaping happens only inside `` `inline code` ``,
where the text is meant to be literal.

    mdslides deck.md -o deck.tex     # convert
    mdslides --pdf deck.md           # convert and build the PDF
    pytest                           # the suite; all of it should pass

Dependencies are in `requirements.txt`: `marko` and `PyYAML`, both hard
imports. `pytest` for the tests and a TeX installation for `--pdf` are noted
there too, as comments, so that installing the file does not drag them in.

## Files

| File | What it is |
|---|---|
| `mdslides` | the whole converter, one executable script, no `.py` suffix |
| `beamer.tex.tpl` | the Beamer preamble, external on purpose |
| `tests/conftest.py` | fixtures, and `EXAMPLE` — a presentation in miniature |
| `tests/test_mdslides.py` | the suite |
| `requirements.txt` | the two runtime dependencies |

Every commit message is deliberately detailed — `git log` is the fine-grained
record of *why* each thing is the way it is.

**There is no presentation in this repository.** The lecture this was written
for is content, not part of the converter, and lives in the author's teaching
repository. What stands in for it is `EXAMPLE` in `tests/conftest.py`: one
short document exercising every construct the renderer knows, which several
tests assert invariants over rather than checking fixed strings.

## Current state

The last full measurement, taken while the lecture was still committed here:
it converted to **40 pages, 0 LaTeX errors, 0 overfull frames**, and compared
page by page against pandoc's output from the same source, **21 of 23 pages
carried identical text** (see "Comparing against pandoc" below for how to
reproduce that).

## Input format

Documented nowhere else, so here it is in full.

**Slide structure.** A heading at `--slide-level` (default 1) starts a frame;
a heading above it becomes `\section`; a heading below it stays inside the
frame (currently `\textbf{...}\par`, see remaining work). A thematic break
`---` starts an untitled frame, as does any content before the first heading.
A leading `---` is metadata, not a break.

**Frame attributes.** `# Title {.fragile}` — recognized classes become frame
options; `{#id}` becomes `label=id`; `key=value` passes through. `[fragile]`
is added automatically to any frame containing verbatim material, so it is
rarely needed by hand.

**Section separator slides.** `{.section}` on a heading (also `{.subsection}`
and `{.part}`) opens that sectioning level:

    # Part II: Symbolic execution {.section}   ->  \section{Part II: ...}

It is a heading class rather than a slide level so that it drops into a deck
whose frames are all `#`, without demoting every heading to `##`. A heading
*above* the slide level is a section already; there the class only says which
level. Give the heading content and it becomes the slide *after* the
separator, so nothing written under it is dropped, and other classes still
apply to that slide (`{.section .plain}`).

The separator slide itself is **not** emitted next to the `\section`. It is
hooked onto the sectioning level in the preamble, by `$sectionpages`:

    \AtBeginSection[]{\frame[plain,noframenumbering]{\sectionpage}}

which is what lets `section-titles: false` switch every one of them off, and
gives one to a section made by a heading above the slide level too. `\...page`
follows the theme, so a deck wanting a different divider overrides
`\setbeamertemplate{section page}` from its `header-includes` — which also
wins outright, because `$sectionpages` comes before `$headerincludes`.
`[plain,noframenumbering]` is what a divider wants: no headline or footline,
and no slide number consumed. `\frame[...]{...}` rather than a `frame`
environment, so that no `\begin{frame}` appears in the preamble where
anything counting the deck's slides would find it.

The divider carries **the name alone**. Beamer's own `part`/`section`/
`subsection page` templates print `\sectionname~\insertsectionnumber` and a
`\vskip1em` above it — "Section 1" — and the template redefines all three
with that line dropped, keeping each theme's colours, fonts and box.

**`toc: true`** puts a table of contents after the title page, titled by
`toc-title` (default `Outline`). That one cannot be a template variable of
its own — a hyphen is not an identifier, so `string.Template` could never
reach `$toc-title`.

Do **not** write `\section{...}` as a line of raw LaTeX instead: everything at
the top level is wrapped into a frame, and a sectioning command has to sit
between frames, so it either becomes a frame of its own or is absorbed into
the one above it.

**Environments.** Two syntaxes, and the choice of syntax is what says how the
contents are treated:

    @theorem[Pumping lemma]        \begin{align}
    For every **regular** ...        x_1 &= y_2 \\
    @end                           \end{align}
    ^ contents are Markdown        ^ contents are LaTeX, untouched

That is why `@theorem` and `\begin{align}` both work without the tool knowing
either name, and why an environment of your own needs no registration.

Directive arguments are read from the first character: `<`, `[` or `{` means
the rest is LaTeX and is handed over exactly as written (overlays, optional
arguments, multi-argument signatures). Anything else is *friendly*: a bare
number is a fraction of `\textwidth` (`@column 0.3`), and a bare title is
parsed as Markdown (`@block Results **so far**`). The sugar tables
(`WIDTH_DIRECTIVES`, `BRACKET_TITLE_DIRECTIVES`) buy convenience only — an
unlisted environment still works, you just write the brackets yourself. They
do carry the one detail worth not remembering: `block`-likes take `{title}`,
`theorem`-likes take `[title]`.

Three things close a directive: `@end` (optionally naming what it closes, and
verified when it does), the same name again for `SIBLING_DIRECTIVES` so a row
of columns needs no `@end` between them, and a heading. `@end name` closes
anything still open inside it, as `</ul>` does in HTML. A stray `@end` is
reported on stderr and dropped. `COMMAND_DIRECTIVES` (`@note`, `@alert`, ...)
emit `\note{...}` rather than an environment.

**Images.** `![alt](f.png){width=0.8 clip}` → `\includegraphics`. A bare
number is a fraction of the slide; anything else is a length. Unknown keys and
bare flags pass through. An image alone in a paragraph *with* alt text becomes
a captioned figure; the caption is parsed as Markdown. The title
(`![](f.png "x")`) is dropped, as pandoc drops it.

**Code.** ```` ```C ```` → `lstlisting[language={C}]`; ```` ```lstlisting ````
means "this is listings input" and gets `escapechar=@` so `@$x_1$@` typesets
as maths (`--escapechar` changes it). Unknown languages become plain listings
rather than a LaTeX error.

**Maths** `$...$` and `$$...$$` are claimed before emphasis, which is what
keeps `$pc_1 \land pc_2$` intact.

**No percentages anywhere.** Widths are bare fractions or lengths. A `%`
reaching LaTeX comments out the rest of its line.

## Design decisions worth not re-deciding

1. **`string.Template` for the template, with `build_variables()` guaranteeing
   every variable.** It has no conditionals, so an absent variable cannot be
   skipped — an unsubstituted `$theme` would reach LaTeX and be read as maths.
   `TEMPLATE_DEFAULTS` covers a document with no metadata at all. **This is the
   main open decision**: wiring up the remaining optional preamble blocks
   (`toc`, hyperref, ...) is what a `$if()$`/`$for()$` engine would buy.
2. **`-V` is applied to the metadata before anything is derived from it**, so
   `-V title=X` also reaches the short title in the footline.
3. **`fontfamily` defaults to `lmodern`.** `palatino` only sets `\rmfamily`,
   which beamer never uses for slide text — it was a no-op that left the body
   in Nimbus Sans and the maths in Computer Modern.
4. **`escapechar` only for `lstlisting`-tagged fences**, since a C snippet is
   free to contain an `@`.
5. **`@columns` defaults to `[T]`.** Without it beamer centres columns against
   each other and a short column of code floats beside a tall table.

## Marko specifics

- Custom elements are registered in `markdown_extension()`; priority is what
  makes them win over the standard parsers (maths at 8-9, above emphasis).
- **The environment and the macro line are separate elements because they want
  opposite answers to `breaks_paragraph`.** A line-initial `\begin{...}` breaks
  a paragraph (the deck has a `tabularx` directly below a directive line with
  no blank line); a lone `\pausex` at column 0 must *not*, or the list it sits
  in is torn in two.
- `parse_one_block()` does one turn of marko's block loop. marko only offers
  `parse_source()`, which runs until nothing matches, and a container ending at
  a marker of its own cannot use that.
- `parse_group` accepts a **named** group, which is how `Graphic` claims a
  whole image while only the alt text becomes children.
- Options reach the renderer as class attributes of a throwaway subclass
  (`make_markdown()`), because marko instantiates the renderer itself.

## Traps already paid for

- **Marko's `Literal` eats one backslash from `\\`** if raw LaTeX gets
  swallowed into a paragraph, silently turning table row ends into `\`. This
  is the reason for decision 2 above under "Marko specifics".
- **`listings`: `Lua` has dialects but no default**, so `language=Lua` fails to
  load; it must be `[5.3]Lua`. And a `[dialect]language` value must be brace
  wrapped or it breaks the option parser. Every entry in `LISTINGS_LANGUAGES`
  was checked by compiling it.
- **`upquote` and `breaklines`** are not optional: without them `'B'` in a C
  listing becomes typographic quotes and long lines are clipped at the slide
  edge. There is a test asserting both are still in the template.
- **Do not redirect pdflatex's stdout to `<job>.out`** — that is hyperref's
  bookmark file, and clobbering it produces a baffling `Missing { inserted`.
- `grep -c` counts *lines*, not occurrences (this produced a phantom `\pausex`
  discrepancy).
- **The template's own comments contain the strings you search for.** This has
  produced three false results so far — a phantom `titlepage`, an
  `AtBeginSection` that was only being explained, and a `\sectionname` in the
  note saying why `\sectionname` is not used. Any assertion that something is
  *absent* from the template must go through `without_comments()` in the
  tests; the same care is needed when grepping by hand.
- The `opts` fixture must take `mdslides` as a parameter; without it the name
  resolves to nothing and ~120 tests fail at once.

## Verification

`pytest.ini` promotes deprecation warnings to errors. Beyond unit tests there
are three kinds of check worth keeping:

- **Compile tests** run `pdflatex`, on an inline document exercising every
  construct and on `EXAMPLE`. Skipped where pdflatex is absent, so the suite
  needs nothing but the standard library plus pytest. These caught a missing
  `\usepackage{listings}` that no unit test could see.
- **Invariants over `EXAMPLE`** rather than fixed strings: every maths span and
  the `tabularx` table appear verbatim in the output, every frame holding a
  listing is marked fragile, the frame count matches the number of `#`
  headings. Add to `EXAMPLE` when adding a construct, and these come along.
- **Reading the built PDF.** `pdftotext -layout` found three faults on the code
  slides that the tests were blind to. Rendering a page with `pdftoppm` and
  looking at it found a column-alignment bug.

## Comparing against pandoc

The reference lives outside this repo:

    ../../teaching/sav-private/97-Lectures-OLD/07-Symbolic-Execution/pandoc/

Its `symbolic-execution.md` is byte-identical to the lecture as first
committed here, which is still recoverable with

    git show 2d20d16:simplified.md

though note that version predates the `@` syntax. The version converted to
`@columns`/`@column` is `git show fad2063:simplified.md`, and the last one,
self-contained after the highlight macros moved into the template, is
`git show 3c59e82:simplified.md`.

To compare fairly: copy `macros.tex`, `stylesheet.tex`, `filter.py3` and
`klee.png` to a scratch directory alongside both sources, strip `\pausex` from
each with `sed` so every frame is one page, build one with
`pandoc --filter ./filter.py3 --wrap=none -t beamer -s` and the other with
`mdslides`, then compare `pdftotext -layout` page by page.

Two differences remain, neither a defect here: pandoc numbers the lines of the
algorithm listing (that is `numbers=left` in the `stylesheet.tex` the deck no
longer reads), and pandoc **drops** the final `etc.` bullet on "Symbolic
execution for verification" because its frame overflows by 12.78pt — ours fits
it, since `lstlisting` is more compact than pandoc's highlighted blocks.

Note the original pandoc source uses `::: {.column}` fenced divs and is **no
longer valid input** here — run it through and the fences come out as literal
text. The two syntaxes diverged deliberately.

## Remaining work

1. **The ignored metadata.** Eight keys parse and are then discarded:
   `colorlinks`, `linkcolor`, `urlcolor`, `filecolor` and `linkstyle` (the
   template loads no `hyperref` at all), `titlegraphic`, `logo`, and `topic`
   (which pandoc ignores too). `toc` and `section-titles` used to be on this
   list and are done; `$titlepage`, `$sectionpages` and `$toc` are the
   precedent for the rest — computed in Python and injected whole, which is
   how `string.Template` gets away with having no conditionals.
2. **`##` → `\begin{block}{...}`** — the one `TODO` in the code. Needs grouping
   a heading with its following siblings, since Markdown gives no nesting.
3. **Pipe tables.** No `render_table` at all; a GFM table falls through to raw
   text. Marko's GFM elements would supply the parsing.
4. **Syntax highlighting for code**, the last visual gap against pandoc, which
   colours keywords via pygments where ours is monochrome.
5. **Smart quotes.** An ASCII `"` becomes a typographic quote in pandoc and a
   literal one here, so `"easily"` comes out with two closing quotes. Belongs
   behind a flag, since rewriting the author's characters cuts against the
   passthrough rule.
6. **A README.** The input format above is the only documentation there is,
   and it is in a file aimed at whoever picks the work up rather than at
   whoever wants to use the tool. Also `strikethrough` and footnotes, which
   marko's GFM elements would make cheap.

## Conventions

- Branch is `master`. Commit messages explain *why*, and record what was
  deliberately left undone.
- Code style follows the original script: `####` separators between functions,
  docstrings in the `name(args) -> type` form, single quotes, 79 columns.
- Tests accompany the code in the same commit. One commit here failed that and
  had to be followed by "Test the renderer" — don't repeat it.
