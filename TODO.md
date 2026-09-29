# TODO

Everything known to be missing, wrong, or undecided. `CLAUDE.md` describes
what the tool *does*; this is what it does not.

Nothing here is urgent — the converter builds a real deck with no LaTeX
errors. The ordering within each group is roughly by how much it buys.

## Defects

Everything from here to the `short-title` entry was found by auditing the
documentation against the source, and none of it was known before.

**A `---` break does not close a directive.** It is swallowed into the
environment and set as `\medskip\hrule\medskip`, the untitled frame it should
have started never appears, and what follows lands inside the environment too.

**`COMMAND_DIRECTIVES` discard their argument.** `render_directive` computes
`arguments` and then does not use it on that branch, so `@note remember this`
loses "remember this" and `@alert[opt]` loses the `[opt]`; only the overlay
survives. Silent.

**`@end name` closes whatever is open and then misreports it.** The name only
decides whether the line is consumed, never whether the directive closes, so
`@end lemma` closes an open `@theorem` exactly as a bare `@end` would. The
orphaned line then reaches the top level and is reported as `'@end lemma' with
nothing open` -- which is the opposite of what happened. Exit status stays 0.

**`-V slides=...` replaces the entire body of the deck**, and
`-V classoptions=...` replaces the computed `\documentclass` options. The four
`FLAG_VARIABLES` are the only computed names protected from the second `-V`
pass. Guarding `slides` and `classoptions` too would cost nothing.

**`aspectratio: 16:9` is YAML for the number 969.** It produces a 2902pt-wide
slide with no error whatsoever; `'16:9'` quoted fails inside beamer with
`Missing = inserted for \ifnum`. Beamer's spelling is `169`. Nothing validates
the value.

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

**`strikethrough` and footnotes.** Marko's GFM elements would make both cheap.

## Open questions

**Per-slide metadata** is built, and so is **Markdown in metadata values**;
both entries have left this file. They had to be decided together, since a
slide's `title:` and the document's had to answer the same way, and they do:
the keys that become prose on a slide are parsed as Markdown, and everything
else reaches the template as YAML read it. `README.md` documents both, under
"A slide's own metadata" and "The metadata block".

Three things were learned in the building that are worth keeping here.

*The block form is not pre-parsed*, against the advice this entry used to
give. It is an ordinary marko block element at priority 9, above
`ThematicBreak`, which claims the `---` only when a closing fence follows. A
`---` is already a block boundary, so nothing new interacts with paragraphs
or lists, and the scars that argued for a pre-pass do not apply here.

*A setext heading still wins.* A block directly below a paragraph is
CommonMark's `---` underline, and marko resolves that while parsing the
paragraph, before any element of ours is asked. So a block wants a blank line
above it. That is the same trap a thematic break already has, and it errs
toward leaving old decks alone.

*The underscore risk was overstated.* This entry used to say that parsing
metadata as Markdown risks an underscore in a title becoming emphasis.
CommonMark has no intraword `_` emphasis, so `a_b_c` survives whole; only a
delimited ` _b_ ` is emphasis, exactly as in a heading. What is genuinely at
risk is a *block*-shaped value, `1. Introduction` being the realistic one, so
a value is parsed only when it parses as a single paragraph and is otherwise
passed through as it always was.

**The template engine.** `string.Template` has no conditionals, so every
optional preamble block has to be computed in Python and injected whole. That
has been fine three times over (`$titlepage`, `$sectionpages`, `$toc`) and the
pattern is clear. What is left that would want conditionals is small — the
keys above — so the pressure that would have forced this decision has largely
gone. Worth deciding on its merits rather than under duress: a small
`$if()$`/`$for()$` engine would make pandoc's own Beamer template usable
directly, which is why a copy of it used to sit in this repository.

**Tight versus loose lists.** Ours marks 60 of 72 lists tight where pandoc
marks 66 of 71, so a few lists are set looser than pandoc sets them. Ours
follows CommonMark (a list is loose if its items are separated by blank lines);
pandoc is more permissive. Probably correct as it stands, but it is the one
measured difference in the comparison that was never chased down.

## Documentation

**Both items here are done.** `README.md` documents the input format for
whoever wants to *use* the tool, where `CLAUDE.md` addresses whoever picks the
work up — the `@` directive syntax and the metadata keys included, and with
them the hand-made title slide (`titlepage: false` plus a frame written in the
body), which worked and was written down nowhere.

What is left is keeping the two in step. `CLAUDE.md` is the older document and
is wrong in a few places the README had to get right: the `@end` that names
something is *not* verified, a leading `---` is metadata only when a closing
fence follows, and a code span is not inviolable — `$...$` and `\macro` are
claimed ahead of it. Those corrections belong in `CLAUDE.md` too.
