"""Shared fixtures.

mdslides is spelled without a '.py' suffix so that it can be run as a
command, which means the ordinary import machinery cannot find it.  Point a
loader straight at the file instead; that is the only bit of awkwardness the
tests need, and it lives here rather than in every test module.
"""

import argparse
import importlib.machinery
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'mdslides')
TEMPLATE = os.path.join(ROOT, 'beamer.tex.tpl')

# A whole presentation in miniature, exercising every construct the renderer
# knows: metadata (including a commented-out line, which is legal Markdown
# but not legal YAML), frames, a frame attribute, nested lists, a pause,
# maths whose underscores emphasis must not touch, both kinds of code fence,
# columns and other directives, a verbatim environment, and a figure.
#
# Several tests assert invariants over this document rather than fixed
# strings, so it stands in for a real deck.  It is self-contained: nothing
# here reads a file that is not written by the test.
EXAMPLE = r'''---
title: "An Example Deck"
short-title: "Example"
author: "Ondřej Lengál"
institute: "FIT VUT v Brně"
date: "3 November 2025"
theme: "Madrid"
colortheme: "dolphin"
fonttheme: "professionalfonts"
fontsize: 10pt
aspectratio: 169
<!--lang: en-->
titlegraphic:
toc: false
section-titles: false

header-includes: |
  \usepackage{listings}
  \usepackage{tabularx}

  \providecommand{\hlbl}[1]{\textcolor{blue}{#1}}
---

# Lists and text
* users try **\hlbl{input vectors}**, trying to break a program
* \hlbl{pros}:
  * **complete**: a failing input vector can be executed
    * not always easy: concurrency, nondeterministic memory layout, etc.
  * can be directed to some *corner cases*
\pausex
* \hlbl{cons}: problematic coverage of `corner_cases`

# Maths
* a symbolic state $\mathit{st} = (\mathit{line}, \mathit{store}, \mathit{pc})$
* two terminal nodes have distinct $pc_1 \land pc_2$
* $\mathit{store} : \mathit{Mem} \rightharpoonup \mathit{Sym}$ is partial
* all values of the input: $2^{80}$
* $P($`counter == 10`$) = 0.5$ for a uniform distribution

# A listing
```C
char input[10];
for (size_t i = 0; i < 10; ++i) {
  if (input[i] == 'B') { ++counter; }
}
```

# Listings input {.fragile}
```lstlisting
@$symState$@ := @$(line\colon 0,~pc\colon \mathit{true})$@  // initial state
while @$workSet \neq \emptyset$@:
  @$st$@ := @$workSet.getAndRemove$@()      // many ways to implement
```

# Columns
@columns
@column 0.4
```C
int power(x, y)
{
1:  int z = 1;
}
```

@column 0.6
\newlength{\rowfill}
\setlength{\rowfill}{1mm}
\begin{tabularx}{\textwidth}{|c|c|X|}
  \hline
  $\mathit{line}$ & \texttt{x} & $\mathit{pc}$ \\
  \hline
  &&\\[\rowfill]
  \hline
\end{tabularx}
@end columns

# Environments
@theorem[Pumping lemma]
For every **regular** language $L$ there is a $p \geq 1$ such that \ldots
@end

@block Results **so far**
Nothing broken yet.
@end

# A figure
![A **captioned** figure](f.png){width=0.4}

# Used materials from
* Jan Strejček, Masaryk University
* Michael Hicks, University of Maryland
'''


def _read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


@pytest.fixture(scope='session')
def mdslides():
    """The script, imported as a module."""
    loader = importlib.machinery.SourceFileLoader('mdslides', SCRIPT)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope='session')
def script():
    """Path to the script, for running it as a command."""
    return SCRIPT


@pytest.fixture(scope='session')
def template_path():
    return TEMPLATE


@pytest.fixture(scope='session')
def template():
    """The default Beamer template."""
    return _read(TEMPLATE)


@pytest.fixture(scope='session')
def deck():
    """The example presentation, as text."""
    return EXAMPLE


@pytest.fixture(scope='session')
def deck_path(tmp_path_factory):
    """The example presentation, as a file, for running the command on."""
    directory = tmp_path_factory.mktemp('deck')
    path = directory / 'example.md'
    path.write_text(EXAMPLE, encoding='utf-8')
    return str(path)


@pytest.fixture
def opts(mdslides):
    """Factory for a stand-in of the parsed command line options."""
    def make(**overrides):
        values = {'dump_ast': False, 'slide_level': 1, 'variable': {},
                  'escapechar': mdslides.LISTINGS_ESCAPECHAR}
        values.update(overrides)
        return argparse.Namespace(**values)
    return make


@pytest.fixture
def convert(mdslides, template, opts):
    """Run the whole pipeline with the default template."""
    def run(text, **overrides):
        return mdslides.convert(text, template, opts(**overrides))
    return run


@pytest.fixture
def render(mdslides, opts):
    """Render a Markdown body to Beamer, without the template around it."""
    def run(text, **overrides):
        return mdslides.make_markdown(opts(**overrides)).convert(text)
    return run


@pytest.fixture
def parse_args(mdslides):
    """parse_args(), closing any file it opened on the way out."""
    opened = []

    def run(argv):
        args = mdslides.parse_args(argv)
        opened.append(args.template)
        return args

    yield run
    for handle in opened:
        handle.close()
