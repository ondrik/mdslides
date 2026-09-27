# mdslides

Converts Markdown into LaTeX Beamer slides. A lightweight alternative to
`pandoc -t beamer`, built on [marko](https://github.com/frostming/marko).

The guiding principle is **LaTeX passthrough**: whatever the Markdown parser
does not recognize is assumed to be LaTeX and emitted untouched, so any slide
can fall back to raw LaTeX. Escaping happens in two places only: inside
`` `inline code` ``, where the text is meant to be literal, and in a link
destination, where LaTeX would read a `#` as a parameter and a `%` as a
comment. A code span is not inviolable even so — maths and raw LaTeX are
claimed ahead of it, so `` `$x$` `` and `` `\ldots` `` keep their backticks
and escape nothing.

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
| `tests/conftest.py` | fixtures, and `EXAMPLE` — the presentation in miniature that stands in for the lecture, which is not in this repository |
| `tests/test_mdslides.py` | the suite |
| `requirements.txt` | the two runtime dependencies |
| `pytest.ini` | testpaths, and deprecation warnings promoted to errors |
| `README.md` | how to install it, how to use it, and the input format in full |
| `TODO.md` | what is missing, wrong, or undecided |
| `HANDOFF.md` | where things stand, and what lives outside the repository |
| `LICENSE` | MIT |

## Current state

The last full measurement, taken while the lecture was still committed here:
it converted to **40 pages, 0 LaTeX errors, 0 overfull frames**, and compared
page by page against pandoc's output from the same source, **21 of 23 pages
carried identical text** (see "Comparing against pandoc" below for how to
reproduce that).

## Input format

Written out for the deck author in [`README.md`](README.md), under "Writing a
deck", where every construct is documented and every example was run against
the code. This section used to hold that account and no longer does: one
description of the format, not two that drift apart.

What the README does not say is which names implement it. The tables are all
near the top of `mdslides`:

| Constant | What it decides |
|---|---|
| `FRAME_OPTIONS` | which `{.class}` on a heading becomes a frame option |
| `SECTIONING_CLASSES` | `{.section}`, `{.subsection}`, `{.part}` |
| `WIDTH_DIRECTIVES` | which directives read a bare number as a width |
| `BRACKET_TITLE_DIRECTIVES` | which take `[title]` rather than `{title}` |
| `SIBLING_DIRECTIVES` | which close a previous one of the same name |
| `COMMAND_DIRECTIVES` | which emit `\name{...}` instead of an environment |
| `DIRECTIVE_DEFAULT_ARGUMENTS` | `@columns` without arguments |
| `LISTINGS_LANGUAGES` | fence word to `listings` language |
| `LATEX_ESCAPES`, `URL_ESCAPES` | the two escape tables |
| `TEMPLATE_DEFAULTS`, `FLAG_VARIABLES` | what every template variable falls back to |
| `SLIDE_METADATA_KEYS` | what a slide's own `---` block understands |
| `MARKDOWN_METADATA` | which metadata values are parsed as Markdown |

The sugar tables buy convenience only — an unregistered environment still
works, you just write the brackets yourself. They carry the one detail worth
not remembering: `block`-likes take `{title}`, `theorem`-likes take `[title]`.

Two properties of the format are worth stating here because they are design,
not usage, and the rest of this file assumes them:

**The syntax is what says how the contents are treated.** `@theorem ... @end`
holds Markdown; `\begin{align} ... \end{align}` holds LaTeX and is emitted
untouched. That is why both work without the tool knowing either name, and why
no name-to-environment table is needed.

**A slide is declared, not only headed.** A heading is sugar for a metadata
block's `title:`, the way `@column 0.3` is sugar for `@column{0.3\textwidth}`.
`SlideMetadata` is an ordinary block element at priority 9, above
`ThematicBreak`.

**The opener is `===` and the closer `---`, and that asymmetry is the whole
point.** The first cut used `---` for both, and two thematic breaks with a
slide between them have exactly that shape — so it ate the slide between
every pair of breaks in the deck, silently, since a heading between them is a
YAML comment. Telling the two apart needed guesswork about the content. With
`===` the opening line settles it, and a pair of breaks cannot be a block at
all.

The guards that guesswork needed are kept, because prose can still sit under
a `===`: `match()` refuses anything but the top level (`Source.expect_re`
matches the raw buffer, and inside a container the lines still carry its
prefix), the content may hold no blank line and no code fence, and
`load_slide_metadata()` parses the YAML *before* the block is claimed, taking
it only when it is a mapping naming a key in `SLIDE_METADATA_KEYS`. A setext
heading still wins over all of it, because marko resolves that while parsing
the paragraph above, before any element of ours is asked.

**Directive arguments are read from the first character.** `<`, `[` or `{`
means the rest is LaTeX and is handed over exactly as written; anything else
is *friendly* and interpreted — a bare number as a fraction of `\textwidth`,
a bare title as Markdown.

## Design decisions worth not re-deciding

1. **`string.Template` for the template, with `build_variables()` guaranteeing
   every variable.** It has no conditionals, so an absent variable cannot be
   skipped — an unsubstituted `$theme` would reach LaTeX and be read as maths.
   `TEMPLATE_DEFAULTS` covers a document with no metadata at all. What a
   `$if()$`/`$for()$` engine would still buy is now small — `titlegraphic`
   and `logo`, the last of the ignored keys — since `$titlepage`,
   `$sectionpages`, `$toc` and `$handout` are computed in Python already, and
   hyperref's global `colorlinks` was rejected rather than deferred. The
   question is kept open in `TODO.md`, "The template engine".
2. **`-V` is applied to the metadata before anything is derived from it**, so
   `-V title=X` also reaches the short title in the footline.
3. **`fontfamily` defaults to `lmodern`.** `palatino` only sets `\rmfamily`,
   which beamer never uses for slide text — it was a no-op that left the body
   in Nimbus Sans and the maths in Computer Modern.
4. **`escapechar` only for `lstlisting`-tagged fences**, since a C snippet is
   free to contain an `@`.
5. **`@columns` defaults to `[T]`.** Without it beamer centres columns against
   each other and a short column of code floats beside a tall table. This is
   the one decision here with no comment beside it in the source —
   `DIRECTIVE_DEFAULT_ARGUMENTS` is bare.
6. **`{.section}` is a heading class, not a slide level.** So it drops into a
   deck whose frames are all `#` without demoting every heading to `##`. A
   heading above the slide level is a section already; there the class only
   says which level. The separator slide is hooked onto the sectioning level
   in the preamble rather than emitted beside the `\section`, which is what
   lets `section-titles: false` switch every one of them off at once, and
   what gives one to a section made by a heading above the slide level too.
   Commented at `mdslides` (`SECTION_PAGE_HOOKS`) and `beamer.tex.tpl`.
7. **`handout: true` empties `\xpause`, and with it `\pausex`.** It replaces
   the `% \newcommand{\xpause}[0]{}` that used to sit commented out in the
   template and be uncommented by hand. Overlay specifications written out in
   LaTeX (`<2->`) are untouched by it — beamer's own `classoption: handout`
   is the blunter instrument for those.

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
  resolves to the fixture object the decorator left behind rather than to the
  module, and most of the suite fails at once with `AttributeError:
  'FixtureFunctionDefinition' object has no attribute 'LISTINGS_ESCAPECHAR'`.

## Verification

`pytest.ini` promotes deprecation warnings to errors. Beyond unit tests there
are three kinds of check worth keeping:

- **Compile tests** run `pdflatex`, on an inline document exercising every
  construct and on `EXAMPLE`. Skipped where pdflatex is absent, so the suite
  needs no TeX at all: beyond the converter's own `marko` and `PyYAML` it
  wants nothing but the standard library and pytest. These caught a missing
  `\usepackage{listings}` that no unit test could see.
- **Invariants over `EXAMPLE`** rather than fixed strings: every maths span and
  the `tabularx` table appear verbatim in the output, every frame holding a
  listing is marked fragile, and the frame count matches the number of `#`
  headings, less the ones that only open a section, plus the slides declared
  by a metadata block of their own. Add to `EXAMPLE` when adding a construct,
  and these come along.
- **Reading the built PDF.** `pdftotext -layout` found three faults on the code
  slides that the tests were blind to; rendering a page with `pdftoppm` and
  looking at it found a column misalignment and a footline that had gone blue
  on blue. Several bugs here were invisible until someone looked at the
  output.

## Comparing against pandoc

The reference is the pandoc build of the same lecture. `HANDOFF.md` says
where that, and the deck's own source, live — neither is in this repository,
and the comparison therefore cannot be rerun from a fresh clone.

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
text, `%` and all. The two syntaxes diverged deliberately; commit `3746e12`
has the argument.

## Remaining work

`TODO.md` — everything known to be missing, wrong, or undecided, kept there
rather than here so there is one list and not two that drift apart. The one
worth knowing before touching the preamble: `string.Template` has no
conditionals, so an optional block is computed in Python and injected whole,
the way `$titlepage`, `$sectionpages` and `$toc` are.

## Conventions

- Branch is `master`. Commit messages explain *why*, and record what was
  deliberately left undone.
- Code style follows the original script: `####` separators between functions,
  docstrings in the `name(args) -> type` form, single quotes, 79 columns.
- Tests accompany the code in the same commit. One commit here failed that and
  had to be followed by "Test the renderer" — don't repeat it.
