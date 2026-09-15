# TODO

Everything known to be missing, wrong, or undecided. `CLAUDE.md` describes
what the tool *does*; this is what it does not.

Nothing here is urgent — the converter builds a real deck with no LaTeX
errors. The ordering within each group is roughly by how much it buys.

## Defects

**`short-title` inherits a multi-line title.** `title: 'A\\B'` renders
correctly on the title slide but also sets `\title[A\\B]`, and beamer
swallows the break in the footline, printing `AB`. Deriving the short form by
turning `\\` into a space would fix it. An explicit `short-title` is the
workaround. *(Small, self-contained, and the fix is obvious — a good first
thing to pick up.)*

**A comment at column 0 between list items splits the list in two.** An HTML
block interrupts a list the way any other block would, so

    * one
    <!-- note -->
    * two

produces two `itemize` blocks. Indenting the comment avoids it. Whether this
is worth fixing is a judgement call: it follows from how block elements work,
and the fix would mean treating HTML comments as not-a-block. The behaviour is
pinned by a test named after the fact that it is documented rather than
desired, so fixing it will fail that test and prompt updating the document.

## Features not built

**The ignored metadata.** Five keys parse and are then discarded:

| Key | What it would take |
|---|---|
| `filecolor`, `citecolor` | nothing is emitted that would use them — no file or citation links |
| `linkstyle` | pandoc's bold/underline link styling, which has no equivalent here |
| `titlegraphic`, `logo` | a `\titlegraphic`/`\logo` line, guarded |

`topic` was on this list and is off it: pandoc ignores it too, so there is
nothing to do. `colorlinks`, `urlcolor` and `linkcolor` are honoured now, as
are `toc` and `section-titles`.

`$titlepage`, `$sectionpages` and `$toc` are the precedent for whatever is
left: computed in Python and injected whole, which is how `string.Template`
gets away with having no conditionals. This was the biggest hole when it was
ten keys; what remains is small and mostly not worth doing.

**`##` → `\begin{block}{...}`** — the one `TODO` left in the code
(`render_heading`). A heading below the slide level currently renders as
`\textbf{...}\par`. Needs grouping a heading with its following siblings,
since Markdown gives no nesting.

**Pipe tables.** No `render_table` at all, so a GFM table falls through to raw
text. Marko's GFM elements supply the parsing; the work is the LaTeX side —
column specifications, alignment, and deciding between `tabular` and
`tabularx`. A deck can write `\begin{tabularx}` by hand meanwhile, which is
what the example does.

**Syntax highlighting.** The last visual gap against pandoc, which colours
keywords via pygments where ours is monochrome with bold keywords. The cheap
version is a richer `\lstset` in the template (keyword, comment and string
styles); the faithful version is per-language styling.

**Smart quotes.** An ASCII `"` becomes a typographic quote in pandoc and a
literal one here, so `"easily"` comes out with two closing quotes. Belongs
behind a flag rather than on by default, since rewriting the author's
characters cuts against the passthrough rule.

**`strikethrough` and footnotes.** Marko's GFM elements would make both cheap.

## Open questions

**The template engine.** `string.Template` has no conditionals, so every
optional preamble block has to be computed in Python and injected whole. That
has been fine three times over (`$titlepage`, `$sectionpages`, `$toc`) and the
pattern is clear. What is left that would want conditionals is small — the
keys above — so the pressure that would have forced this decision has largely
gone. Worth deciding on its merits rather than under duress: a small
`$if()$`/`$for()$` engine would make pandoc's own Beamer template usable
directly, which is why a copy of it used to sit in this repository.

**Markdown in metadata values.** `title: '**Lecture 7**'` emits literal
asterisks today, because metadata reaches the template as it stands. Parsing
title, subtitle, author and institute as inline Markdown would fix that, and
would match what directive titles (`@block Results **so far**`) and image
captions already do — so it is a consistency gap rather than a new feature.
LaTeX in those values keeps working either way, since that is what passthrough
means. The risk is that an underscore in a title would become emphasis.

**Tight versus loose lists.** Ours marks 60 of 72 lists tight where pandoc
marks 66 of 71, so a few lists are set looser than pandoc sets them. Ours
follows CommonMark (a list is loose if its items are separated by blank lines);
pandoc is more permissive. Probably correct as it stands, but it is the one
measured difference in the comparison that was never chased down.

## Documentation

**A README.** The input format is documented only in `CLAUDE.md`, which is
aimed at whoever picks the work up rather than at whoever wants to use the
tool. The `@` directive syntax and the metadata keys are what it needs to
cover.

**The hand-made title slide.** `titlepage: false` plus a frame written in the
body gives complete control over the title slide, for anything beamer's own
title page cannot express. This works today and is written down nowhere.
