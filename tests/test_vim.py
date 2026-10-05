"""The vim syntax file in vim/.

Nothing else in the suite looks at it, so it had already drifted behind the
format twice before this existed.  What is checked is what vim actually makes
of a deck: the file is loaded, a document is opened under it, and synID() is
asked which group every character ended up in.  Reading the patterns proves
nothing -- ordering alone decides most of what a vim syntax file does.

Skipped where vim is absent, so the suite still needs nothing but pytest.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

VIM = shutil.which('vim')
vim_needed = pytest.mark.skipif(VIM is None, reason='vim is not installed')

HERE = os.path.dirname(os.path.abspath(__file__))
VIM_DIR = os.path.join(os.path.dirname(HERE), 'vim')


# A line for every construct the syntax file claims to know, so that one
# probe covers the lot.  Kept here rather than in conftest's EXAMPLE because
# these assertions are about colour, not about conversion.
SAMPLE = """\
---
title: 'Symbolic Execution'
---

# A heading {.fragile #intro}

* a bullet with $x_1 \\land y_2$
% a comment line
\\pausex

===
title: A slide
nosuchkey: 1
---

@columns
@column 0.45
```C
int main(void) { return 0; }
```
@end

\\begin{tabularx}{\\textwidth}{lX}
  KLEE & a symbolic executor \\\\
\\end{tabularx}

---

\\[\\bigvee_i a_i\\] and \\(x_3\\)

(a) a lettered item
(ii) a roman one
2. a plain one starting at two

==highlighted== and [red]{.hlrd}

a span that [wraps across
a line]{.hlgr}, and ==a highlight
that wraps== too

![A caption](f.png){width=0.4}
"""

PROSE = """\
# Prose

A. Turing wrote about machines
i.e. this is prose
Note. a sentence
"""

PROBE = """\
set nocompatible
set runtimepath^=%(runtimepath)s
syntax enable
set filetype=%(filetype)s
let s:out = []
for s:l in range(1, line('$'))
  let s:groups = []
  let s:line = getline(s:l)
  let s:c = 1
  while s:c <= strlen(s:line)
    let s:g = synIDattr(synID(s:l, s:c, 1), 'name')
    if s:g !=# '' && (empty(s:groups) || s:groups[-1] !=# s:g)
      call add(s:groups, s:g)
    endif
    let s:c += 1
  endwhile
  call add(s:out, [s:line, s:groups])
endfor
call writefile([json_encode(s:out)], '%(out)s')
qall!
"""


def run_vim(tmp_path, text, filetype='mdslides'):
    """run_vim(Path, str, str) -> [(str, [str])]

Opens `text' in vim under the syntax file and returns, for each line, the
syntax groups its characters fell into, in the order they appear.
"""
    source = tmp_path / 'deck.md'
    source.write_text(text, encoding='utf-8')
    out = tmp_path / 'groups.json'
    script = tmp_path / 'probe.vim'
    script.write_text(PROBE % {'runtimepath': VIM_DIR, 'filetype': filetype,
                               'out': str(out)}, encoding='utf-8')

    subprocess.run([VIM, '-N', '-u', 'NONE', '-i', 'NONE',
                    '-S', str(script), str(source)],
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=60, check=False)

    assert out.exists(), 'vim wrote no result; the syntax file may not load'
    return [(line, groups)
            for line, groups in json.loads(out.read_text(encoding='utf-8'))]


def groups_on(probed, needle):
    """groups_on([(str, [str])], str) -> [str]: the line holding `needle'."""
    for line, groups in probed:
        if needle in line:
            return groups
    raise AssertionError('no line holding %r' % needle)


@pytest.fixture(scope='module')
def sample(tmp_path_factory):
    if VIM is None:
        pytest.skip('vim is not installed')
    return run_vim(tmp_path_factory.mktemp('sample'), SAMPLE)


@pytest.fixture(scope='module')
def prose(tmp_path_factory):
    if VIM is None:
        pytest.skip('vim is not installed')
    return run_vim(tmp_path_factory.mktemp('prose'), PROSE)


