# mdslides

Turns Markdown into LaTeX Beamer slides. A lightweight alternative to
`pandoc -t beamer`, built on [marko](https://github.com/frostming/marko).

```console
$ mdslides deck.md -o deck.tex     # convert
$ mdslides --pdf deck.md           # convert, and build the PDF
```

The guiding principle is **LaTeX passthrough**: whatever the Markdown parser
does not recognize is assumed to be LaTeX and emitted untouched. That is why a
slide can always fall back to raw LaTeX, why `\begin{align}` and `@theorem`
both work without the tool knowing either name, and why you can write
`$pc_1 \land pc_2$` in the middle of a bullet and get exactly that back.

```markdown
---
title: 'Symbolic Execution'
subtitle: 'SAV --- Static Analysis and Verification'
author: 'Ondřej Lengál'
toc: true
theme: Madrid
---

# What it does

* executes a program on **symbolic** inputs
* builds a path condition $pc_1 \land pc_2$

@theorem[Pumping lemma]
For every *regular* language $L$ there is an $n$.
@end
```

becomes a title page, a table of contents, and

```latex
\begin{frame}{What it does}
\begin{itemize}
\tightlist
\item executes a program on \textbf{symbolic} inputs
\item builds a path condition $pc_1 \land pc_2$
\end{itemize}
\begin{theorem}[Pumping lemma]
For every \emph{regular} language $L$ there is an $n$.
\end{theorem}
\end{frame}
```


## Installing

There is no package: `mdslides` is one executable script that reads one
template file sitting beside it.

```console
$ git clone https://github.com/ondrik/mdslides.git
$ cd mdslides
$ pip install -r requirements.txt
$ ./mdslides deck.md -o deck.tex
```

The two runtime dependencies are `marko` (>= 2.2) and `PyYAML` (>= 6.0), both
hard imports — without them the script does not start. Python 3.9 or newer.

On Debian, Ubuntu and anything else that ships a
[PEP 668](https://peps.python.org/pep-0668/) Python, that `pip install` is
refused with `error: externally-managed-environment`. Use a virtual
environment — on Debian and Ubuntu `python3 -m venv` is a package of its own,
so `sudo apt install python3-venv` (or `python3-full`) comes first:

```console
$ python3 -m venv .venv && . .venv/bin/activate
$ pip install -r requirements.txt
```

or, if you would rather not, `pip install --user --break-system-packages -r
requirements.txt`.

The executable bit is committed, so no `chmod` is needed. To put it on your
`PATH`, **symlink** it rather than copying it:

```console
$ ln -s ~/src/mdslides/mdslides ~/.local/bin/mdslides
```

The script resolves its template through `realpath(__file__)`, so a symlink
still finds `beamer.tex.tpl` back in the repository. A bare *copy* of the
script fails with `cannot open the default template '...'` — for that, set
`MD_SLIDES_TEMPLATE` to the template's path. If you installed into a venv,
remember that `#!/usr/bin/env python3` picks up whichever Python is on the
`PATH` at the time, so a symlink only works while that venv is active.

`--pdf` additionally needs a TeX installation with beamer, listings, lmodern,
graphicx, color, xspace and (optionally, but do have it) upquote. Only upquote
is loaded conditionally; the rest the template pulls in unconditionally, and
lmodern is the one a lean install is likeliest to lack — it is `fontfamily`'s
default, and on Debian it lives in the `lmodern` package, which `texlive-base`
only recommends. If your deck writes tables, it needs tabularx too — the
template does not load that for you either.

The template loads no `fontenc`, no `inputenc` and no `babel`, and `lang:` is
not a key it reads. A deck with accented prose — `Ondřej Lengál`, `FIT VUT v
Brně` — compiles cleanly and looks right, but the glyphs are OT1 composites:
the PDF cannot be searched or copied out of, and an accented word is never
hyphenated. One line of `header-includes` fixes both:

```yaml
header-includes: |
  \usepackage[T1]{fontenc}
```

Add `\usepackage[<language>]{babel}` as well for that language's hyphenation
patterns, if your TeX has the language pack.


## Using it

`mdslides` is a filter: it reads the file you name (or standard input) and
writes LaTeX to `-o` (or standard output). Its own diagnostics go to standard
error, so the LaTeX on standard output stays clean; the one thing that does
not is the LaTeX engine under `--verbose-latex`, which inherits standard
output.

```console
$ mdslides deck.md > deck.tex          # same as -o deck.tex
$ cat deck.md | mdslides | less        # both ends are streams
$ mdslides --pdf deck.md               # writes deck.tex, then builds deck.pdf
```

| Option | Meaning |
|---|---|
| `FILE` | input Markdown, `-` for stdin (the default) |
| `-o, --output FILE` | output `.tex`, `-` for stdout (the default) |
| `-t, --template FILE` | Beamer template to use |
| `-V, --variable KEY=VALUE` | set a metadata key from the command line; repeatable |
| `-l, --slide-level N` | heading level that starts a frame (default 1) |
| `--escapechar CHAR` | escape character inside ` ```lstlisting ` blocks (default `@`; empty to switch it off) |
| `--handout` | one page per frame — the same as `handout: true` |
| `-p, --pdf` | run the LaTeX engine on the result as well |
| `--verbose-latex` | show the engine's output instead of just its errors |
| `-d, --dump-ast` | dump the parsed Markdown tree to stderr |
| `--version` | print `mdslides 0.1` |

`-V` is applied to the metadata *before* anything is derived from it, so
`-V title=X` also reaches the short title in the footline. It takes any
metadata key, and the value may itself contain `=`; the last one wins. Use it
for the keys that have no flag of their own:

```console
$ mdslides deck.md -V smart=false -V highlight=alert -V theme=metropolis
$ mdslides deck.md -V toc=true -V toc-title=Plan
```

Booleans accept `true`/`false`, `yes`/`no`, `on`/`off`, `1`/`0` and the empty
string, case-insensitively. Anything else — including a typo — reads as true.

### Building the PDF

`--pdf` runs `latexmk -pdf` once if latexmk is on the `PATH`, and otherwise
`pdflatex` twice, because beamer needs the second pass for its counters — or
once, if the first pass already fails, since a failing run stops there. It
announces each run on stderr, runs in the directory of the
`.tex`, exits with the engine's own status, and leaves the `.tex` and every
aux file behind. Without `-o` the output name comes from the input, so
`mdslides --pdf slides/deck.md` writes `slides/deck.tex` and builds
`slides/deck.pdf`.

Note that **most LaTeX errors are not echoed**. The engine is run with
`-file-line-error`, which rewrites errors as `./deck.tex:150: Undefined
control sequence.`, and only lines starting with `!` are lifted out of the
log — which in practice means missing packages and little else. When a build
fails with nothing but `mdslides: see /path/deck.log`, open that log, or
re-run with `--verbose-latex`.


## Writing a deck

### The metadata block

A YAML block fenced by `---`, at the very top of the file. It must start on
line 1, and it must be closed (by `---` or `...`) — an unclosed block is not
recognized at all, and every key silently becomes slide text.

```yaml
---
title:    'Symbolic Execution'
subtitle: 'SAV --- Static Analysis and Verification'
author:   'Ondřej Lengál'
institute: 'FIT BUT'
date:     '4 November 2025'
short-institute: ''
theme:    Madrid
toc:      true
---
```

| Key | Default | What it does |
|---|---|---|
| `title`, `subtitle`, `author`, `institute`, `date` | empty | beamer's own title page; `author` and `institute` may be lists, joined with `\and` |
| `short-title`, `short-author`, `short-institute`, `short-date` | the long form | what beamer puts in the footline |
| `titlepage` | true if there is a title | emit `\frame{\titlepage}` |
| `toc` | `false` | a table of contents after the title page |
| `toc-title` | `Outline` | its frame title |
| `section-titles` | `true` | a separator slide at each part, section and subsection |
| `theme`, `colortheme`, `fonttheme` | `default` | `\usetheme` and friends |
| `fontfamily` | `lmodern` | emitted as `\usepackage{...}`, so it must name a package |
| `fontsize`, `aspectratio`, `classoption` | — | `\documentclass` options, after the unconditional `dvipsnames`; e.g. `fontsize: 10pt`, `aspectratio: 169` |
| `handout` | `false` | empty `\xpause`, and with it `\pausex`, so every frame is one page |
| `header-includes` | empty | LaTeX injected last in the preamble, so it overrides everything above |
| `colorlinks` | `true` | colour the link text |
| `urlcolor` | `blue` | colour for `\href` and `\url` |
| `linkcolor` | whatever `urlcolor` is | colour for internal `[text](#label)` links |
| `smart` | `true` | turn `"` into typographic quotes |
| `highlight` | `hlbl` | the macro `==this==` becomes |

A few things worth knowing about that table:

* **Metadata values are not parsed as Markdown.** `title: '**Lecture 7**'`
  puts literal asterisks on the title slide. LaTeX in them *does* work, which
  is the way to get emphasis, maths, or a line break there:
  `title: 'Lecture 7\\Symbolic Execution'` (single-quote it, or YAML eats the
  backslashes). They are not escaped either, so a literal `%` in a title
  comments out the rest of its line — write `\%`.
* **Absent and empty are different** for the short forms. `short-institute:`
  with no value is "not given" and falls back to the long form;
  `short-institute: ''` is "leave it empty", which is the only way to get
  nothing in that corner of the footline.
* `classoption` is singular, and `handout: true` is not the same switch as
  `classoption: handout`: the first empties `\pausex`, the second is beamer's
  own blunter instrument, which also collapses overlay specifications you
  wrote out by hand.
* **Watch YAML's booleans.** `institute: NO` becomes `\institute{False}`.
  Quote anything that could be read as one.
* **`aspectratio` is beamer's spelling, not a ratio.** Write `169` (or `1610`,
  `149`, `43`, `32`). `16:9` is YAML for the number 969 and gives you a
  2902pt-wide slide with no error whatsoever; `'16:9'` fails inside beamer
  with `Missing = inserted for \ifnum`. With neither key you get beamer's own
  4:3 at 11pt.
* `slide-level` and `escapechar` are *not* metadata keys, unlike pandoc —
  they are command-line options only.
* Nothing warns about a key it does not know. `filecolor`, `citecolor`,
  `linkstyle`, `titlegraphic` and `logo` parse and are then discarded, and a
  misspelled key is simply inert.
* A `#` comment is YAML's own way to disable a line; `<!-- ... -->` lines are
  stripped from the block before it is parsed, and work too.

### Slides

A heading at `--slide-level` (1 by default) starts a frame. A heading *above*
it becomes a `\section` — always `\section`, however far above, so with
`--slide-level 3` both `#` and `##` open a section rather than a section and a
subsection; `{.part}` and `{.subsection}` are how you ask for another level. A
heading *below* it stays inside the frame, currently as `\textbf{...}\par`. A
thematic break (`---`, `***`, `___`) at the top level starts an untitled
frame, as does any content before the first heading.

```markdown
# A frame

text

---

another frame, with no title
```

Frame titles are parsed as Markdown, so `# Why $x_1$ matters` and
`# **This** one` both work.

Leave a blank line before a `---`. Directly under a paragraph it is a setext
heading, not a break — and a setext `---` is level 2, so at the default slide
level it is a heading *below* it: no break, no title, just the paragraph set
as `\textbf{...}\par` inside the frame you were already on. (`===` under a
paragraph is level 1, and that one does start a frame.)

### Frame attributes

A trailing `{...}` on a heading sets frame options: a recognized class becomes
an option, `#id` becomes `label=id` (which `[text](#id)` can link to), and
`key=value` passes through.

```markdown
# Algorithm {.fragile #algo}      ->  \begin{frame}[fragile,label=algo]{Algorithm}
```

The recognized classes are `fragile`, `plain`, `allowframebreaks`, `shrink`,
`squeeze`, `noframenumbering`, `t`, `b` and `c`. `[fragile]` is added
automatically to any frame holding verbatim material, so you rarely need it by
hand. An unrecognized class is dropped in silence, and one token that is
neither `.class`, `#id` nor `key=value` makes the whole list fail and print as
part of the title.

A heading may be nothing but an attribute list. `# {.plain}` is an untitled
frame *with* options, which a `---` break cannot give you — `--- {.plain}` is
not a break at all, and comes out as literal text.

### A title slide of your own

For anything beamer's own title page cannot express, set `titlepage: false`
and write the frame yourself, as the first thing in the body:

````markdown
# {.plain}

\begin{center}
  \includegraphics[width=0.3\textwidth]{logo.png}\par
  \vspace{1em}
  {\Large Symbolic Execution}\par
  {\small Ondřej Lengál}
\end{center}
````

Write the frame *contents*, never `\begin{frame}` itself: everything at the
top level is wrapped into a frame, so a hand-written one ends up nested inside
another, and the build dies somewhere far from the cause.

### Section separator slides

`{.section}` on a heading opens that sectioning level, and `{.subsection}` and
`{.part}` do the same one level down or up:

```markdown
# Part II: Symbolic execution {.section}   ->  \section{Part II: ...}
```

The separator slide itself is not emitted next to it — the template hooks one
onto every sectioning level with `\AtBeginSection`, which is what lets
`section-titles: false` switch all of them off at once, and what gives one to
a section made by a heading above the slide level too. The divider carries the
section name alone, in the theme's own colours and fonts. To change it,
redefine `\setbeamertemplate{section page}` from `header-includes`.

Give a `{.section}` heading content and that content becomes the slide right
after the divider, so nothing written under it is lost.

Do **not** write `\section{...}` as a line of raw LaTeX instead: everything at
the top level is wrapped into a frame, so it would become a frame of its own
or be swallowed by the one above it.

### Environments: the `@` directives

Two syntaxes, and which one you pick is what says how the contents are
treated:

```markdown
@theorem[Pumping lemma]        \begin{align}
For every **regular** ...        x_1 &= y_2 \\
@end                           \end{align}
^ contents are Markdown        ^ contents are LaTeX, untouched
```

An environment of your own needs no registration — `@onlyenv<2>` becomes
`\begin{onlyenv}<2>`, whatever the tool knows about `onlyenv`.

The argument is read from its first character. `<`, `[` or `{` means the rest
is LaTeX and is handed over exactly as written, which is how you reach
overlays, optional arguments and multi-argument signatures. Anything else is
*friendly*: a bare number is a fraction of `\textwidth` (`@column 0.3`), and a
bare title is parsed as Markdown (`@block Results **so far**`). The tool
knows, for the common environments, that `block`-likes take `{title}` and
`theorem`-likes take
`[title]`; an unlisted environment still works, you just write the brackets
yourself.

Three things close a directive: `@end` (optionally naming what it closes), the
same name again for `@column`, so a row of columns needs no `@end` between
them, and any heading. A `---` break does **not**: it is swallowed into the
environment and set as a horizontal rule, the untitled frame it should have
started never appears, and what follows lands inside the environment too.
Write the `@end` first. `@end name` closes everything still open inside it, as
`</ul>` does in HTML. A stray `@end` is reported on stderr and dropped.

````markdown
# Two columns

@columns
@column 0.45
```C
int main(void) { return 0; }
```
@column 0.55
* the right-hand side
@end
````

gives `\begin{columns}[T]`, a `\begin{column}{0.45\textwidth}` and a
`\begin{column}{0.55\textwidth}`, and `[fragile]` on the frame because of the
listing. `[T]` is the default because without it beamer centres the columns
against each other, and a short column of code floats beside a tall one.

`@note`, `@alert`, `@only`, `@uncover`, `@visible` and `@invisible` emit
`\note{...}` and friends rather than an environment. **The argument on the
directive line is discarded** — `@note remember this` loses "remember this" —
so only the overlay survives and the text goes on the lines below:

```markdown
@note
remember the **KLEE** paper
@end
```

Nothing of a `\note` reaches the PDF unless the deck asks for it: put
`\setbeameroption{show notes}` (or `show notes on second screen`) in
`header-includes`.

### Code

A fenced block becomes an `lstlisting`:

````markdown
```C
int main(void) { return 0; }
```
````

The language word is looked up in a table of 35 aliases (`c`, `c++`, `py`,
`sh`, `haskell`, `matlab`, `llvm`, `verilog`, ...); a language listings does
not know becomes a plain listing rather than a LaTeX error. Three entries
carry a dialect: `lua` is `[5.3]Lua`, because listings has no default dialect
for Lua, while `latex` is `[LaTeX]TeX` and `ocaml` is `[Objective]Caml`, which
name dialects of the `tex` and `caml` entries beside them.

Tagging a fence as `lstlisting` (or `listings`) means "this is listings
input": no language is set, and `escapechar=@` is added instead, so `@$x_1$@`
inside the listing typesets as maths. A language fence never gets an
escapechar, since a C snippet is free to contain an `@`.

Every listing is governed by the `\lstset` in the template, which is emitted
before `header-includes` so that an `\lstset` of your own wins. Line numbering
is off; `header-includes: \lstset{numbers=left}` turns it on — the options
need that `\lstset` around them, or they land in the preamble as loose text
and the build stops with `Missing \begin{document}`.

### Images

```markdown
![KLEE's architecture](klee.png){width=0.8 clip}
```

`width` and `height` are measured against the slide when they are bare
numbers, so `width=0.8` is `0.8\textwidth`; anything else (`50mm`) is used as
written. Unknown keys and bare flags pass through into `\includegraphics`. An
attribute value containing spaces must be quoted: `trim="0 0 0 10"`.

An image alone in a paragraph **with** alt text becomes a centred `figure`
with the alt text as its caption, parsed as Markdown; with empty alt text it
stays a bare `\includegraphics`. The title — `![](f.png "x")` — is dropped, as
pandoc drops it.

The path is passed through untouched, so LaTeX resolves it relative to the
generated `.tex`, not to the Markdown — and `--pdf` runs the engine in the
`.tex`'s own directory. Keep the two together, or, when `-o` writes elsewhere
(`mdslides deck/s.md -o build/s.tex`), point LaTeX back with
`\graphicspath{{../deck/}}` in `header-includes`. A missing image is one of
the errors `--pdf` does not echo: you get only the name of the log.

### Text

**Maths.** `$...$` and `$$...$$` are claimed ahead of emphasis, which is what
keeps `$pc_1 \land pc_2$` and `$a *b* c$` intact. Display maths becomes
`\[...\]`, and a display and an inline formula may share a paragraph. Only the
`$` spellings work, though — `\(x\)` and `\[y\]` typed in the source silently
lose their backslashes. Two inline spans written with nothing at all between
them (`$x$$y$`) are ambiguous, since that could be a display opener: the first
is claimed and the second passes through, which LaTeX still typesets.

**Highlighting.** `==like this==` becomes `\hlbl{like this}`; the macro is the
`highlight` metadata key. It nests with emphasis either way round —
`==**x**==` and `**==x==**` both work. As with `**`, the delimiters may not
sit against whitespace, so `a == b` stays arithmetic, and a run of three or
more `=` is left alone, so a setext underline is safe.

**Bracketed spans.** `[text]{.hlrd}` becomes `\hlrd{text}` — the class *is*
the macro name, so any macro of your own works without being registered, and
several nest with the first outermost: `[x]{.hlbl .hlgr}` is
`\hlbl{\hlgr{x}}`, which means the *last* class is the colour you see. The
contents are Markdown. Nothing checks that the macro exists; a typo surfaces
as an undefined control sequence from LaTeX, and `--pdf` will not show you
that error. The template predefines `\hlbl` (`blue`), `\hlgr`
(`olive!50!green`), `\hlrd` (`red`), `\hlorg` (`Orange`), `\hlgrey`
(`black!50`), `\hldgr` (`olive!20!green`) and `\hlvio` (`[rgb]{0.7,0,0.35}`).

**Links.** `[text](url)` becomes `\href`, `<url>` becomes `\url`, and
`[text](#label)` becomes `\hyperlink`, pairing with the `{#label}` heading
attribute. All three are coloured so they can be told from the prose; only the
link text is, never beamer's own navigation, which on a dark theme would put
blue on blue. Bare URLs are not autolinked — write `<...>`.

**Quotes.** A straight `"` becomes ``` ``like this'' ```, which LaTeX sets as
“like this”. Which way a quote leans is decided from the character before it
rather than by pairing, so an odd one cannot send the rest of the deck the
wrong way round, and `10"` reads as an inch mark. Only prose is touched —
quotes in code, in maths, in listings and inside raw LaTeX stay straight
without needing to be excluded. `\"` is the way out, and `smart: false` turns
it off. Only the double quote is smartened; `'` is left to LaTeX, which sets
it as a right single quote.

**Line breaks.** Two trailing spaces give `\\`. A literal `\\` typed in prose
does *not* — Markdown reads it as an escaped backslash and one of them is
eaten. Inside a raw LaTeX environment it survives, which is what makes
hand-written table rows work.

### Overlays

`\pausex` is the deck's pause; it is `\pause` unless `handout: true` or
`--handout` empties it, in which case every frame is one page. Overlay
specifications written out in LaTeX (`<2->`) are untouched by that — beamer's
own `classoption: handout` is the instrument for those.

Put `\pausex` on a line of its own, indented to the content of the list item
it follows. A macro line at column 0 is still fine inside a list; it is
comments that are fussy (below).

### Comments

A `%` at the start of a line is the everyday one. The line is removed from the
source before parsing, so it reaches neither the `.tex` nor the PDF, and —
because it is removed rather than blanked — it cannot end a paragraph or make
a list loose:

```markdown
* users try **input vectors**
% remember to mention the KLEE paper
* pros: no false positives
```

A `%` part-way along a line is left alone and passed through to LaTeX, where
it still comments out the rest of that line. Write `\%` for a literal percent
sign. A leading `%` is kept inside a **fenced** code block and inside a
hand-written verbatim environment, where it may be Matlab or a `printf`
format. A four-space-indented code block is *not* protected — its `%` lines
are deleted like any other comment, silently — so fence any snippet whose own
comments start with `%`.

`<!-- ... -->` also works and is dropped. It is the one for a block: several
lines, inline mid-sentence, or wrapped around a whole slide, which is how you
park the slides you are not giving today — with one exception: a comment
before the *first* heading is still content before the first heading, so it
opens an untitled frame and you get a blank slide. Park that one with `%`
lines, which are removed from the source outright. **But at column 0 between
two list items it splits the list in two**, because an HTML block interrupts a
list the way any other block would. Indent it to the item's own content, or
use a `%` line, which never has that problem.

### Tables

There is no support for Markdown pipe tables — write the LaTeX, which is taken
verbatim:

```markdown
\begin{tabularx}{\textwidth}{lX}
  KLEE & a symbolic executor \\
\end{tabularx}
```

and pull the package in yourself, since the template does not:

```yaml
header-includes: |
  \usepackage{tabularx}
  \usepackage{booktabs}
```

More than one line needs that `|` block scalar (a YAML list, one `- ` per
item, works too). Repeating the key does *not* — YAML keeps the last one and
the rest vanish without a word.


## Everything is LaTeX, including your prose

This is the one thing to internalize, and the source of most surprises:
**running text is not escaped**. It is handed to LaTeX as you typed it, which
is exactly what makes `\ldots`, `Fig.~1`, `e.g.\ this` and `\textbf{x}` work
in the middle of a sentence without ceremony. The cost is that the characters
LaTeX reserves are yours to escape:

| You type | You get | Write instead |
|---|---|---|
| `&` | an alignment error | `\&` |
| `%` | the rest of the line commented out | `\%` |
| `_`, `#` | an error | `\_`, `\#` |
| `{`, `}` | grouping | `\{`, `\}` |
| `~`, `^` | a non-breaking space; a maths error | `\textasciitilde{}`, `\textasciicircum{}` |
| `<`, `>` | `¡` and `¿` | `\textless{}`, `\textgreater{}` |
| <code>&#124;</code> | an em dash | `$\mid$` |

Note that `\~` and `\^` do **not** work, though `\&`, `\%`, `\_`, `\#`, `\{`
and `\}` do.

Escaping happens in one place in your prose: inside `` `inline code` ``, where
the text is meant to be literal, and where all ten of the reserved characters
are handled for you. (A link's destination is escaped too — `#` and `%` get a
backslash, braces are percent-encoded — so a URL needs nothing by hand.) That
has one sharp edge — a code span containing `$...$` or a `\macro` is
destroyed, because maths and raw LaTeX are claimed first. Write the maths
outside the span:

```markdown
$P($`counter == 10`$) = 0.5$
```

Two more consequences of the same rule:

* Anything tag-shaped is dropped, brackets and all. `x<y>z` becomes `xz`, and
  `a<b and c>d` loses everything between the angle brackets. That is the
  inline case, where the prose around the tag survives; a line that *begins*
  with a tag starts an HTML block, and the whole block goes with its text, up
  to the next blank line — a pasted `<div>` or HTML table disappears without a
  word. HTML entities are not decoded either: `&amp;` stays as it is.
* There is no strikethrough, superscript or subscript. `~~x~~`, `H~2~O` and
  `x^2^` pass through and break the build or the spacing.


## Traps

The ones that have actually cost time:

* **`mdslides --pdf deck.tex` destroys `deck.tex`.** With `--pdf` and no `-o`
  the output name is the input with its extension replaced, so when the input
  is already a `.tex` the two coincide, and the output is truncated before the
  input is read. The same holds for `-o` naming the input. More generally, the
  output file is truncated at startup, so a conversion that fails leaves an
  empty file where the old one was.
* **The metadata block needs its closing fence**, and must start on line 1.
  Otherwise it is not metadata at all, silently.
* **Most LaTeX errors are not echoed by `--pdf`** — read the log it names, or
  pass `--verbose-latex`.
* **`-V` reaches template variables too**, which is mostly a feature, but
  `-V slides=...` replaces the entire body of your deck and
  `-V classoptions=...` replaces the computed `\documentclass` options. Set
  `classoption`, `aspectratio` and `fontsize` instead.
* **Any line starting with `@` and a letter is a directive**, even mid
  paragraph: `@home tonight` opens an environment called `home`. Reflow the
  line so the `@` is not first.
* **`@block` with no title** emits `\begin{block}` with no argument, and LaTeX
  silently eats the first character of the body as the title.
* **Task lists misfire**: `- [ ] a task` becomes `\item [ ] a task`, where
  LaTeX reads the brackets as `\item`'s optional label.
* **An ordered list's start number is ignored** — `5.` renumbers to 1.
* **An unterminated `\begin{env}`** is not an error here. It swallows the rest
  of the *file*: every heading and slide after it is absorbed as literal text,
  so a three-frame deck comes out as one frame — and LaTeX still gets an
  unbalanced environment, which fails much later with a confusing message.
* **A four-space indent makes a code block**, so an indented `@block` or
  `\begin{...}` line is a listing instead of what you meant.


## What it does not do

Known gaps, kept in full in [`TODO.md`](TODO.md):

* **Pipe tables.** Write `tabularx` by hand.
* **`##` as a beamer block.** A heading below the slide level is
  `\textbf{...}\par` today.
* **Syntax highlighting.** Listings' monochrome bold keywords, where pandoc
  colours them through pygments.
* **Strikethrough and footnotes.**
* `filecolor`, `citecolor`, `linkstyle`, `titlegraphic` and `logo` parse and
  are discarded.
* A multi-line `title` leaks its `\\` into the footline; give an explicit
  `short-title` until that is fixed.

### Coming from pandoc

Most of a pandoc beamer deck converts unchanged. What does not:

* **Fenced divs.** `::: {.column}` is not supported and comes out as literal
  text — with the `%` in `width=50%` commenting out the rest of the line for
  good measure. Use the `@` directives.
* `slide-level` is a command-line option here, not a metadata key.
* There is no `-s/--standalone` and no `-t/--to`: the output is always a
  complete Beamer document.
* Metadata values are not parsed as Markdown.


## Custom templates

The preamble lives in `beamer.tex.tpl`, an ordinary
[`string.Template`](https://docs.python.org/3/library/string.html#template-strings).
Point at your own with `-t`, or with `MD_SLIDES_TEMPLATE`; `-t` wins.

The only variable a template must have is `$slides` — but the LaTeX that goes
into it is not self-contained. A template of your own must also load
`listings` (every code block is an `lstlisting`) and define `\tightlist`
(emitted at the top of every tight list), the highlight macro (`\hlbl` unless
`highlight` says otherwise), any macro your bracketed spans name, and
`\xpause`/`\pausex` if the deck pauses. `graphicx`, `xcolor` and hyperref come
from beamer itself. Copying `beamer.tex.tpl` and editing it is the safe start.
Every metadata key is available under its own name, and every key the shipped
template mentions is guaranteed to have a value, so nothing needs a
conditional — which is just as well, because `string.Template` has none.
Optional blocks (`$titlepage`, `$sectionpages`, `$toc`, `$handout`) are
therefore computed in Python and injected whole.

A hyphenated key is reachable only with the hyphens removed:
`$headerincludes`, `$toctitle`. Substitution is a single pass and unknown
variables are left alone, so a typo reaches LaTeX as a stray `$` — which LaTeX
reads as the start of maths, far from where you made the mistake.


## Developing

```console
$ pip install pytest
$ pytest
```

A few seconds. Four tests run `pdflatex` and skip themselves when it is not
installed, so the suite is green with nothing but pytest, marko and PyYAML. `pytest.ini` promotes deprecation warnings to errors, which is
deliberate: marko is the dependency most likely to break something quietly,
since the converter registers custom elements against its parser internals.
Run the suite after upgrading it.

There is no presentation in this repository — the lecture this was written for
is content, not part of the converter. What stands in for it is `EXAMPLE` in
`tests/conftest.py`, one short document exercising every construct, which
several tests assert invariants over rather than checking fixed strings. Add
to it when you add a construct, and those tests come along.

Three other documents, each with a job the others do not do:

* [`CLAUDE.md`](CLAUDE.md) — what the tool does, how it is built, and why.
* [`TODO.md`](TODO.md) — what is missing, wrong, or undecided.
* [`HANDOFF.md`](HANDOFF.md) — where things stand, and what lives outside the
  repository.

`git log` is the fine-grained record: the commit messages explain why each
thing is the way it is, and several say what was deliberately left undone.


## Licence

MIT — see [`LICENSE`](LICENSE).
