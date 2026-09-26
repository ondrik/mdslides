# TODO

Everything known to be missing, wrong, or undecided. `CLAUDE.md` describes
what the tool *does*; this is what it does not.

Nothing here is urgent — the converter builds a real deck with no LaTeX
errors. The ordering within each group is roughly by how much it buys.

## Defects

Everything from here to the `short-title` entry was found by auditing the
documentation against the source, and none of it was known before. The first
two produce wrong output with no warning at all.

**`$$...$$` corrupts the next `$...$` in the same paragraph.** `A $$y$$ then
$a _b_ c$` renders as `\[y\] then $a \emph{b} c$`. `Math.pattern` cannot match
the `$$` opener, so `finditer` matches from its *second* `$`, producing a
bogus token that intersects the `MathDisplay` one; `_resolve_overlap` drops
the bogus token, but the region is already consumed and the real inline maths
never gets one. Invisible when the inline maths holds no Markdown-active
character. Putting the display in a paragraph of its own avoids it.

**A failed conversion leaves an empty output file.** `parse_args` opens the
output for writing, which truncates it, before anything is read -- so a deck
that fails to convert replaces the previous `.tex` with nothing. Writing to a
temporary file and renaming it on success is the fix. (The worst case, `-o`
naming the input, is refused now.)

**`\(x\)` and `\[y\]` lose their backslashes**, rendering as `(x)` and `[y]`.
The brackets are ASCII punctuation, so marko's `Literal` claims them, and
`render_literal` re-emits the backslash only for `LATEX_SPECIALS`. Only the
`$` spellings work -- which bites hardest because `mdslides` *emits* `\[...\]`,
so copying its own output back into a source breaks silently.

**An unterminated `\begin{env}` swallows the rest of the file.**
`RawLatexEnvironment.parse()` loops to the end of the source with no heading
or frame boundary, unlike a directive, which any heading closes. A three-frame
deck comes out as one frame with the later headings in it as literal text.

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

**Per-slide metadata, and what starts a slide.** Nothing can be said about one
slide except through its heading: `{.fragile}`, `{#id}` and `key=value` on the
heading line, and that is all. Two things have no way in. A setting that is
not a frame option — the `\itemsep` of the lists on one slide, say — has
nowhere to go; and *no* setting at all can reach a frame that has no heading,
since one started by `---`, or by the text before the first heading, has no
attribute list to carry it.

The proposal is to let a slide carry a metadata block of its own, and to tell
it from a thematic break exactly as the document's own block is told from one:
**by a closing fence.**

    ---
    title: Why the path condition only ever grows
    label: growth
    itemsep: 1.2em
    options: [t]
    ---

    * every branch conjoins a constraint
    * nothing ever removes one

`FRONTMATTER_RE` already requires that closer, which is why a lone `---` at
the top of a file is a break and a closed one is metadata. Per slide the same
rule reads: a `---` starts a slide; if what follows parses as YAML and is
closed by `---` or `...`, it is that slide's metadata; otherwise the `---` was
a break and nothing more.

The heading stays, as sugar for the commonest field:

    # Why it grows {#growth}    ==    ---
                                      title: Why it grows
                                      label: growth
                                      ---

which is the shape the `@` directives already have — `@column 0.3` is sugar
for `@column{0.3\textwidth}`, `@block Results` for `@block{Results}`. Most
slides are a title and five bullets and should go on being written that way;
the block is what you reach for when the sugar runs out. One model with a
shorthand, not two syntaxes competing.

The spelling is free. Today a `---`, two `key: value` lines and a `---` parse
as a thematic break followed by a setext heading, and come out as
`\textbf{title: Two itemsep: 1em}\par` — nonsense no deck can be relying on.

Three alternatives, considered and set aside, recorded so they are not
proposed again. `%!` pragma lines (`%! itemsep: 1em`) are mechanically the
safest of the four, since `strip_comments()` already drops them before marko
runs, so they cannot interact with paragraphs or lists at all; they lose
because they read as comments rather than as metadata, and because a title
does not belong in one. A `+++` fence buys nothing over `---` and costs a
second marker. Extending the heading's `{...}` further never reaches an
untitled frame, which is half the problem.

**Two decisions it forces.**

*Is a slide's `title:` parsed as Markdown?* Frame titles are today —
`# Why $x_1$ matters` and `# **This** one` both work — while metadata values
deliberately are not. A `title:` key that stands in for a heading has to pick
a side, and picking "not parsed" means every deck that moves a heading into a
block silently loses its maths and its emphasis. It is the same question as
"Markdown in metadata values" below, and the two have to answer it the same
way.

*The deck stops being plain Markdown.* Anywhere else — GitHub, an editor
preview — a per-slide block shows up as a rule and a line of stray text,
where a heading renders as a heading. That is the real price.

**Where it would go.** Pre-parse, beside `split_frontmatter()` and
`strip_comments()`, not as a marko block element: every scar in this codebase
comes from a new block construct interacting with paragraphs and lists — the
HTML comment that splits a list, the `\begin{...}` that has to break a
paragraph while `\pausex` must not. `split_slides()` would then consume a
list of (metadata, blocks) groups rather than deriving everything from heading
level, with the heading filling in `title` when no block gave one. The cost is
the line numbers shifting, which `strip_comments()` already does and nothing
reports on yet.

**What works today, meanwhile.** `\tightlist` is emitted inside every tight
list and `\begin{frame}` is a group, so a slide can already set its own
spacing without any of this:

    # Results

    \renewcommand{\tightlist}{\setlength{\itemsep}{1.5em}}

    * alpha
    * beta

Measured on the built PDF, that is 13.55pt between baselines without the line
and 29.91pt with it, back to 13.55pt on the next slide. A plain
`\setlength{\itemsep}{1.5em}` before the list does nothing, since `itemize`
resets it on entry. Only tight lists carry the hook — a loose one stays at
beamer's own 16.54pt.

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