@pytest.fixture(scope='module')
def example(tmp_path_factory):
    """conftest.EXAMPLE, which grows as the format does."""
    if VIM is None:
        pytest.skip('vim is not installed')
    sys.path.insert(0, HERE)
    import conftest

    return run_vim(tmp_path_factory.mktemp('example'), conftest.EXAMPLE)


###########################################
# the constructs the file claims to know
###########################################

@vim_needed
@pytest.mark.parametrize('needle, group', [
    pytest.param("title: 'Symbolic Execution'", 'mdslidesMetaKey', id='meta'),
    pytest.param('# A heading', 'mdslidesHeading', id='heading'),
    pytest.param('{.fragile #intro}', 'mdslidesClass', id='class'),
    pytest.param('{.fragile #intro}', 'mdslidesLabel', id='label'),
    pytest.param('% a comment line', 'mdslidesComment', id='comment'),
    pytest.param('\\pausex', 'mdslidesPause', id='pause'),
    pytest.param('title: A slide', 'mdslidesSlideKey', id='slide-key'),
    pytest.param('nosuchkey: 1', 'mdslidesMetaKey', id='unknown-slide-key'),
    pytest.param('@columns', 'mdslidesDirective', id='directive'),
    pytest.param('@end', 'mdslidesDirectiveEnd', id='directive-end'),
    pytest.param('int main(void)', 'mdslidesCodeFence', id='code-fence'),
    pytest.param('KLEE & a symbolic', 'mdslidesLatexEnv', id='latex-env'),
    pytest.param('$x_1 \\land y_2$', 'mdslidesMath', id='maths'),
    pytest.param('\\[\\bigvee_i', 'mdslidesMathBracket', id='display-maths'),
    pytest.param('\\(x_3\\)', 'mdslidesMathParen', id='latex-inline-maths'),
    pytest.param('(a) a lettered', 'mdslidesListMarker', id='lettered'),
    pytest.param('(ii) a roman', 'mdslidesListMarker', id='roman'),
    pytest.param('2. a plain one', 'mdslidesListMarker', id='plain-ordered'),
    pytest.param('==highlighted==', 'mdslidesHighlight', id='highlight'),
    pytest.param('[red]{.hlrd}', 'mdslidesSpan', id='span'),
    pytest.param('![A caption]', 'mdslidesImage', id='image'),
])
def test_the_construct_is_coloured(sample, needle, group):
    assert group in groups_on(sample, needle), \
        'expected %s on the line holding %r' % (group, needle)


@vim_needed
def test_a_slide_key_it_knows_is_told_from_one_it_does_not(sample):
    """So a typo is visible before the converter warns about it."""
    assert 'mdslidesSlideKey' in groups_on(sample, 'title: A slide')
    assert 'mdslidesSlideKey' not in groups_on(sample, 'nosuchkey: 1')


@vim_needed
@pytest.mark.parametrize('needle, group', [
    pytest.param('a span that [wraps across', 'mdslidesSpan', id='span'),
    pytest.param('that wraps== too', 'mdslidesHighlight', id='highlight'),
])
def test_an_inline_span_may_wrap(sample, needle, group):
    """Prose is wrapped, and the converter reads these across a line break.
The editor showing them as broken text is the same bug seen from the other
side."""
    assert group in groups_on(sample, needle)


@vim_needed
def test_a_lone_break_is_a_break_and_a_fence_is_a_fence(sample):
    """The '---' that closes a slide's metadata and the one that starts an
untitled frame are the same characters, and must not be the same colour."""
    assert groups_on(sample, '---')[0] == 'mdslidesMetaFence'
    lone = [groups for line, groups in sample
            if line.strip() == '---' and groups == ['mdslidesBreak']]
    assert lone, 'expected a thematic break somewhere'


###########################################
# what it must leave alone
###########################################

@vim_needed
@pytest.mark.parametrize('needle', [
    pytest.param('A. Turing', id='initial'),
    pytest.param('i.e. this is prose', id='ie'),
    pytest.param('Note. a sentence', id='word'),
])
def test_a_letter_and_a_full_stop_is_not_a_list(prose, needle):
    """The converter needs a parenthesis for a letter, and so does this."""
    assert 'mdslidesListMarker' not in groups_on(prose, needle)


@vim_needed
def test_the_example_deck_has_nothing_vim_calls_an_error(example):
    """conftest.EXAMPLE grows as the format does, and stock markdown.vim
flags what it does not understand -- a raw LaTeX environment above all.  So
this fails when a construct is added to the format and not to the syntax
file, which is how it drifted behind twice before."""
    bad = [(line, groups) for line, groups in example
           if any('Error' in group for group in groups)]
    assert not bad, 'vim flags an error on: %r' % (bad[:3],)


@vim_needed
def test_the_example_deck_is_recognized_as_ours(example):
    """And that it is this syntax doing the work, not markdown's alone."""
    seen = {group for _, groups in example for group in groups}
    assert {'mdslidesDirective', 'mdslidesMath', 'mdslidesSlideKey'} <= seen


###########################################
# filetype detection
###########################################

# A deck is an ordinary '.md', so detection reads the file.  All the cases
# go through one vim, since starting it is the slow part.
DETECT_CASES = {
    'directive.md': '# D\n\n@theorem[X]\nbody\n@end\n',
    'slidemeta.md': '# D\n\n===\ntitle: T\n---\n\nx\n',
    'pause.md': '# D\n\n* a\n\\pausex\n* b\n',
    'plain.md': '# Ordinary\n\n* a list\n\nand a@b.com address\n',
    'about.md': ('# About the format\n\nA slide may say what it is:\n\n'
                 '```markdown\n===\ntitle: T\n---\n\n@columns\n@end\n'
                 '```\n\nand that is all.\n'),
    'explicit.mdslides': '# No markers at all\n\n* just bullets\n',
}


@pytest.fixture(scope='module')
def detected(tmp_path_factory):
    """The filetype vim settles on, for each of the cases above."""
    if VIM is None:
        pytest.skip('vim is not installed')

    work = tmp_path_factory.mktemp('detect')
    cases = dict(DETECT_CASES)
    with open(os.path.join(os.path.dirname(HERE), 'README.md'),
              encoding='utf-8') as handle:
        cases['README.md'] = handle.read()

    for name, text in cases.items():
        (work / name).write_text(text, encoding='utf-8')

    out = work / 'ft.json'
    # 'filetype on' has to happen before the files are read, or no BufRead
    # autocommand ever runs and every filetype comes back empty
    subprocess.run(
        [VIM, '-N', '-u', 'NONE', '-i', 'NONE',
         '--cmd', 'set runtimepath^=%s' % VIM_DIR,
         '--cmd', 'filetype on',
         '-c', 'let g:ft = {}',
         '-c', "argdo let g:ft[expand('%:t')] = &filetype",
         '-c', "call writefile([json_encode(g:ft)], '%s')" % out,
         '-c', 'qall!'] + [str(work / name) for name in cases],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=60, check=False)

    assert out.exists(), 'vim wrote no result'
    return json.loads(out.read_text(encoding='utf-8'))


@vim_needed
@pytest.mark.parametrize('name', [
    pytest.param('directive.md', id='directive'),
    pytest.param('slidemeta.md', id='slide-metadata'),
    pytest.param('pause.md', id='pause'),
    pytest.param('explicit.mdslides', id='by-extension'),
])
def test_a_deck_is_detected(detected, name):
    assert detected[name] == 'mdslides'


@vim_needed
def test_plain_markdown_is_left_alone(detected):
    assert detected['plain.md'] == 'markdown'


@vim_needed
def test_a_document_about_the_format_is_not_a_deck(detected):
    """Fenced code is skipped while looking, or a document explaining the
format detects as one written in it."""
    assert detected['about.md'] == 'markdown'


@vim_needed
def test_the_readme_is_not_a_deck(detected):
    """The real one, which is where that was first noticed."""
    assert detected['README.md'] == 'markdown'
