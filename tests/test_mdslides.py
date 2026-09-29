"""Tests for mdslides.

    pytest                              # everything
    pytest -k frontmatter               # one area
    pytest -v                           # per-test names
"""

import os
import re
import shutil
import stat
import string
import struct
import subprocess
import sys
import textwrap
import zlib

import pytest


def doc(text):
    """doc(str) -> str: a readable inline document fixture."""
    return textwrap.dedent(text).lstrip('\n')


def without_comments(latex):
    """without_comments(str) -> str

Strips LaTeX comments.  Asserting that something is *absent* from the
template is otherwise defeated by the comments explaining why it is absent.
"""
    return re.sub(r'(?m)(?<!\\)%.*$', '', latex)


###########################################
# split_frontmatter() -- recognizing and parsing the metadata block
###########################################

def test_frontmatter_is_parsed(mdslides):
    meta, body = mdslides.split_frontmatter(doc("""
        ---
        title: "Symbolic Execution"
        aspectratio: 169
        colorlinks: true
        ---

        # Manual Testing
    """))
    assert meta == {'title': 'Symbolic Execution',
                    'aspectratio': 169,
                    'colorlinks': True}
    assert '# Manual Testing' in body


def test_frontmatter_keeps_yaml_types(mdslides):
    meta, _ = mdslides.split_frontmatter(doc("""
        ---
        aspectratio: 169
        fontsize: 10pt
        toc: false
        titlegraphic:
        ---
    """))
    assert isinstance(meta['aspectratio'], int)
    assert isinstance(meta['fontsize'], str)
    assert meta['toc'] is False
    assert meta['titlegraphic'] is None


def test_frontmatter_block_scalar_survives(mdslides):
    meta, _ = mdslides.split_frontmatter(doc("""
        ---
        header-includes: |
          \\usepackage{listings}

          \\input{macros.tex}
        ---
    """))
    assert meta['header-includes'] == \
        '\\usepackage{listings}\n\n\\input{macros.tex}\n'


def test_frontmatter_html_comments_are_stripped(mdslides):
    """HTML comments are valid Markdown but not valid YAML."""
    meta, _ = mdslides.split_frontmatter(doc("""
        ---
        title: T
        <!--lang: en-->
        date: today
        ---
    """))
    assert meta == {'title': 'T', 'date': 'today'}


@pytest.mark.parametrize('text, expected', [
    pytest.param('---\ntitle: T\n---\n', {'title': 'T'}, id='minimal'),
    pytest.param('---\ntitle: T\n...\n', {'title': 'T'}, id='closed-with-dots'),
    pytest.param('---   \ntitle: T\n---\t\n', {'title': 'T'}, id='fence-whitespace'),
    pytest.param('---\ntitle: "a --- b"\n---\n', {'title': 'a --- b'},
                 id='dashes-in-value'),
    pytest.param('---\n---\n', {}, id='empty-block'),
    pytest.param('---\r\ntitle: T\r\n---\r\n', {'title': 'T'}, id='crlf'),
])
def test_frontmatter_recognized_forms(mdslides, text, expected):
    meta, _ = mdslides.split_frontmatter(text)
    assert meta == expected


@pytest.mark.parametrize('text', [
    pytest.param('# Just a slide\n* bullet\n', id='no-metadata'),
    pytest.param('intro\n\n---\n\n# Slide\n', id='thematic-break'),
    pytest.param('\n---\ntitle: T\n---\n', id='not-on-the-first-line'),
    pytest.param('---\ntitle: T\n\n# Slide\n', id='no-closing-fence'),
])
def test_frontmatter_absent_leaves_the_document_alone(mdslides, text):
    """Anything that is not a metadata block has to survive untouched."""
    assert mdslides.split_frontmatter(text) == ({}, text)


def test_frontmatter_only_the_first_block_counts(mdslides):
    """Fences further down belong to the body."""
    meta, body = mdslides.split_frontmatter(
        '---\ntitle: T\n---\n\n# A\n\n---\n\n# B\n')
    assert meta == {'title': 'T'}
    assert '---' in body
    assert '# B' in body


def test_frontmatter_preserves_line_numbers(mdslides):
    """The block becomes blank lines so the body keeps its numbering."""
    text = doc("""
        ---
        title: T
        date: today
        ---

        # Slide
    """)
    _, body = mdslides.split_frontmatter(text)
    assert len(body.splitlines()) == len(text.splitlines())
    assert body.splitlines()[:4] == [''] * 4
    assert body.splitlines()[5] == '# Slide'


@pytest.mark.parametrize('block, message', [
    pytest.param('title: [unclosed', 'cannot parse the metadata block',
                 id='malformed-yaml'),
    pytest.param('just a string', 'must be a mapping', id='scalar'),
    pytest.param('- a\n- b', 'must be a mapping', id='sequence'),
])
def test_frontmatter_bad_block_exits_cleanly(mdslides, block, message):
    with pytest.raises(SystemExit) as caught:
        mdslides.split_frontmatter('---\n%s\n---\n' % block)
    assert message in str(caught.value)


###########################################
# find_template() -- where the default template comes from
###########################################

def test_template_defaults_to_beside_the_script(mdslides, monkeypatch,
                                                template_path):
    monkeypatch.delenv(mdslides.TEMPLATE_ENV_VAR, raising=False)
    assert mdslides.find_template() == template_path


def test_template_environment_variable_wins(mdslides, monkeypatch):
    monkeypatch.setenv(mdslides.TEMPLATE_ENV_VAR, '/somewhere/else.tpl')
    assert mdslides.find_template() == '/somewhere/else.tpl'


def test_template_empty_environment_variable_is_ignored(mdslides, monkeypatch,
                                                        template_path):
    monkeypatch.setenv(mdslides.TEMPLATE_ENV_VAR, '')
    assert mdslides.find_template() == template_path


###########################################
# parse_args() -- the command line
###########################################

def test_args_defaults(parse_args, template_path):
    args = parse_args([])
    assert args.file is sys.stdin
    assert args.output is sys.stdout
    assert args.slide_level == 1
    assert args.dump_ast is False
    assert args.variable == {}
    assert args.template.name == template_path


@pytest.mark.parametrize('argv, expected', [
    pytest.param(['-V', 'title=T'], {'title': 'T'}, id='one'),
    pytest.param(['-V', 'title=T', '-V', 'aspectratio=169'],
                 {'title': 'T', 'aspectratio': '169'}, id='several'),
    pytest.param(['-V', 'linkstyle=a=b'], {'linkstyle': 'a=b'},
                 id='value-with-equals'),
    pytest.param(['-V', '  title  =T'], {'title': 'T'}, id='key-is-stripped'),
    pytest.param(['-V', 'title='], {'title': ''}, id='empty-value'),
])
def test_args_variables_become_a_dict(parse_args, argv, expected):
    assert parse_args(argv).variable == expected


def test_args_dash_means_the_standard_streams(parse_args):
    args = parse_args(['-', '-o', '-'])
    assert args.file is sys.stdin
    assert args.output is sys.stdout


def test_args_missing_input_file_is_an_error(mdslides, capsys):
    with pytest.raises(SystemExit):
        mdslides.parse_args(['/no/such/deck.md'])
    assert "cannot open the input file '/no/such/deck.md'" \
        in capsys.readouterr().err


def test_args_variable_without_a_value_is_an_error(mdslides, capsys):
    with pytest.raises(SystemExit):
        mdslides.parse_args(['-V', 'oops'])
    assert 'KEY=VALUE' in capsys.readouterr().err


def test_args_missing_default_template_is_an_error(mdslides, monkeypatch, capsys):
    monkeypatch.setenv(mdslides.TEMPLATE_ENV_VAR, '/no/such/template.tpl')
    with pytest.raises(SystemExit):
        mdslides.parse_args([])
    assert 'default template' in capsys.readouterr().err


@pytest.mark.parametrize('argv', [['-l', '2'], ['--slide-level', '2']])
def test_args_slide_level(parse_args, argv):
    assert parse_args(argv).slide_level == 2


###########################################
# The renderer: helpers
###########################################

@pytest.mark.parametrize('text, expected', [
    pytest.param('a_b', 'a\\_b', id='underscore'),
    pytest.param('100%', '100\\%', id='percent'),
    pytest.param('a & b', 'a \\& b', id='ampersand'),
    pytest.param('#1', '\\#1', id='hash'),
    pytest.param('a{b}', 'a\\{b\\}', id='braces'),
    pytest.param('\\n', '\\textbackslash{}n', id='backslash'),
    pytest.param('a~b', 'a\\~{}b', id='tilde'),
    pytest.param('plain', 'plain', id='nothing-to-do'),
])
def test_escape_latex(mdslides, text, expected):
    assert mdslides.escape_latex(text) == expected


@pytest.mark.parametrize('title, expected', [
    pytest.param('Plain', ('Plain', [], None), id='no-attributes'),
    pytest.param('Algorithm {.fragile}', ('Algorithm', ['fragile'], None),
                 id='fragile'),
    pytest.param('T {.plain .allowframebreaks}',
                 ('T', ['plain', 'allowframebreaks'], None), id='two-classes'),
    pytest.param('T {label=intro}', ('T', ['label=intro'], None),
                 id='key-value'),
    pytest.param('T {#intro}', ('T', ['label=intro'], None), id='identifier'),
    pytest.param('T {.nosuchoption}', ('T', [], None),
                 id='unknown-class-dropped'),
    pytest.param('Part II {.section}', ('Part II', [], 'section'),
                 id='section'),
    pytest.param('T {.subsection}', ('T', [], 'subsection'), id='subsection'),
    pytest.param('T {.part}', ('T', [], 'part'), id='part'),
    pytest.param('T {.section .plain}', ('T', ['plain'], 'section'),
                 id='section-with-a-frame-option'),
    # a title may legitimately end in a braced LaTeX group
    pytest.param('A \\hlbl{Foo}', ('A \\hlbl{Foo}', [], None),
                 id='latex-group'),
    pytest.param('\\texttt{x}', ('\\texttt{x}', [], None),
                 id='only-a-latex-group'),
])
def test_split_heading_attributes(mdslides, title, expected):
    assert mdslides.split_heading_attributes(title) == expected


###########################################
# The renderer: document structure
###########################################

def test_render_one_frame_per_heading(render):
    result = render('# One\n\ntext\n\n# Two\n\ntext\n')
    assert result.count('\\begin{frame}') == 2
    assert result.count('\\end{frame}') == 2
    assert '\\begin{frame}{One}' in result
    assert '\\begin{frame}{Two}' in result


def test_render_heading_above_the_slide_level_is_a_section(render):
    result = render('# Part\n\n## Slide\n\ntext\n', slide_level=2)
    assert '\\section{Part}' in result
    assert '\\begin{frame}{Slide}' in result


def test_render_heading_below_the_slide_level_stays_in_the_frame(render):
    result = render('# Slide\n\n## Sub\n\ntext\n')
    assert result.count('\\begin{frame}') == 1
    assert 'Sub' in result


###########################################
# Section separator slides
###########################################

@pytest.mark.parametrize('level', ['section', 'subsection', 'part'])
def test_section_opens_the_level_and_takes_no_frame(render, level):
    """A bare '{.section}' heading opens the sectioning level and nothing
else; the separator slide is hooked onto it in the preamble."""
    body = render('# Part II {.%s}\n\n# Basics\ncontent\n' % level)
    assert '\\%s{Part II}' % level in body
    assert body.count('\\begin{frame}') == 1        # only "Basics"


def test_section_content_becomes_the_slide_after_it(render):
    """Content under the heading is not dropped."""
    body = render('# Part II {.section}\ncustom text\n\n# Basics\nx\n')
    assert body.index('\\section{Part II}') < body.index('custom text')
    assert body.count('\\begin{frame}') == 2


def test_section_keeps_other_frame_options_for_its_content(render):
    body = render('# Part II {.section .plain}\ncustom\n')
    assert '\\section{Part II}' in body
    assert '\\begin{frame}[plain]' in body


def test_section_title_may_hold_markdown(render):
    assert '\\section{\\textbf{Part} II}' in render('# **Part** II {.section}\n')


def test_section_class_chooses_the_level_above_the_slide_level(render):
    body = render('# Part {.part}\n\n## Slide\nx\n', slide_level=2)
    assert '\\part{Part}' in body


def test_section_above_the_slide_level_without_a_class(render):
    """Unchanged behaviour: a heading above the slide level is a section."""
    body = render('# Part\n\n## Slide\nx\n', slide_level=2)
    assert '\\section{Part}' in body


###########################################
# Separator slides and the table of contents, from the metadata
###########################################

def test_section_pages_are_hooked_on_by_default(convert):
    """As in pandoc. A deck with no sections registers hooks that never
fire, so the default costs nothing."""
    result = convert('# S\nx\n')
    for level in ('Part', 'Section', 'Subsection'):
        assert '\\AtBegin%s' % level in result


def test_section_pages_are_plain_and_unnumbered(convert):
    """A divider should carry no footline and consume no slide number."""
    result = convert('# S\nx\n')
    assert '\\frame[plain,noframenumbering]{\\sectionpage}' in result


@pytest.mark.parametrize('source, overrides', [
    pytest.param('---\nsection-titles: false\n---\n\n# S\nx\n', {},
                 id='from-the-metadata'),
    # -V gives a string, which must not read as a non-empty truth
    pytest.param('# S\nx\n', {'variable': {'section-titles': 'false'}},
                 id='from-the-command-line'),
])
def test_section_pages_can_be_switched_off(convert, source, overrides):
    """Assert on the hook, not on the word: the template's own comment
mentions \\AtBeginSection, which a substring check would match."""
    result = convert(source, **overrides)
    assert '\\AtBeginSection[]{' not in result
    assert '\\AtBeginPart{' not in result


def test_section_pages_come_before_header_includes(convert):
    """So that a deck defining its own \\AtBeginSection wins."""
    result = convert('---\nheader-includes: |\n'
                     '  \\AtBeginSection[]{\\frame{mine}}\n---\n\n# S\nx\n')
    assert result.index('\\AtBeginSection[]{\\frame[plain') \
        < result.index('\\AtBeginSection[]{\\frame{mine}}')


###########################################
# handout
###########################################

HANDOUT = '\\renewcommand{\\xpause}{}'


def test_handout_is_off_by_default(convert):
    assert HANDOUT not in convert('# S\n\ntext\n')


def test_handout_from_the_metadata(convert):
    assert HANDOUT in convert('---\nhandout: true\n---\n\n# S\n\ntext\n')


def test_handout_from_the_command_line(convert):
    assert HANDOUT in convert('# S\n\ntext\n', variable={'handout': 'true'})


def test_handout_comes_after_the_definition_it_replaces(convert):
    """It is a \\renewcommand, so \\xpause has to exist by then."""
    result = convert('---\nhandout: true\n---\n\n# S\n\ntext\n')
    assert result.index('\\newcommand{\\xpause}') < result.index(HANDOUT)


@pytest.mark.parametrize('key', ['titlepage', 'toc', 'section-titles',
                                 'handout'])
def test_a_flag_variable_never_leaks_its_value_into_the_document(convert, key):
    """-V sets the flag, not the block of LaTeX computed from it: '-V
toc=false' means no table of contents, not the word 'false' on a slide."""
    result = convert('---\ntitle: T\n---\n\n# S\n\ntext\n',
                     variable={key: 'false'})
    assert '\nfalse\n' not in result
    assert '\ntrue\n' not in result


def test_toc_is_off_by_default(convert):
    assert '\\tableofcontents' not in convert('# S\nx\n')


def test_toc_when_asked_for(convert):
    result = convert('---\ntitle: T\ntoc: true\n---\n\n# S\nx\n')
    assert '\\tableofcontents' in result
    assert '\\frametitle{Outline}' in result
    # after the title page, before the slides
    assert result.index('\\titlepage') < result.index('\\tableofcontents')
    assert result.index('\\tableofcontents') < result.index('\\begin{frame}{S}')


def test_toc_title_can_be_set(convert):
    result = convert('---\ntoc: true\ntoc-title: "Contents"\n---\n\n# S\nx\n')
    assert '\\frametitle{Contents}' in result


def test_render_thematic_break_starts_an_untitled_frame(render):
    result = render('# One\n\ntext\n\n---\n\nmore\n')
    assert result.count('\\begin{frame}') == 2
    assert '\\begin{frame}\n' in result


def test_render_material_before_the_first_heading(render):
    result = render('orphan text\n\n# Slide\n')
    assert result.count('\\begin{frame}') == 2
    assert 'orphan text' in result


def test_render_metadata_blank_lines_make_no_empty_frame(mdslides, convert):
    """split_frontmatter() pads with blank lines; they must not become a frame."""
    result = convert('---\ntitle: T\n---\n\n# Slide\n')
    assert result.count('\\begin{frame}') == 1


###########################################
# The renderer: blocks
###########################################

def test_render_nested_lists(render):
    result = render('# S\n\n* one\n  * inner\n* two\n')
    assert result.count('\\begin{itemize}') == 2
    assert result.count('\\end{itemize}') == 2
    assert '\\item one' in result
    assert '\\item inner' in result


def test_render_ordered_list(render):
    result = render('# S\n\n1. one\n2. two\n')
    assert '\\begin{enumerate}' in result
    assert '\\end{enumerate}' in result


def test_render_tight_list_is_marked_tight(render):
    """Otherwise beamer leaves a gap between every item."""
    result = render('# S\n\n* one\n* two\n')
    assert '\\begin{itemize}\n\\tightlist' in result


def test_render_loose_list_is_not_marked_tight(render):
    """Items separated by blank lines are meant to breathe."""
    result = render('# S\n\n* one\n\n* two\n')
    assert '\\tightlist' not in result


def test_template_defines_tightlist(template):
    """The renderer emits it, so it cannot be left undefined."""
    assert 'providecommand{\\tightlist}' in template


@pytest.mark.parametrize('level', ['part', 'section', 'subsection'])
def test_template_separator_pages_carry_the_name_alone(template, level):
    """Beamer's own templates print "Section 1" above the name; ours are
those with that line dropped."""
    code = without_comments(template)
    assert '\\setbeamertemplate{%s page}' % level in code
    assert '\\insert%s\\par' % level in code
    assert '\\insert%snumber' % level not in code
    assert '\\%sname' % level not in code


@pytest.mark.parametrize('macro', [
    'hlbl', 'hlgr', 'hlrd', 'hlorg', 'hlgrey', 'hldgr', 'hlvio',
])
def test_template_defines_the_highlight_macros(template, macro):
    """Decks write these in their prose and nothing else defines them, so
dropping one silently breaks every deck that used it."""
    assert '\\newcommand{\\%s}' % macro in template


def test_render_block_quote(render):
    assert '\\begin{quote}' in render('# S\n\n> quoted\n')


def test_render_html_comments_are_dropped(render):
    """This is how a deck's commented-out slides disappear."""
    result = render('# S\n\n<!-- a comment -->\n\ntext\n')
    assert 'comment' not in result
    assert 'text' in result


@pytest.mark.parametrize('source', [
    pytest.param('# S\n\n<!--\nline one\nline two\n-->\n\ntext\n',
                 id='several-lines'),
    pytest.param('# S\n\ntext <!-- aside -->\n', id='inline'),
    pytest.param('# S\n\ntext\n\n<!-- # Hidden\n\n* not shown\n-->\n',
                 id='a-whole-slide'),
])
def test_render_comment_forms_are_all_dropped(render, source):
    result = render(source)
    assert 'text' in result
    for word in ('line one', 'aside', 'Hidden', 'not shown'):
        assert word not in result


def test_render_a_comment_between_list_items_splits_the_list(render):
    """Documented rather than desired: an HTML block interrupts a list the
way any other block would.  Indent it to keep the list whole."""
    result = render('# S\n\n* one\n<!-- note -->\n* two\n')
    assert result.count('\\begin{itemize}') == 2


def test_render_an_indented_comment_keeps_the_list_whole(render):
    result = render('# S\n\n* one\n  <!-- note -->\n* two\n')
    assert result.count('\\begin{itemize}') == 1
    assert 'note' not in result


def test_render_comments_inside_a_listing_are_content(render):
    result = render('# S\n\n```C\n/* kept */\n// kept\n```\n')
    assert '/* kept */' in result
    assert '// kept' in result


def test_render_an_escaped_percent_survives(render):
    """A bare '%' would comment out the rest of the line in LaTeX."""
    assert '100\\% sure' in render('# S\n\n100\\% sure\n')


###########################################
# '%' line comments, stripped before marko runs
###########################################

@pytest.mark.parametrize('source', [
    pytest.param('# S\n\n% a note\n\ntext\n', id='on-its-own'),
    pytest.param('# S\n\ntext\n% a note\n', id='under-a-paragraph-line'),
    pytest.param('# S\n\n  % a note\n\ntext\n', id='indented'),
    pytest.param('# S\n\n%a note\n\ntext\n', id='no-space-after-it'),
])
def test_comment_lines_never_reach_the_output(convert, source):
    result = convert(source)
    assert 'a note' not in result


def test_comment_line_does_not_split_a_paragraph(render):
    """It is removed, not blanked: a blank line would end the paragraph."""
    body = render('# S\n\nbefore\n% a note\nafter\n')
    assert 'before\nafter' in body


def test_comment_line_does_not_split_a_list(render):
    """The reason to prefer '%' over '<!-- -->' for a note."""
    body = render('# S\n\n* one\n% a note\n* two\n')
    assert body.count('\\begin{itemize}') == 1
    assert 'a note' not in body


def test_comment_line_does_not_make_a_list_loose(render):
    body = render('# S\n\n* one\n% a note\n* two\n')
    assert '\\tightlist' in body


@pytest.mark.parametrize('source, kept', [
    pytest.param('# S\n\n```C\n% not a comment\n```\n', '% not a comment',
                 id='in-a-fenced-block'),
    pytest.param('# S\n\n```C\nint r = a % b;\n```\n', 'a % b',
                 id='modulo-in-code'),
    pytest.param('# S\n\n```C\nprintf("%d", r);\n```\n', '"%d"',
                 id='a-printf-format'),
    pytest.param('# S\n\n\\begin{verbatim}\n% kept\n\\end{verbatim}\n',
                 '% kept', id='in-a-verbatim-environment'),
    pytest.param('# S\n\ntext with a % trailing note\n',
                 'text with a % trailing note', id='partway-along-a-line'),
    pytest.param('# S\n\n100\\% sure\n', '100\\% sure', id='escaped'),
])
def test_a_percent_that_is_not_a_comment_line_is_kept(render, source, kept):
    assert kept in render(source)


def test_comment_lines_are_stripped_before_parsing(mdslides):
    """strip_comments() runs on the source, so marko never sees them."""
    assert mdslides.strip_comments('a\n% note\nb\n') == 'a\nb\n'
    assert mdslides.strip_comments('```\n% kept\n```\n') == '```\n% kept\n```\n'


@pytest.mark.parametrize('fence, expected', [
    pytest.param('C', 'language={C}', id='c'),
    pytest.param('haskell', 'language={Haskell}', id='case-insensitive'),
    pytest.param('lua', 'language={[5.3]Lua}', id='dialect-in-braces'),
    pytest.param('', None, id='no-language'),
    pytest.param('nosuchlanguage', None, id='unknown-language'),
])
def test_render_fenced_code(render, fence, expected):
    result = render('# S\n\n```%s\ncode()\n```\n' % fence)
    assert '\\begin{lstlisting}' in result
    assert 'code()' in result
    if expected:
        assert expected in result
    else:
        # a language listings cannot load would be a hard error
        assert 'language=' not in result


@pytest.mark.parametrize('fence', ['lstlisting', 'listings', 'LstListing'])
def test_render_raw_listing_gets_an_escapechar(render, fence):
    """The deck writes '@$symState$@' to put maths inside a listing; without
escapechar those characters print as themselves."""
    body = render('# S\n\n```%s\n@$x_1$@ := 0\n```\n' % fence)
    assert '\\begin{lstlisting}[escapechar=@]' in body
    assert '@$x_1$@ := 0' in body
    assert 'language=' not in body


def test_render_escapechar_can_be_changed(render):
    body = render('# S\n\n```lstlisting\n!$x$!\n```\n', escapechar='!')
    assert '[escapechar=!]' in body


def test_render_escapechar_can_be_switched_off(render):
    body = render('# S\n\n```lstlisting\n@$x$@\n```\n', escapechar='')
    assert '\\begin{lstlisting}\n' in body
    assert 'escapechar' not in body


def test_render_a_language_fence_gets_no_escapechar(render):
    """A C snippet is free to contain an '@'."""
    body = render('# S\n\n```C\nx = a@b;\n```\n')
    assert 'escapechar' not in body
    assert 'language={C}' in body


def test_render_code_is_not_escaped(render):
    """A listing is verbatim; escaping it would show the backslashes."""
    result = render('# S\n\n```C\nif (a_b & c) { }\n```\n')
    assert 'a_b & c' in result


###########################################
# The renderer: [fragile]
###########################################

def test_render_fragile_is_added_for_a_listing(render):
    assert '\\begin{frame}[fragile]{S}' in render('# S\n\n```C\nx\n```\n')


def test_render_fragile_is_not_added_without_one(render):
    result = render('# S\n\ntext\n')
    assert '\\begin{frame}{S}' in result
    assert 'fragile' not in result


def test_render_fragile_is_found_inside_a_list(render):
    """The listing is nested two levels down, not a direct child."""
    result = render('# S\n\n* item\n\n    ```C\n    x\n    ```\n')
    assert '[fragile]' in result


def test_render_fragile_attribute_is_honoured(render):
    result = render('# S {.fragile}\n\ntext\n')
    assert '\\begin{frame}[fragile]{S}' in result
    assert '{.fragile}' not in result


def test_render_fragile_is_not_duplicated(render):
    result = render('# S {.fragile}\n\n```C\nx\n```\n')
    assert result.count('fragile') == 1


###########################################
# The renderer: inline, and the passthrough rule
###########################################

def test_render_emphasis(render):
    result = render('# S\n\n*one* and **two**\n')
    assert '\\emph{one}' in result
    assert '\\textbf{two}' in result


def test_render_nested_emphasis(render):
    result = render('# S\n\n*a lot of **stuff***\n')
    assert '\\emph{a lot of \\textbf{stuff}}' in result


def test_render_inline_code_is_escaped(render):
    assert '\\texttt{a\\_b}' in render('# S\n\n`a_b`\n')


@pytest.mark.parametrize('text', [
    pytest.param('\\hlbl{highlighted}', id='macro-with-argument'),
    pytest.param('\\ldots', id='bare-macro'),
    pytest.param('a~program', id='non-breaking-space'),
    pytest.param('\\textbf{x} \\emph{y}', id='several-macros'),
])
def test_render_latex_passes_through(render, text):
    """Anything not recognized as Markdown is assumed to be LaTeX."""
    assert text in render('# S\n\n%s\n' % text)


def test_render_latex_inside_markdown_emphasis(render):
    assert '\\textbf{\\hlbl{input vectors}}' in \
        render('# S\n\n**\\hlbl{input vectors}**\n')


@pytest.mark.parametrize('source, expected', [
    pytest.param('\\_', '\\_', id='underscore-keeps-its-backslash'),
    pytest.param('\\#', '\\#', id='hash-keeps-its-backslash'),
    pytest.param('\\*', '*', id='asterisk-loses-it'),
])
def test_render_escaped_characters(render, source, expected):
    """LaTeX spells '\\_' the same way Markdown does, but not '\\*'."""
    body = render('# S\n\nx%sy\n' % source)
    assert 'x%sy' % expected in body


###########################################
# Typographic quotes
###########################################

def test_quotes_become_typographic(render):
    body = render('# S\n\ncan be "easily" executed\n')
    assert "can be ``easily'' executed" in body


@pytest.mark.parametrize('source, expected', [
    pytest.param('"at the start"', "``at the start''", id='opening-a-line'),
    pytest.param('("in brackets")', "(``in brackets'')", id='after-a-bracket'),
    pytest.param('"a" and "b"', "``a'' and ``b''", id='two-pairs'),
    pytest.param('"spanning **bold** text"',
                 "``spanning \\textbf{bold} text''", id='around-emphasis'),
    pytest.param('==a "quote" inside==', "\\hlbl{a ``quote'' inside}",
                 id='inside-a-highlight'),
])
def test_quotes_lean_the_right_way(render, source, expected):
    """Which way a quote leans is decided from the character before it."""
    assert expected in render('# S\n\n%s\n' % source)


def test_quotes_start_of_a_paragraph_opens(render):
    """Without resetting at a paragraph, the word above would decide."""
    body = render('# S\n\nended here\n\n"a new paragraph"\n')
    assert "``a new paragraph''" in body


def test_quotes_start_of_a_list_item_opens(render):
    body = render('# S\n\n* one\n* "second item"\n')
    assert "``second item''" in body


@pytest.mark.parametrize('source, kept', [
    pytest.param('`"code"`', '\\texttt{"code"}', id='inline-code'),
    pytest.param('$"maths"$', '$"maths"$', id='maths'),
    pytest.param('\\texttt{"macro"}', '\\texttt{"macro"}', id='a-macro'),
    pytest.param('```C\nchar *s = "kept";\n```', '"kept"', id='a-listing'),
    pytest.param('\\begin{verbatim}\n"kept"\n\\end{verbatim}', '"kept"',
                 id='verbatim'),
    pytest.param('an escaped \\" stays', 'an escaped " stays', id='escaped'),
])
def test_quotes_left_straight_where_they_are_not_prose(render, source, kept):
    assert kept in render('# S\n\n%s\n' % source)


def test_quotes_can_be_switched_off(convert):
    result = convert('---\nsmart: false\n---\n\n# S\n\nsaid "hello" twice\n')
    assert 'said "hello" twice' in result


def test_quotes_off_from_the_command_line(convert):
    result = convert('# S\n\nsaid "hello"\n', variable={'smart': 'false'})
    assert 'said "hello"' in result


###########################################
# Highlighted text and bracketed spans
###########################################

def test_highlight(render):
    assert '\\hlbl{like this}' in render('# S\n\n==like this==\n')


@pytest.mark.parametrize('source, expected', [
    pytest.param('==**bold**==', '\\hlbl{\\textbf{bold}}', id='bold-inside'),
    pytest.param('**==bold==**', '\\textbf{\\hlbl{bold}}', id='bold-outside'),
    pytest.param('==*em*==', '\\hlbl{\\emph{em}}', id='emphasis-inside'),
    pytest.param('==$x_1$==', '\\hlbl{$x_1$}', id='maths-inside'),
    pytest.param('==\\ldots==', '\\hlbl{\\ldots}', id='a-macro-inside'),
])
def test_highlight_composes(render, expected, source):
    assert expected in render('# S\n\n%s\n' % source)


@pytest.mark.parametrize('source', [
    pytest.param('a == b', id='spaced-equals'),
    pytest.param('$a == b$', id='inside-maths'),
    pytest.param('`x == y`', id='inside-code'),
    pytest.param('a ==b', id='unclosed'),
    pytest.param('|====|', id='a-run-of-equals'),
])
def test_highlight_leaves_other_equals_alone(render, source):
    assert '\\hlbl' not in render('# S\n\n%s\n' % source)


def test_highlight_does_not_eat_a_setext_heading(render):
    """A line of '=' under text is an h1, not a highlight."""
    body = render('# S\n\nA setext heading\n================\n\ntext\n')
    assert '\\hlbl' not in body


def test_highlight_macro_can_be_chosen(convert):
    result = convert('---\nhighlight: hlgr\n---\n\n# S\n\n==green==\n')
    assert '\\hlgr{green}' in result
    assert '\\hlbl' not in result.split('\\begin{document}')[1]


def test_span_wraps_the_text_in_the_class(render):
    assert '\\hlrd{not true}' in render('# S\n\n[not true]{.hlrd}\n')


def test_span_takes_any_macro_name(render):
    """The class is the macro, so one of your own needs no registration."""
    assert '\\myownmacro{x}' in render('# S\n\n[x]{.myownmacro}\n')


def test_span_with_several_classes_nests_first_outermost(render):
    assert '\\hlbl{\\hlgr{two}}' in render('# S\n\n[two]{.hlbl .hlgr}\n')


def test_span_contents_are_markdown(render):
    assert '\\hlrd{\\textbf{bold}}' in render('# S\n\n[**bold**]{.hlrd}\n')


def test_span_does_not_disturb_links(render):
    body = render('# S\n\n[text](http://x.org) and [red]{.hlrd}\n')
    assert '\\href{http://x.org}' in body
    assert '\\hlrd{red}' in body


def test_span_without_a_class_is_just_the_text(render):
    assert 'plain' in render('# S\n\n[plain]{#anchor}\n')


###########################################
# Links
###########################################

def test_render_link(render):
    """Coloured by default, so a link can be told from the prose."""
    body = render('# S\n\n[text](http://x.org)\n')
    assert '\\href{http://x.org}{\\textcolor{blue}{text}}' in body


def test_render_bare_url_is_coloured_too(render):
    body = render('# S\n\n<http://x.org>\n')
    assert '\\textcolor{blue}{\\url{http://x.org}}' in body


@pytest.mark.parametrize('url, expected', [
    pytest.param('https://x.org/#frag', 'https://x.org/\\#frag',
                 id='fragment'),
    pytest.param('https://x.org/?a=1%2Bb', 'https://x.org/?a=1\\%2Bb',
                 id='percent-encoding'),
    pytest.param('https://x.org/{a}', 'https://x.org/\\%7Ba\\%7D',
                 id='braces-are-percent-encoded'),
    pytest.param('https://x.org/a&b_c~d', 'https://x.org/a&b_c~d',
                 id='ampersand-underscore-tilde-left-alone'),
])
def test_render_url_specials_are_escaped(render, url, expected):
    """A '#' in a URL is read as a parameter and loses the whole frame:
'Illegal parameter number in definition of \\iterate'."""
    assert '\\href{%s}' % expected in render('# S\n\n[t](%s)\n' % url)


def test_render_bare_url_specials_are_escaped_too(render):
    body = render('# S\n\n<https://x.org/#frag>\n')
    assert '\\url{https://x.org/\\#frag}' in body


def test_render_internal_link(render):
    """'[text](#intro)' pairs with the '{#intro}' heading attribute."""
    body = render('# Intro {#intro}\n\n# S\n\n[back](#intro)\n')
    assert '\\begin{frame}[label=intro]' in body
    assert '\\hyperlink{intro}{\\textcolor{blue}{back}}' in body


def test_render_link_colour_can_be_chosen(convert):
    result = convert('---\nurlcolor: "olive!50!green"\n---\n\n'
                     '# S\n\n[text](http://x.org)\n')
    assert '\\textcolor{olive!50!green}{text}' in result


def test_render_internal_links_have_their_own_colour(convert):
    result = convert('---\nurlcolor: blue\nlinkcolor: red\n---\n\n'
                     '# S\n\n[out](http://x.org) [in](#a)\n')
    assert '\\textcolor{blue}{out}' in result
    assert '\\textcolor{red}{in}' in result


def test_render_links_are_not_coloured_when_switched_off(convert):
    """'colorlinks: false' leaves them looking like the prose."""
    result = convert('---\ncolorlinks: false\n---\n\n'
                     '# S\n\n[text](http://x.org) <http://y.org>\n')
    # the template defines \hl... in terms of \textcolor{blue}, so assert on
    # the wrapped link itself rather than on the colour anywhere
    assert '\\href{http://x.org}{text}' in result
    assert '\\url{http://y.org}' in result
    assert '\\textcolor{blue}{text}' not in result


def test_render_link_colouring_leaves_the_navigation_alone(convert):
    """hyperref's colorlinks would repaint beamer's footline as well --
blue on blue on a dark theme. Only the links in the text are touched."""
    result = convert('# S\n\n[text](http://x.org)\n')
    assert 'colorlinks' not in result
    assert '\\hypersetup' not in result


def test_render_image(render):
    assert '\\includegraphics{fig.png}' in render('# S\n\n![](fig.png)\n')


###########################################
# Images and their attributes
###########################################

@pytest.mark.parametrize('attributes, expected', [
    pytest.param('{width=0.8}', '[width=0.8\\textwidth]',
                 id='bare-number-is-a-fraction'),
    pytest.param('{height=0.5}', '[height=0.5\\textheight]',
                 id='height-against-the-slide'),
    pytest.param('{width=4cm}', '[width=4cm]', id='a-length-is-kept'),
    pytest.param('{width=0.5 height=0.25}',
                 '[width=0.5\\textwidth,height=0.25\\textheight]',
                 id='two-keys-in-order'),
    pytest.param('{scale=0.5}', '[scale=0.5]', id='other-keys-pass-through'),
    pytest.param('{clip}', '[clip]', id='bare-flag'),
    pytest.param('{.plain #fig width=0.3}', '[width=0.3\\textwidth]',
                 id='classes-and-identifiers-are-dropped'),
    pytest.param('', '', id='no-attributes'),
])
def test_image_attributes(render, attributes, expected):
    body = render('# S\n\n![](fig.png)%s\n' % attributes)
    assert '\\includegraphics%s{fig.png}' % expected in body


def test_image_attributes_do_not_leak_as_text(render):
    """They used to arrive in LaTeX as a stray group next to the graphic."""
    body = render('# S\n\n![](fig.png){width=0.8}\n')
    assert 'width=0.8}' not in body.replace('width=0.8\\textwidth]', '')
    assert '{ width' not in body


def test_image_title_is_dropped(render):
    """LaTeX has nowhere to put it; a caption comes from the alt text."""
    body = render('# S\n\n![](fig.png "KLEE results"){width=1.0}\n')
    assert 'KLEE results' not in body
    assert '\\includegraphics[width=1.0\\textwidth]{fig.png}' in body


###########################################
# Images: implicit figures
###########################################

def test_image_alone_with_alt_text_is_a_captioned_figure(render):
    body = render('# S\n\n![KLEE results](fig.png){width=0.8}\n')
    assert '\\begin{figure}' in body
    assert '\\centering' in body
    assert '\\caption{KLEE results}' in body
    assert '\\end{figure}' in body


def test_image_caption_may_hold_markdown(render):
    """Consistent with a directive's title."""
    body = render('# S\n\n![A **bold** caption with $x_1$](fig.png)\n')
    assert '\\caption{A \\textbf{bold} caption with $x_1$}' in body


def test_image_alone_without_alt_text_is_not_a_figure(render):
    """This is the deck's case; wrapping it would change the layout."""
    body = render('# S\n\n![](fig.png){width=0.8}\n')
    assert '\\begin{figure}' not in body
    assert '\\includegraphics[width=0.8\\textwidth]{fig.png}' in body


def test_image_in_a_sentence_is_not_a_figure(render):
    body = render('# S\n\nsee ![alt](fig.png) here\n')
    assert '\\begin{figure}' not in body
    assert 'see \\includegraphics{fig.png} here' in body


def test_two_images_in_a_paragraph_are_not_a_figure(render):
    body = render('# S\n\n![one](a.png) ![two](b.png)\n')
    assert '\\begin{figure}' not in body
    assert body.count('\\includegraphics') == 2


###########################################
# Maths
###########################################

@pytest.mark.parametrize('source', [
    pytest.param('$pc_1 \\land pc_2$', id='underscores'),
    pytest.param('$\\mathit{st}_{i}$', id='subscript-braces'),
    pytest.param('$2^{80}$', id='superscript'),
    pytest.param('$a_1 + b_2 = c_3$', id='several-underscores'),
    pytest.param('$x * y * z$', id='asterisks'),
    pytest.param('$\\mathbb{T}$', id='macro-inside'),
])
def test_math_is_left_intact(render, source):
    """Emphasis must not get at the underscores or asterisks inside maths."""
    body = render('# S\n\n%s\n' % source)
    assert source in body
    assert '\\emph' not in body
    assert '\\textbf' not in body


def test_math_several_spans_on_one_line(render):
    body = render('# S\n\nfrom $a_1$ to $b_2$ inclusive\n')
    assert '$a_1$' in body and '$b_2$' in body


def test_math_around_inline_code(render):
    """The deck writes '$P($`counter == 10`$) = ...$'."""
    body = render('# S\n\n$P($`counter == 10`$) = 0.5$\n')
    assert '$P($' in body
    assert '\\texttt{counter == 10}' in body
    assert '$) = 0.5$' in body


def test_math_display(render):
    assert '\\[x = y\\]' in render('# S\n\n$$x = y$$\n')


@pytest.mark.parametrize('markdown, expected', [
    pytest.param('\\(x_1 \\land y_2\\)', '\\(x_1 \\land y_2\\)', id='inline'),
    pytest.param('\\[\\bigvee_i a_i\\]', '\\[\\bigvee_i a_i\\]', id='display'),
    pytest.param('a \\(x_1\\) b', 'a \\(x_1\\) b', id='mid-sentence'),
])
def test_latex_maths_delimiters_survive(render, markdown, expected):
    """marko read the '\\(' as an escaped bracket and render_literal dropped
the backslash, so the maths became prose -- and the contents were parsed as
Markdown on the way, which is what ate the underscores."""
    assert expected in render('# S\n\n%s\n' % markdown)


def test_the_renderers_own_display_maths_is_valid_input(render):
    """It emits '\\[...\\]' for '$$...$$', so its output was not input to it."""
    once = render('# S\n\n$$a_1 + b_2$$\n')
    assert '\\[a_1 + b_2\\]' in once
    twice = render('# S\n\n\\[a_1 + b_2\\]\n')
    assert '\\[a_1 + b_2\\]' in twice


def test_latex_inline_maths_does_not_cross_a_newline(render):
    """As with '$...$', so that an unclosed one cannot run away with the rest
of the paragraph.  The delimiter is then an ordinary escaped bracket again,
which is where the backslash goes."""
    body = render('# S\n\nan \\(unclosed one\nand the next line\n')
    assert 'an (unclosed one' in body
    assert 'and the next line' in body


def test_an_escaped_backslash_before_a_paren_is_not_maths(render):
    body = render('# S\n\nnot maths: \\\\(x\\\\)\n')
    assert '\\(x\\)' in body


def test_plain_brackets_need_no_escaping(render):
    """Which is the way out, now that an escaped one is LaTeX's display
maths: prose is not escaped here, so a bracket can simply be written."""
    body = render('# S\n\nsee [1] and [2, 3] for details\n')
    assert 'see [1] and [2, 3] for details' in body


@pytest.mark.parametrize('markdown, expected', [
    pytest.param('A $$y$$ then $a _b_ c$ end.',
                 'A \\[y\\] then $a _b_ c$ end.', id='underscores'),
    pytest.param('A $$y$$ then $a *b* c$ end.',
                 'A \\[y\\] then $a *b* c$ end.', id='asterisks'),
    pytest.param('A $$y$$ then $a ==b== c$ end.',
                 'A \\[y\\] then $a ==b== c$ end.', id='highlight'),
    pytest.param('A $$y$$ and $$z$$ and $a _b_ c$.',
                 'A \\[y\\] and \\[z\\] and $a _b_ c$.', id='two-displays'),
])
def test_display_maths_leaves_the_next_inline_maths_alone(render, markdown,
                                                          expected):
    """Math.pattern could not match a '$$' opener, so finditer() matched from
its second '$' and consumed the inline maths that followed; the real span then
got no token and its Markdown-active characters were parsed as markup."""
    assert expected in render('# S\n\n%s\n' % markdown)


def test_inline_maths_still_wins_without_a_display(render):
    """The guard must not cost the ordinary case."""
    assert '$a _b_ c$' in render('# S\n\nNo display: $a _b_ c$ end.\n')
    assert '$pc_1 \\land pc_2$' in render('# S\n\n$pc_1 \\land pc_2$\n')


def test_two_inline_spans_with_nothing_between_them(render):
    """'$x$$y$' is ambiguous -- it could be a display opener. The first span is
claimed and the second passes through, which LaTeX still typesets."""
    assert '$x$$y$' in render('# S\n\n$x$$y$\n')


def test_math_escaped_dollar_is_not_maths(render):
    """'\\$5' is a dollar sign, and LaTeX spells it '\\$' too."""
    body = render('# S\n\ncosts \\$5 today\n')
    assert 'costs \\$5 today' in body


def test_math_a_lone_dollar_does_not_run_away(render):
    """A newline ends the search, so an unpaired '$' cannot eat the rest."""
    body = render('# S\n\nprice is $5 here\nand more text\n')
    assert 'and more text' in body


###########################################
# Raw LaTeX: inline
###########################################

def test_raw_inline_protects_macro_arguments(render):
    """Markdown must not look inside '\\hlbl{...}'."""
    assert '\\hlbl{a_b}' in render('# S\n\n\\hlbl{a_b}\n')


@pytest.mark.parametrize('source', [
    pytest.param('\\ldots', id='bare'),
    pytest.param('\\hlbl{x}', id='one-argument'),
    pytest.param('\\frac{a}{b}', id='two-arguments'),
    pytest.param('\\includegraphics[width=2cm]{fig.png}', id='option'),
    pytest.param('\\textbf{\\hlbl{nested}}', id='nested-braces'),
    pytest.param('\\section*{starred}', id='starred'),
])
def test_raw_inline_forms(render, source):
    assert source in render('# S\n\n%s\n' % source)


###########################################
# Raw LaTeX: environments
###########################################

TABLE = ('\\begin{tabularx}{\\textwidth}{|c|X|}\n'
         '  \\hline\n'
         '  $\\mathit{line}$ & \\texttt{x} \\\\\n'
         '  &&\\\\[\\rowfill]\n'
         '\\end{tabularx}\n')


def test_raw_environment_is_verbatim(render):
    """'&' and '\\\\' have to survive; Markdown would eat a backslash."""
    body = render('# S\n\n%s' % TABLE)
    for line in TABLE.splitlines():
        assert line in body


def test_raw_environment_breaks_a_paragraph(render):
    """The deck has a table directly below ':::' with no blank line."""
    body = render('# S\n\n::: { .column }\n%s' % TABLE)
    assert '\\hline' in body
    assert '\\\\' in body          # not collapsed to a single backslash


def test_raw_environment_nesting(render):
    source = ('\\begin{tabular}{c}\n'
              '\\begin{tabular}{c} inner \\end{tabular}\n'
              '\\end{tabular}\n')
    body = render('# S\n\n%safter\n' % source)
    assert body.count('\\begin{tabular}') == 2
    assert body.count('\\end{tabular}') == 2
    assert 'after' in body


def test_raw_environment_unterminated_is_not_fatal(render):
    body = render('# S\n\n\\begin{tabular}{c}\na & b\n')
    assert '\\begin{tabular}{c}' in body


def test_raw_environment_makes_the_frame_fragile(render):
    """A hand-written verbatim environment needs [fragile] just as much."""
    body = render('# S\n\n\\begin{verbatim}\nliteral\n\\end{verbatim}\n')
    assert '[fragile]' in body


def test_raw_environment_table_does_not_need_fragile(render):
    body = render('# S\n\n%s' % TABLE)
    assert 'fragile' not in body


###########################################
# Raw LaTeX: macro lines
###########################################

def test_macro_line_on_its_own(render):
    body = render('# S\n\ntext\n\n\\pausex\n\nmore\n')
    assert '\\pausex' in body


def test_macro_line_does_not_tear_a_list_apart(render):
    """A '\\pausex' at column 0 mid-list stays with the item above it."""
    body = render('# S\n\n* one\n* two\n\\pausex\n* three\n')
    assert body.count('\\begin{itemize}') == 1
    assert '\\pausex' in body


def test_macro_line_indented_in_a_list_item(render):
    body = render('# S\n\n* item\n\n    \\medskip\n\n* next\n')
    assert '\\medskip' in body
    assert body.count('\\begin{itemize}') == 1


def test_macro_line_is_not_a_paragraph_of_prose(render):
    """A line with a macro and prose is prose, not a macro line."""
    body = render('# S\n\n\\hlbl{pros}: and some words\n')
    assert '\\hlbl{pros}: and some words' in body


###########################################
# Environment directives: '@name ... @end'
###########################################

def test_directive_columns(render):
    body = render('# S\n\n@columns\n@column 0.3\nleft\n\n@column 0.7\nright\n'
                  '@end columns\n')
    assert '\\begin{columns}' in body
    assert body.count('\\begin{column}') == 2
    assert '\\begin{column}{0.3\\textwidth}' in body
    assert '\\begin{column}{0.7\\textwidth}' in body
    assert body.count('\\end{column}') == 2
    assert '\\end{columns}' in body


def test_directive_columns_are_top_aligned_by_default(render):
    """Without [T] beamer centres the columns against each other, so a short
column of code floats in the middle beside a tall table."""
    body = render('# S\n\n@columns\n@column 0.3\na\n@column 0.7\nb\n@end\n')
    assert '\\begin{columns}[T]' in body


@pytest.mark.parametrize('arguments, expected', [
    pytest.param('[c]', '\\begin{columns}[c]', id='explicit-centred'),
    pytest.param('[t]', '\\begin{columns}[t]', id='explicit-baseline'),
    pytest.param('<2->', '\\begin{columns}<2->', id='overlay-only'),
])
def test_directive_columns_default_can_be_overridden(render, arguments,
                                                     expected):
    body = render('# S\n\n@columns%s\n@column 0.5\na\n@end\n' % arguments)
    assert expected in body


def test_directive_default_arguments_apply_only_to_columns(render):
    body = render('# S\n\n@center\ntext\n@end\n')
    assert '\\begin{center}\n' in body


def test_directive_body_is_markdown(render):
    """The point of '@' over \\begin: the contents are still Markdown."""
    body = render('# S\n\n@column 0.5\n* **bold** item\n* $pc_1$\n@end\n')
    assert '\\begin{itemize}' in body
    assert '\\textbf{bold}' in body
    assert '$pc_1$' in body


def test_directive_begin_stays_verbatim(render):
    """...and the contents of \\begin{...} are still not."""
    body = render('# S\n\n\\begin{align}\n* **not** a list\n\\end{align}\n')
    assert '* **not** a list' in body
    assert '\\textbf' not in body


@pytest.mark.parametrize('source, expected', [
    pytest.param('0.3', '{0.3\\textwidth}', id='bare-number-is-a-fraction'),
    pytest.param('.5', '{.5\\textwidth}', id='leading-dot'),
    pytest.param('4cm', '{4cm}', id='a-length-is-passed-through'),
    pytest.param('{0.3\\textwidth}', '{0.3\\textwidth}', id='explicit-braces'),
])
def test_directive_width(render, source, expected):
    body = render('# S\n\n@column %s\ntext\n@end\n' % source)
    assert '\\begin{column}%s' % expected in body


@pytest.mark.parametrize('name, expected', [
    pytest.param('theorem', '\\begin{theorem}[Pumping lemma]', id='bracket'),
    pytest.param('lemma', '\\begin{lemma}[Pumping lemma]', id='another-bracket'),
    pytest.param('block', '\\begin{block}{Pumping lemma}', id='brace'),
    pytest.param('tcolorbox', '\\begin{tcolorbox}{Pumping lemma}',
                 id='unknown-defaults-to-brace'),
])
def test_directive_titles(render, name, expected):
    """theorem-likes take [title]; block-likes and the rest take {title}."""
    body = render('# S\n\n@%s Pumping lemma\ntext\n@end\n' % name)
    assert expected in body


def test_directive_title_may_hold_markdown(render):
    body = render('# S\n\n@block Results **so far**\ntext\n@end\n')
    assert '\\begin{block}{Results \\textbf{so far}}' in body


def test_directive_latex_arguments_are_not_touched(render):
    body = render('# S\n\n@block{Results **so far**}\ntext\n@end\n')
    assert '\\begin{block}{Results **so far**}' in body


@pytest.mark.parametrize('arguments, expected', [
    pytest.param('[t]{0.4\\textwidth}', '\\begin{minipage}[t]{0.4\\textwidth}',
                 id='two-arguments-in-order'),
    pytest.param('', '\\begin{minipage}\n', id='no-arguments'),
])
def test_directive_argument_passthrough(render, arguments, expected):
    body = render('# S\n\n@minipage%s\ntext\n@end\n' % arguments)
    assert expected in body


def test_directive_unknown_environment_needs_no_table_entry(render):
    body = render('# S\n\n@tcolorbox[colback=red]\n* item\n@end\n')
    assert '\\begin{tcolorbox}[colback=red]' in body
    assert '\\begin{itemize}' in body


@pytest.mark.parametrize('source, expected', [
    pytest.param('@block<2-> Later', '\\begin{block}<2->{Later}',
                 id='before-a-friendly-title'),
    pytest.param('@block<2->{Later}', '\\begin{block}<2->{Later}',
                 id='before-latex-arguments'),
    pytest.param('@block<2->', '\\begin{block}<2->\n', id='on-its-own'),
])
def test_directive_overlay(render, source, expected):
    assert expected in render('# S\n\n%s\ntext\n@end\n' % source)


def test_directive_command_form(render):
    """beamer spells a note as a macro, not an environment."""
    body = render('# S\n\n@note\nRemember **this**.\n@end\n')
    assert '\\note{' in body
    assert '\\textbf{this}' in body
    assert '\\begin{note}' not in body


###########################################
# Directives: how they close
###########################################

def test_directive_sibling_closes_the_previous_one(render):
    """A row of columns needs no @end between them."""
    body = render('# S\n\n@columns\n@column 0.5\na\n@column 0.5\nb\n@end\n')
    assert body.count('\\begin{column}') == 2
    assert body.count('\\end{column}') == 2


def test_directive_heading_closes_it(render):
    """No environment may reach past the end of its frame."""
    body = render('# One\n\n@column 0.5\ntext\n\n# Two\n\nmore\n')
    assert '\\end{column}' in body
    assert body.count('\\begin{frame}') == 2
    frames = body.split('\\begin{frame}')
    assert '\\end{column}' in frames[1]
    assert 'column' not in frames[2]


def test_directive_bare_end(render):
    body = render('# S\n\n@block T\ntext\n@end\n\nafter\n')
    assert '\\end{block}' in body
    assert 'after' in body


def test_directive_named_end(render):
    body = render('# S\n\n@block T\ntext\n@end block\n\nafter\n')
    assert '\\end{block}' in body
    assert 'after' in body


def test_directive_named_end_closes_what_is_open_inside_it(render):
    """'@end columns' closes a dangling column, the way </ul> does in HTML."""
    body = render('# S\n\n@columns\n@column 0.5\na\n@end columns\nafter\n')
    assert body.index('\\end{column}') < body.index('\\end{columns}')
    assert 'after' in body


def test_directive_same_name_nests_when_not_a_sibling(render):
    body = render('# S\n\n@block Outer\n@block Inner\ntext\n@end\n@end\n')
    assert body.count('\\begin{block}') == 2
    assert body.count('\\end{block}') == 2


def test_unterminated_environment_stops_at_the_next_heading(render, capsys):
    """It used to run to the end of the source, so every later heading became
literal text inside the environment and a whole deck came out as one frame."""
    body = render(doc("""
        # One

        \\begin{align}
        x &= y

        # Two

        second

        # Three

        third
    """))
    assert body.count('\\begin{frame}') == 3
    assert 'was never closed' in capsys.readouterr().err


def test_unterminated_environment_keeps_what_it_had(render, capsys):
    """What it did consume is still emitted verbatim -- unbalanced, which is
LaTeX's business to complain about, rather than silently invented."""
    body = render('# One\n\n\\begin{align}\nx &= y\n\n# Two\n\nsecond\n')
    assert '\\begin{align}\nx &= y' in body
    assert '\\end{align}' not in body
    capsys.readouterr()


@pytest.mark.parametrize('line', [
    pytest.param('# a shell comment', id='hash-space'),
    pytest.param('#!/bin/sh', id='shebang'),
    pytest.param('#include <stdio.h>', id='include'),
])
def test_verbatim_environment_is_not_closed_by_a_hash_line(render, capsys,
                                                           line):
    """A '# ' line inside a hand-written listing is a shell or Python comment,
not a heading, so only the matching \\end closes one of these."""
    body = render('# L\n\n\\begin{lstlisting}\n%s\n\\end{lstlisting}\n' % line)
    assert line in body
    assert '\\end{lstlisting}' in body
    assert 'never closed' not in capsys.readouterr().err


@pytest.mark.parametrize('line', [
    pytest.param('#include <stdio.h>', id='include'),
    pytest.param('#define N 10', id='define'),
])
def test_a_hash_without_a_space_is_not_a_heading(render, capsys, line):
    """So a C preprocessor line does not close even a non-verbatim one."""
    body = render('# S\n\n\\begin{align}\n%s\n\\end{align}\n' % line)
    assert line in body
    assert '\\end{align}' in body
    assert 'never closed' not in capsys.readouterr().err


def test_a_closed_environment_is_untouched_by_the_heading_rule(render, capsys):
    """The ordinary case, including a nested environment of the same name."""
    body = render(doc("""
        # S

        \\begin{center}
        \\begin{center}
        inner
        \\end{center}
        \\end{center}

        # T

        after
    """))
    assert body.count('\\begin{center}') == 2
    assert body.count('\\end{center}') == 2
    assert body.count('\\begin{frame}') == 2
    assert 'never closed' not in capsys.readouterr().err


###########################################
# a slide's own metadata block
###########################################

def test_slide_metadata_starts_a_frame_with_a_title(render):
    body = render(doc("""
        ===
        title: Why it grows
        ---

        alpha
    """))
    assert '\\begin{frame}{Why it grows}' in body
    assert body.count('\\begin{frame}') == 1


def test_slide_metadata_title_is_markdown(render):
    """The same answer a heading gives, which is the point of the key."""
    body = render('===\ntitle: Why it **grows** by $x_1$\n---\n\nalpha\n')
    assert '{Why it \\textbf{grows} by $x_1$}' in body


def test_slide_metadata_label_and_options(render):
    body = render('===\ntitle: T\nlabel: growth\noptions: [t, plain]\n---\n\na\n')
    assert '\\begin{frame}[t,plain,label=growth]{T}' in body


def test_slide_metadata_options_may_be_one_string(render):
    body = render('===\noptions: plain\n---\n\na\n')
    assert '\\begin{frame}[plain]' in body


@pytest.mark.parametrize('level', ['part', 'section', 'subsection'])
def test_slide_metadata_opens_a_sectioning_level(render, level):
    body = render('===\n%s: Part II\n---\n\n' % level)
    assert '\\%s{Part II}' % level in body
    assert '\\begin{frame}' not in body


def test_slide_metadata_closed_by_three_dots(render):
    body = render('===\ntitle: T\n...\n\nalpha\n')
    assert '\\begin{frame}{T}' in body


def test_a_break_without_a_closing_fence_is_still_a_break(render):
    """Which is the rule the document's own metadata block already follows."""
    body = render('# One\n\n---\n\nloose text\n')
    assert body.count('\\begin{frame}') == 2
    assert 'loose text' in body


def test_a_break_followed_by_unclosed_yaml_is_still_a_break(render):
    body = render('# One\n\n---\ntitle: never closed\n\nmore\n')
    assert 'title: never closed' in body
    assert '{never closed}' not in body


def test_slide_metadata_under_a_paragraph_is_a_setext_heading(render):
    """A '---' directly below a paragraph is CommonMark's setext underline and
is claimed before any of this; a blank line above the block avoids it."""
    body = render('Some title\n---\nkey: value\n---\n\nbody\n')
    assert '\\textbf{Some title}' in body
    assert '\\begin{frame}{value}' not in body


def test_slide_metadata_warns_about_a_key_it_does_not_know(render, capsys):
    """Only when the block is a block: it has to name something we know."""
    body = render('===\ntitle: T\nnosuchkey: 1\n---\n\nalpha\n')
    assert '\\begin{frame}{T}' in body
    err = capsys.readouterr().err
    assert 'nosuchkey' in err
    assert 'title' in err, 'the warning should say which block it is'


@pytest.mark.parametrize('block', [
    pytest.param('nosuchkey: 1', id='no-key-we-know'),
    pytest.param('- a\n- b', id='not-a-mapping'),
    pytest.param('title: [unclosed', id='bad-yaml'),
    pytest.param('# just a yaml comment', id='comment-only'),
])
def test_what_is_not_a_slide_block_stays_two_breaks(render, block):
    """A block is claimed only when the YAML is usable and names a setting we
know.  Anything else is a pair of thematic breaks with text between them,
which is what it was before this existed -- and eating that text is the one
mistake this feature must never make.

The frame count differs between these cases, because a '---' below a line of
text is CommonMark's setext underline; what matters is that nothing is lost
and that no frame is configured."""
    body = render('# One\n\n===\n%s\n---\n\nalpha\n' % block)
    assert 'alpha' in body
    assert '\\begin{frame}[' not in body, 'not settings, just text'
    if not block.startswith('#'):
        assert block.splitlines()[0] in body or 'a' in body


def test_two_breaks_keep_the_slide_between_them(render):
    """The shape of two thematic breaks is the shape of a block, and the
first cut of this ate the slide between them."""
    body = render(doc("""
        # One

        ---

        body two

        ---

        body three
    """))
    assert body.count('\\begin{frame}') == 3
    assert 'body two' in body
    assert 'body three' in body


def test_a_heading_between_two_breaks_survives(render):
    """'# B' is a YAML comment, so the eaten version was silent."""
    body = render('# A\n\n---\n\n# B\n\n---\n\n# C\n')
    assert body.count('\\begin{frame}') == 5
    for title in ('{A}', '{B}', '{C}'):
        assert title in body


def test_prose_between_breaks_is_not_promoted_to_settings(render):
    """Even when it parses as a mapping: it has to name a key we know."""
    body = render(doc("""
        # One

        ===
        Note: this is prose
        Also: so is this
        ---

        alpha
    """))
    assert 'Note: this is prose' in body
    assert '\\begin{frame}[' not in body


def test_a_break_inside_a_container_is_not_a_slide_block(render):
    """Source.expect_re matches the raw buffer, so without the top-level
guard the match ran straight through the end of a quote or a list item."""
    body = render(doc("""
        # One

        > quoted
        >
        > ===
        > title: not a slide
        > ---
        >
        > more quoted

        # Two

        after
    """))
    assert body.count('\\begin{frame}') == 2
    assert 'after' in body
    assert '\\begin{quote}' in body


def test_a_fenced_block_between_breaks_is_not_torn_apart(render):
    body = render(doc("""
        # One

        ---

        ```yaml
        ---
        title: My deck
        ---
        ```

        # Two

        after
    """))
    assert body.count('\\begin{frame}') == 3
    assert 'after' in body
    assert 'title: My deck' in body


def test_slide_metadata_itemsep_reaches_the_lists(render):
    body = render('===\nitemsep: 1.2em\n---\n\n* a\n* b\n')
    assert '\\tightlist\n\\setlength{\\itemsep}{1.2em}' in body


def test_slide_metadata_itemsep_reaches_a_nested_list(render):
    """Set on the renderer, so a list inside a directive is reached too."""
    body = render('===\nitemsep: 2em\n---\n\n@block T\n1. a\n2. b\n@end\n')
    assert '\\begin{enumerate}' in body
    assert '\\setlength{\\itemsep}{2em}' in body


def test_slide_metadata_itemsep_per_level(render):
    """A list gives the first, second, third nesting level."""
    body = render(doc("""
        ===
        itemsep: [1.2em, 0.6em, 0.2em]
        ---

        * one
            * two
                * three
    """))
    assert '\\begin{itemize}\n\\tightlist\n\\setlength{\\itemsep}{1.2em}' in body
    assert '\\setlength{\\itemsep}{0.6em}' in body
    assert '\\setlength{\\itemsep}{0.2em}' in body


def test_slide_metadata_itemsep_last_value_covers_deeper_levels(render):
    """Otherwise a two-item list would leave the third level unset, which is
never what naming two levels means."""
    body = render(doc("""
        ===
        itemsep: [1em, 2em]
        ---

        * one
            * two
                * three
                    * four
    """))
    assert body.count('\\setlength{\\itemsep}{2em}') == 3


def test_slide_metadata_itemsep_scalar_applies_to_every_level(render):
    """What a lone value has always meant, and must go on meaning."""
    body = render('===\nitemsep: 1em\n---\n\n* one\n    * two\n')
    assert body.count('\\setlength{\\itemsep}{1em}') == 2


def test_slide_metadata_itemsep_counts_every_kind_of_list(render):
    """An enumerate inside an itemize is the second level: that is what it
looks like on the slide, and what beamer sets with its second-level
template."""
    body = render('===\nitemsep: [1em, 2em]\n---\n\n* one\n    1. two\n')
    assert '\\begin{enumerate}\n\\tightlist\n\\setlength{\\itemsep}{2em}' in body


def test_slide_metadata_itemsep_depth_is_restored_between_slides(render):
    """The depth counter is renderer state, so a slide must not start one
level in because the last one ended there."""
    body = render(doc("""
        ===
        itemsep: [1em, 2em]
        ---

        * one
            * two

        ===
        itemsep: [1em, 2em]
        ---

        * one again
    """))
    assert body.count('\\setlength{\\itemsep}{1em}') == 2
    assert body.count('\\setlength{\\itemsep}{2em}') == 1


def test_slide_metadata_itemsep_does_not_leak_to_the_next_slide(render):
    body = render(doc("""
        ===
        itemsep: 2em
        ---

        * a

        # Next

        * b
    """))
    assert body.count('\\setlength{\\itemsep}') == 1


###########################################
# metadata values as Markdown
###########################################

@pytest.mark.parametrize('value, expected', [
    pytest.param('**Lecture 7**', '\\textbf{Lecture 7}', id='strong'),
    pytest.param('*Lecture* 7', '\\emph{Lecture} 7', id='emphasis'),
    pytest.param('Symbolic $x_1$', 'Symbolic $x_1$', id='maths'),
    pytest.param('\\textbf{raw}', '\\textbf{raw}', id='raw-latex'),
    pytest.param('==hot==', '\\hlbl{hot}', id='highlight'),
    # CommonMark forbids intraword '_' emphasis, so a name survives whole;
    # only a delimited one is emphasis, as it already was in a heading
    pytest.param('a_b_c', 'a_b_c', id='underscore-intraword'),
    pytest.param('a _b_ c', 'a \\emph{b} c', id='underscore-delimited'),
])
def test_metadata_title_is_markdown(mdslides, opts, value, expected):
    # single-quoted: YAML reads a '\\t' in a double-quoted scalar as a tab
    out = mdslides.convert("---\ntitle: '%s'\n---\n\n# S\n" % value,
                           '$title', opts())
    assert out == expected


def test_metadata_block_shaped_values_pass_through(mdslides, opts):
    """'1. Introduction' is a numbered title, not a list."""
    out = mdslides.convert("---\ntitle: '1. Introduction'\n---\n\n# S\n",
                           '$title', opts())
    assert out == '1. Introduction'


def test_metadata_author_list_items_are_markdown(mdslides, opts):
    out = mdslides.convert('---\nauthor: ["A *One*", "B"]\n---\n\n# S\n',
                           '$author', opts())
    assert out == 'A \\emph{One} \\and B'


def test_metadata_short_form_inherits_the_rendered_long_one(mdslides, opts):
    out = mdslides.convert("---\ntitle: '**T**'\n---\n\n# S\n",
                           '$shorttitle', opts())
    assert out == '\\textbf{T}'


@pytest.mark.parametrize('key, variable', [
    pytest.param('header-includes', '$headerincludes', id='header-includes'),
    pytest.param('theme', '$theme', id='theme'),
])
def test_metadata_that_is_not_prose_is_left_alone(mdslides, opts, key,
                                                  variable):
    """Only the values that become prose on a slide are parsed."""
    out = mdslides.convert("---\n%s: 'a _b_ c'\n---\n\n# S\n" % key,
                           variable, opts())
    assert out == 'a _b_ c'


def test_directive_stray_end_is_dropped_with_a_warning(render, capsys):
    body = render('# S\n\ntext\n@end\n')
    assert '@end' not in body
    assert 'nothing open' in capsys.readouterr().err


###########################################
# Directives: what is not a directive
###########################################

@pytest.mark.parametrize('text', [
    pytest.param('write to me @home tonight', id='mid-sentence'),
    pytest.param('@2x scaling', id='name-must-start-with-a-letter'),
])
def test_directive_not_recognized_in_prose(render, text):
    assert text in render('# S\n\n%s\n' % text)


def test_directive_inside_a_listing_is_left_alone(render):
    """The deck's algorithm slide has lines starting with '@'."""
    body = render('# S\n\n```C\n@end\n@column 0.3\n```\n')
    assert '@end' in body
    assert '@column 0.3' in body
    assert '\\begin{column}' not in body


def test_directive_listing_inside_makes_the_frame_fragile(render):
    body = render('# S\n\n@column 0.5\n\n```C\nx\n```\n@end\n')
    assert '[fragile]' in body


###########################################
# The renderer: the example presentation (conftest.EXAMPLE)
###########################################

def test_render_deck_produces_frames(mdslides, deck, render):
    _, body = mdslides.split_frontmatter(deck)
    result = render(body)
    # One frame per '#' heading, except that a heading opening a section
    # produces a separator slide instead of a frame of its own -- plus one
    # per slide declared by a metadata block, which has no heading at all.
    headings = [line for line in body.splitlines() if re.match(r'# \S', line)]
    separators = [line for line in headings
                  if mdslides.split_heading_attributes(line)[2]]
    blocks = len(mdslides.SLIDE_METADATA_RE.findall(body))
    assert separators, 'expected the example to have a section separator'
    assert blocks, 'expected the example to have a slide metadata block'
    assert (result.count('\\begin{frame}')
            == len(headings) - len(separators) + blocks)
    assert result.count('\\section{') == len(separators)
    assert result.count('\\begin{frame}') == result.count('\\end{frame}')


def test_render_deck_algorithm_listing_can_escape_to_maths(mdslides, deck,
                                                           render):
    """The algorithm slide is written as listings input, not as C."""
    _, body = mdslides.split_frontmatter(deck)
    assert '```lstlisting' in body, 'expected a raw listing in the deck'
    assert '[escapechar=@]' in render(body)


def test_template_settings_that_listings_needs(template):
    """Behaviour the real deck proved necessary, easy to delete by accident.

upquote: 'B' in a C listing came out as typographic quotes.
breaklines: long lines ran off the edge of the slide and were clipped.
"""
    assert 'upquote' in template
    assert 'breaklines=true' in template


def test_template_loads_xspace(template):
    """A macro in header-includes that wants the space after it kept
(\\newcommand{\\KLEE}{KLEE\\xspace}) needs the package loaded here, since
header-includes comes last and the deck cannot get in before it."""
    assert '\\usepackage{xspace}' in without_comments(template)


def test_render_deck_math_survives_verbatim(mdslides, deck, render):
    """Every maths span in the deck has to come out exactly as written."""
    _, body = mdslides.split_frontmatter(deck)
    result = render(body)
    # anything commented out is dropped on purpose, maths included
    visible = re.sub(r'<!--.*?-->', '', body, flags=re.S)
    spans = re.findall(r'(?<!\\)\$(?:[^$\n\\]|\\.)+?(?<!\\)\$', visible)
    assert len(spans) > 10, 'expected the example to be full of maths'
    assert [span for span in spans if span not in result] == []


def test_render_deck_table_survives_verbatim(mdslides, deck, render):
    """The tabularx table, '&' and '\\\\' and all."""
    _, body = mdslides.split_frontmatter(deck)
    result = render(body)
    table = re.search(r'\\begin\{tabularx\}.*?\\end\{tabularx\}', body, re.S)
    assert table, 'expected a tabularx table in the deck'
    assert table.group(0) in result


def test_render_deck_listings_all_have_a_frame_marked_fragile(mdslides, deck,
                                                              render):
    """Every listing has to sit in a frame that beamer will re-read."""
    _, body = mdslides.split_frontmatter(deck)
    for frame in render(body).split('\\begin{frame}')[1:]:
        if '\\begin{lstlisting}' in frame:
            assert frame.startswith('[fragile]') or \
                frame.startswith('[fragile,')


###########################################
# build_variables() -- metadata into template substitutions
###########################################

def test_variables_pass_metadata_through(mdslides):
    variables = mdslides.build_variables({'theme': 'Madrid'}, 'BODY')
    assert variables['theme'] == 'Madrid'
    assert variables['slides'] == 'BODY'


def test_variables_supply_defaults(mdslides):
    """Every variable the template may mention has to resolve to something."""
    variables = mdslides.build_variables({}, '')
    assert set(mdslides.TEMPLATE_DEFAULTS) <= set(variables)

    # These three are computed from the metadata rather than taken from the
    # defaults, and have tests of their own.
    computed = {'titlepage', 'sectionpages', 'toc'}
    for name, value in mdslides.TEMPLATE_DEFAULTS.items():
        if name not in computed:
            assert variables[name] == value


def test_variables_ignore_empty_metadata_entries(mdslides):
    """'titlegraphic:' with no value must not override a default."""
    variables = mdslides.build_variables({'theme': None}, '')
    assert variables['theme'] == mdslides.TEMPLATE_DEFAULTS['theme']


@pytest.mark.parametrize('key', ['author', 'institute'])
def test_variables_join_people_with_and(mdslides, key):
    variables = mdslides.build_variables({key: ['Jakub Havlík', 'Ondřej Lengál']}, '')
    assert variables[key] == 'Jakub Havlík \\and Ondřej Lengál'


@pytest.mark.parametrize('key', ['author', 'institute'])
def test_variables_accept_a_lone_name(mdslides, key):
    variables = mdslides.build_variables({key: 'Ondřej Lengál'}, '')
    assert variables[key] == 'Ondřej Lengál'


def test_variables_join_other_lists_with_newlines(mdslides):
    variables = mdslides.build_variables(
        {'header-includes': ['\\usepackage{listings}', '\\input{macros.tex}']}, '')
    assert variables['headerincludes'] == \
        '\\usepackage{listings}\n\\input{macros.tex}'


def test_variables_alias_hyphenated_keys(mdslides):
    """string.Template cannot reach '$header-includes'."""
    variables = mdslides.build_variables({'header-includes': 'X'}, '')
    assert variables['headerincludes'] == 'X'
    assert variables['header-includes'] == 'X'


@pytest.mark.parametrize('meta, expected', [
    pytest.param({}, 'dvipsnames', id='bare'),
    pytest.param({'aspectratio': 169}, 'dvipsnames,aspectratio=169',
                 id='aspectratio'),
    pytest.param({'fontsize': '10pt'}, 'dvipsnames,10pt', id='fontsize'),
    pytest.param({'fontsize': '10pt', 'aspectratio': 169},
                 'dvipsnames,10pt,aspectratio=169', id='both'),
    pytest.param({'classoption': ['handout', 'draft']},
                 'dvipsnames,handout,draft', id='extra-options'),
])
def test_variables_build_the_documentclass_options(mdslides, meta, expected):
    """One string, so that an absent option cannot leave a stray comma."""
    assert mdslides.build_variables(meta, '')['classoptions'] == expected


@pytest.mark.parametrize('short, long', [
    pytest.param('shorttitle', 'title', id='title'),
    pytest.param('shortauthor', 'author', id='author'),
    pytest.param('shortdate', 'date', id='date'),
])
def test_variables_short_forms_fall_back_to_the_long_ones(mdslides, short, long):
    variables = mdslides.build_variables({long: 'Long Form'}, '')
    assert variables[short] == 'Long Form'


def test_variables_short_institute_falls_back_to_the_institute(mdslides):
    """It appears in the footline beside the author, as it does in pandoc."""
    variables = mdslides.build_variables({'institute': 'Brno University'}, '')
    assert variables['shortinstitute'] == 'Brno University'


def test_variables_short_institute_can_be_given_explicitly(mdslides):
    variables = mdslides.build_variables(
        {'institute': 'Brno University of Technology', 'short-institute': 'BUT'},
        '')
    assert variables['shortinstitute'] == 'BUT'


@pytest.mark.parametrize('short, long, value', [
    pytest.param('shortinstitute', 'institute', 'FIT VUT', id='institute'),
    pytest.param('shorttitle', 'title', 'A Long Title', id='title'),
    pytest.param('shortauthor', 'author', 'Ondřej Lengál', id='author'),
    pytest.param('shortdate', 'date', '3 November 2025', id='date'),
])
def test_variables_an_empty_short_form_is_kept(mdslides, short, long, value):
    """'short-institute: ""' is how a deck says "leave the affiliation out
of the footline"; falling back to the long form would do the opposite."""
    key = short.replace('short', 'short-')
    variables = mdslides.build_variables({long: value, key: ''}, '')
    assert variables[short] == ''


@pytest.mark.parametrize('key', ['short-institute', 'shortinstitute'])
def test_variables_short_form_spelling(mdslides, key):
    """Hyphenated or not, the deck's own value is what counts."""
    variables = mdslides.build_variables({'institute': 'FIT VUT', key: ''}, '')
    assert variables['shortinstitute'] == ''


def test_variables_a_valueless_short_form_still_falls_back(mdslides):
    """'short-institute:' with nothing after it is YAML None, not an empty
string, and reads as "not given"."""
    variables = mdslides.build_variables(
        {'institute': 'FIT VUT', 'short-institute': None}, '')
    assert variables['shortinstitute'] == 'FIT VUT'


def test_convert_empty_short_institute_reaches_the_document(convert):
    result = convert('---\ntitle: T\ninstitute: "FIT VUT"\n'
                     'short-institute: ""\n---\n\n# S\nx\n')
    assert '\\institute[]{FIT VUT}' in result


@pytest.mark.parametrize('key', ['short-title', 'shorttitle'])
def test_variables_explicit_short_form_wins(mdslides, key):
    variables = mdslides.build_variables({'title': 'Long', key: 'Short'}, '')
    assert variables['shorttitle'] == 'Short'


###########################################
# as_bool() -- metadata flags, which -V can only give us as strings
###########################################

@pytest.mark.parametrize('value, expected', [
    pytest.param(True, True, id='yaml-true'),
    pytest.param(False, False, id='yaml-false'),
    pytest.param('true', True, id='string-true'),
    pytest.param('false', False, id='string-false'),
    pytest.param('no', False, id='no'),
    pytest.param('off', False, id='off'),
    pytest.param('0', False, id='zero'),
    pytest.param('', False, id='empty'),
    pytest.param('  FALSE  ', False, id='case-and-space'),
    pytest.param('yes', True, id='yes'),
    pytest.param('1', True, id='one'),
])
def test_as_bool(mdslides, value, expected):
    assert mdslides.as_bool(value) is expected


@pytest.mark.parametrize('default', [True, False])
def test_as_bool_default_for_absent(mdslides, default):
    assert mdslides.as_bool(None, default) is default


###########################################
# The title page
###########################################

TITLEPAGE = '\\frame{\\titlepage}'


def test_titlepage_is_added_when_there_is_a_title(mdslides):
    assert mdslides.build_variables({'title': 'T'}, '')['titlepage'] == TITLEPAGE


def test_titlepage_is_absent_without_a_title(mdslides):
    """Nothing to put on one, so an empty title frame is not produced."""
    assert mdslides.build_variables({}, '')['titlepage'] == ''


@pytest.mark.parametrize('value', [False, 'false', 'no', '0'])
def test_titlepage_can_be_switched_off(mdslides, value):
    variables = mdslides.build_variables({'title': 'T', 'titlepage': value}, '')
    assert variables['titlepage'] == ''


def test_titlepage_can_be_forced_without_a_title(mdslides):
    variables = mdslides.build_variables({'titlepage': True}, '')
    assert variables['titlepage'] == TITLEPAGE


def test_subtitle_reaches_the_document(convert):
    """A lecture deck puts the lesson in the title and the course here."""
    result = convert('---\ntitle: "Symbolic Execution"\n'
                     'subtitle: "SAV --- Static Analysis"\n---\n\n# S\nx\n')
    assert '\\subtitle{SAV --- Static Analysis}' in result


def test_subtitle_is_empty_when_not_given(convert):
    """Beamer skips an empty subtitle, so the command is emitted anyway
rather than being made conditional."""
    assert '\\subtitle{}' in convert('---\ntitle: T\n---\n\n# S\nx\n')


def test_subtitle_may_hold_latex(convert):
    result = convert('---\ntitle: T\nsubtitle: "Lecture $7$: \\\\emph{x}"\n'
                     '---\n\n# S\nx\n')
    assert '\\subtitle{Lecture $7$: \\emph{x}}' in result


def test_titlepage_reaches_the_document(convert):
    result = convert('---\ntitle: T\nauthor: A\n---\n\n# Slide\n')
    assert TITLEPAGE in result
    assert result.index(TITLEPAGE) < result.index('\\begin{frame}')


def test_titlepage_switched_off_from_the_command_line(convert):
    """-V gives a string, which must not be read as a non-empty truth."""
    result = convert('---\ntitle: T\n---\n\n# Slide\n',
                     variable={'titlepage': 'false'})
    assert TITLEPAGE not in result


def test_titlepage_in_the_deck(mdslides, deck, template, opts):
    result = mdslides.convert(deck, template, opts())
    assert TITLEPAGE in result


###########################################
# convert() -- the whole pipeline, with the template applied
###########################################

def test_convert_produces_a_complete_document(convert):
    result = convert('# Slide\n')
    assert '\\documentclass' in result
    assert '\\begin{document}' in result
    assert '\\end{document}' in result


def test_convert_metadata_reaches_the_template(convert):
    result = convert('---\naspectratio: 169\ntitle: T\n---\n\n# Slide\n')
    assert 'aspectratio=169' in result


def test_convert_fills_the_slides_placeholder(convert):
    """Whatever render_slides() returns has to land in the document."""
    assert '$slides' not in convert('# Slide\n')


def test_convert_command_line_variables_override_the_metadata(convert):
    result = convert('---\ntitle: FromMetadata\n---\n\n# Slide\n',
                     variable={'title': 'FromCommandLine'})
    assert 'FromCommandLine' in result
    assert 'FromMetadata' not in result


def test_convert_leaves_unknown_placeholders_alone(mdslides, opts):
    """safe_substitute(): a variable we cannot fill is not fatal."""
    result = mdslides.convert('# Slide\n', 'a $nosuchvariable b $slides', opts())
    assert '$nosuchvariable' in result


def test_shipped_template_is_fully_substituted(mdslides, deck, template):
    """No '$name' may reach LaTeX, where it would be read as maths.

Rendered with an empty body on purpose: once the renderer emits real slides
they will contain $maths$, which is not what this test is about.
"""
    meta, _ = mdslides.split_frontmatter(deck)
    filled = string.Template(template).safe_substitute(
        mdslides.build_variables(meta, ''))
    assert re.findall(r'\$[A-Za-z_]\w*', filled) == []


def test_shipped_template_is_substituted_without_any_metadata(mdslides, template):
    """The defaults have to cover a document with no metadata block at all."""
    filled = string.Template(template).safe_substitute(
        mdslides.build_variables({}, ''))
    assert re.findall(r'\$[A-Za-z_]\w*', filled) == []


def test_convert_dump_ast_goes_to_stderr_only(convert, capsys):
    result = convert('# Slide\n', dump_ast=True)
    assert 'Heading' in capsys.readouterr().err
    assert 'Heading' not in result


def test_convert_is_quiet_without_dump_ast(convert, capsys):
    convert('# Slide\n')
    assert capsys.readouterr().err == ''


###########################################
# The committed deck, end to end
#
# Assertions read values out of the parsed metadata rather than hard-coding
# strings, so editing the deck does not break the tests.
###########################################

def test_deck_metadata_is_parsed(mdslides, deck):
    meta, _ = mdslides.split_frontmatter(deck)
    assert isinstance(meta['aspectratio'], int)
    assert '\\usepackage{listings}' in meta['header-includes']


def test_deck_commented_out_metadata_is_dropped(mdslides, deck):
    """The deck disables 'lang' with an HTML comment."""
    assert '<!--lang:' in deck
    meta, _ = mdslides.split_frontmatter(deck)
    assert 'lang' not in meta


def test_deck_body_lines_keep_their_numbers(mdslides, deck):
    _, body = mdslides.split_frontmatter(deck)
    original = deck.splitlines()
    assert len(body.splitlines()) == len(original)
    for number, line in enumerate(body.splitlines()):
        if line.strip():
            assert line == original[number], 'line %d moved' % (number + 1)


def test_deck_metadata_is_gone_from_the_body(mdslides, deck):
    _, body = mdslides.split_frontmatter(deck)
    assert 'header-includes' not in body


def test_deck_converts_to_a_document(mdslides, deck, template, opts):
    meta, _ = mdslides.split_frontmatter(deck)
    result = mdslides.convert(deck, template, opts())
    assert '\\documentclass' in result
    assert str(meta['aspectratio']) in result
    assert meta['title'] in result


###########################################
# Does the output actually compile?
#
# The unit tests above check what we emit; only LaTeX can say whether it is
# valid. Skipped where pdflatex is not installed, so the suite still needs
# nothing but the standard library.
###########################################

pdflatex_needed = pytest.mark.skipif(shutil.which('pdflatex') is None,
                                     reason='pdflatex is not installed')

def png_bytes(size=8):
    """A valid PNG, so that a figure has something real to include."""
    def chunk(kind, data):
        body = kind + data
        return (struct.pack('>I', len(data)) + body
                + struct.pack('>I', zlib.crc32(body)))

    header = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    rows = b''.join(b'\x00' + bytes([200, 120, 60]) * size
                    for _ in range(size))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', header)
            + chunk(b'IDAT', zlib.compress(rows))
            + chunk(b'IEND', b''))


def compile_latex(directory, text, script):
    """Run mdslides on `text' and pdflatex on the result."""
    (directory / 'f.png').write_bytes(png_bytes())
    source = directory / 'deck.md'
    source.write_text(text, encoding='utf-8')
    done = run(script, str(source), '-o', str(directory / 'deck.tex'))
    assert done.returncode == 0, done.stderr

    done = subprocess.run(
        ['pdflatex', '-interaction=nonstopmode', 'deck.tex'],
        cwd=directory, capture_output=True, encoding='utf-8', errors='replace')
    log = (directory / 'deck.log').read_text(encoding='utf-8', errors='replace')
    return done, log


@pdflatex_needed
def test_compiles_everything_we_emit(tmp_path, script):
    """One document exercising every construct the renderer knows."""
    document = doc("""
        ---
        title: "Compile test"
        author: "Ondřej Lengál"
        theme: "Madrid"
        aspectratio: 169
        header-includes: |
          \\providecommand{\\hlbl}[1]{\\textbf{#1}}
        ---

        # Lists and text
        * **bold**, *emphasis*, `a_b` and \\hlbl{a macro}
        * maths: $pc_1 \\land pc_2$ and $\\mathbb{T}$
        \\pausex
        * a~non-breaking space

        # A listing {.fragile}
        ```C
        if (input[i] == 'B') { ++counter; }
        ```

        # Columns
        @columns
        @column 0.4
        * left
        @column 0.6
        \\begin{tabular}{|c|c|}
          \\hline
          $a$ & $b$ \\\\
          \\hline
        \\end{tabular}
        @end columns

        # Environments
        @theorem Pumping lemma
        For every **regular** language $L$ ...
        @end

        @block Results **so far**
        Fine.
        @end

        # A figure
        ![A **captioned** figure](f.png){width=0.4}

        # Display maths
        $$ x = y $$
    """)
    done, log = compile_latex(tmp_path, document, script)
    errors = [line for line in log.splitlines() if line.startswith('!')]
    assert errors == [], '\n'.join(errors)
    assert (tmp_path / 'deck.pdf').exists()


@pdflatex_needed
def test_the_deck_compiles(tmp_path, script, deck, deck_path):
    """The example presentation, end to end."""
    done, log = compile_latex(tmp_path, deck, script)
    errors = [line for line in log.splitlines() if line.startswith('!')]
    assert errors == [], '\n'.join(errors)
    assert (tmp_path / 'deck.pdf').exists()
    assert re.search(r'Output written .* \((\d+) pages', log)


###########################################
# The script as a command: shebang, wiring, exit codes
###########################################

def run(script, *argv, stdin=None):
    """Run the script as a command.  UTF-8 explicitly, so that the non-ASCII
    test exercises the script rather than the locale of whoever runs pytest.
    """
    return subprocess.run([script] + list(argv), input=stdin,
                          capture_output=True, encoding='utf-8')


def test_cli_is_executable(script):
    assert os.access(script, os.X_OK), 'mdslides is not executable'


def test_cli_version(script, mdslides):
    done = run(script, '--version')
    assert done.returncode == 0
    assert mdslides.VERSION in done.stdout


def test_cli_help_lists_the_options(script):
    done = run(script, '--help')
    assert done.returncode == 0
    for option in ('--output', '--template', '--variable', '--slide-level',
                   '--dump-ast', '--escapechar', '--pdf'):
        assert option in done.stdout


def test_cli_converts_the_deck(script, deck_path):
    done = run(script, deck_path)
    assert done.returncode == 0, done.stderr
    assert '\\begin{document}' in done.stdout
    assert done.stderr == ''


def test_cli_reads_stdin(script):
    done = run(script, stdin='---\ntitle: T\n---\n\n# Slide\n')
    assert done.returncode == 0, done.stderr
    assert '\\documentclass' in done.stdout


def test_cli_writes_to_a_file(script, deck_path, tmp_path):
    out = tmp_path / 'out.tex'
    done = run(script, deck_path, '-o', str(out))
    assert done.returncode == 0, done.stderr
    assert done.stdout == ''
    assert '\\end{document}' in out.read_text(encoding='utf-8')


def test_cli_dump_ast_keeps_stdout_clean(script, deck_path):
    done = run(script, '-d', deck_path)
    assert done.returncode == 0, done.stderr
    assert 'Heading' in done.stderr
    assert '\\documentclass' in done.stdout


def test_cli_explicit_dash_reads_stdin(script):
    done = run(script, '-', stdin='# Slide\n')
    assert done.returncode == 0, done.stderr
    assert '\\documentclass' in done.stdout


def test_cli_unwritable_output_is_an_error(script, deck_path, tmp_path):
    done = run(script, deck_path, '-o', str(tmp_path / 'no' / 'such' / 'o.tex'))
    assert done.returncode == 2
    assert 'cannot open' in done.stderr


@pytest.mark.parametrize('source', ['stdin', 'file'])
def test_cli_handles_non_ascii(script, tmp_path, source):
    """UTF-8 whatever the locale says; FileType used the locale encoding."""
    text = '---\ntitle: "Ondřej Lengál"\n---\n\n# Přehled\n'
    if source == 'stdin':
        done = run(script, stdin=text)
    else:
        deck = tmp_path / 'deck.md'
        deck.write_text(text, encoding='utf-8')
        done = run(script, str(deck))
    assert done.returncode == 0, done.stderr
    assert 'Ondřej Lengál' in done.stdout


###########################################
# --pdf
###########################################

class FakeRun:
    """Stands in for subprocess.run, recording the commands asked for."""

    def __init__(self, returncode=0):
        self.commands = []
        self.returncode = returncode

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        return subprocess.CompletedProcess(command, self.returncode)


def test_latex_prefers_latexmk(mdslides, monkeypatch, tmp_path):
    """latexmk works out for itself how many passes are needed."""
    monkeypatch.setattr(mdslides.shutil, 'which',
                        lambda name: '/bin/' + name if name == 'latexmk' else None)
    fake = FakeRun()
    monkeypatch.setattr(mdslides.subprocess, 'run', fake)
    assert mdslides.run_latex(str(tmp_path / 'deck.tex')) == 0
    assert len(fake.commands) == 1
    assert fake.commands[0][0] == 'latexmk'


def test_latex_falls_back_to_two_pdflatex_passes(mdslides, monkeypatch,
                                                 tmp_path):
    """beamer needs a second pass before its counters settle."""
    monkeypatch.setattr(mdslides.shutil, 'which',
                        lambda name: '/bin/' + name if name == 'pdflatex' else None)
    fake = FakeRun()
    monkeypatch.setattr(mdslides.subprocess, 'run', fake)
    assert mdslides.run_latex(str(tmp_path / 'deck.tex')) == 0
    assert [c[0] for c in fake.commands] == ['pdflatex', 'pdflatex']


def test_latex_without_an_engine_is_reported(mdslides, monkeypatch, capsys,
                                             tmp_path):
    monkeypatch.setattr(mdslides.shutil, 'which', lambda name: None)
    assert mdslides.run_latex(str(tmp_path / 'deck.tex')) == 1
    assert 'neither latexmk nor pdflatex' in capsys.readouterr().err


def test_latex_stops_at_the_first_failing_pass(mdslides, monkeypatch, tmp_path):
    monkeypatch.setattr(mdslides.shutil, 'which',
                        lambda name: '/bin/' + name if name == 'pdflatex' else None)
    fake = FakeRun(returncode=1)
    monkeypatch.setattr(mdslides.subprocess, 'run', fake)
    assert mdslides.run_latex(str(tmp_path / 'deck.tex')) == 1
    assert len(fake.commands) == 1, 'should not run again after a failure'


def test_pdf_needs_somewhere_to_write(script):
    """A PDF cannot be made out of stdout."""
    done = run(script, '--pdf', stdin='# S\n')
    assert done.returncode == 2
    assert '--pdf needs -o FILE' in done.stderr


def test_pdf_derives_the_output_name_from_the_input(mdslides, tmp_path,
                                                    monkeypatch):
    source = tmp_path / 'talk.md'
    source.write_text('# S\n', encoding='utf-8')
    args = mdslides.parse_args(['--pdf', str(source)])
    args.template.close()
    mdslides.discard_output(args)
    # not args.output.name: the handle is the temporary file it is written to
    assert args.output_path == str(tmp_path / 'talk.tex')


def test_pdf_keeps_an_explicit_output_name(mdslides, tmp_path):
    source = tmp_path / 'talk.md'
    source.write_text('# S\n', encoding='utf-8')
    args = mdslides.parse_args(['--pdf', str(source), '-o',
                                str(tmp_path / 'other.tex')])
    args.template.close()
    mdslides.discard_output(args)
    assert args.output_path == str(tmp_path / 'other.tex')


@pdflatex_needed
def test_pdf_builds_a_pdf_in_one_command(script, tmp_path):
    (tmp_path / 'f.png').write_bytes(png_bytes())
    source = tmp_path / 'deck.md'
    source.write_text(doc("""
        ---
        title: "One command"
        aspectratio: 169
        ---

        # A slide
        * text and $x_1$

        # A listing
        ```C
        int main(void) { return 0; }
        ```
    """), encoding='utf-8')
    done = run(script, '--pdf', str(source))
    assert done.returncode == 0, done.stderr
    assert (tmp_path / 'deck.tex').exists()
    assert (tmp_path / 'deck.pdf').exists()


@pdflatex_needed
def test_pdf_reports_latex_errors_and_fails(script, tmp_path):
    source = tmp_path / 'bad.md'
    source.write_text(doc("""
        ---
        title: T
        header-includes: |
          \\usepackage{nosuchpackageexists}
        ---

        # S
        text
    """), encoding='utf-8')
    done = run(script, '--pdf', str(source))
    assert done.returncode != 0
    assert 'nosuchpackageexists' in done.stderr
    assert 'bad.log' in done.stderr


def test_a_failed_conversion_leaves_the_previous_output_alone(script,
                                                              tmp_path):
    """The output used to be opened -- and so truncated -- in parse_args,
before a byte of the input was read, so a document that failed to convert
replaced the previous .tex with an empty one."""
    source = tmp_path / 'deck.md'
    source.write_text('---\ntitle: [unclosed\n---\n\n# S\n', encoding='utf-8')
    out = tmp_path / 'deck.tex'
    out.write_text('PREVIOUS\n', encoding='utf-8')
    done = run(script, str(source), '-o', str(out))
    assert done.returncode == 1
    assert out.read_text(encoding='utf-8') == 'PREVIOUS\n'


def test_a_failed_conversion_leaves_no_output_and_no_litter(script, tmp_path):
    """And when there was no previous file, it does not create one -- nor
leave the temporary file it wrote to behind."""
    source = tmp_path / 'deck.md'
    source.write_text('---\ntitle: [unclosed\n---\n\n# S\n', encoding='utf-8')
    done = run(script, str(source), '-o', str(tmp_path / 'deck.tex'))
    assert done.returncode == 1
    assert not (tmp_path / 'deck.tex').exists()
    assert sorted(f.name for f in tmp_path.iterdir()) == ['deck.md']


def test_the_output_keeps_the_mode_of_the_file_it_replaces(script, tmp_path):
    """A temporary file is created 0600; replacing a 0644 .tex with one would
be a quiet regression."""
    source = tmp_path / 'deck.md'
    source.write_text('# S\n', encoding='utf-8')
    out = tmp_path / 'deck.tex'
    out.write_text('old\n', encoding='utf-8')
    out.chmod(0o640)
    done = run(script, str(source), '-o', str(out))
    assert done.returncode == 0, done.stderr
    assert stat.S_IMODE(out.stat().st_mode) == 0o640


def test_a_new_output_is_readable(script, tmp_path):
    """And a file that did not exist gets what a plain open() would have
given it, not 0600."""
    source = tmp_path / 'deck.md'
    source.write_text('# S\n', encoding='utf-8')
    out = tmp_path / 'deck.tex'
    done = run(script, str(source), '-o', str(out))
    assert done.returncode == 0, done.stderr
    assert stat.S_IMODE(out.stat().st_mode) & 0o044


def test_pdf_refuses_to_write_over_its_own_input(script, tmp_path):
    """'mdslides --pdf deck.tex' used to destroy deck.tex: the output name is
the input with its extension replaced, and opening the output truncates it
before a byte of the input is read."""
    source = tmp_path / 'deck.tex'
    source.write_text('PRECIOUS\n', encoding='utf-8')
    done = run(script, '--pdf', str(source))
    assert done.returncode == 2
    assert 'is the input file' in done.stderr
    assert source.read_text(encoding='utf-8') == 'PRECIOUS\n'


def test_output_refuses_to_write_over_its_own_input(script, tmp_path):
    """The same guard without --pdf, where -o names the input."""
    source = tmp_path / 'deck.md'
    source.write_text('# S\n', encoding='utf-8')
    done = run(script, str(source), '-o', str(source))
    assert done.returncode == 2
    assert 'is the input file' in done.stderr
    assert source.read_text(encoding='utf-8') == '# S\n'


def test_output_may_be_a_different_file(script, tmp_path):
    """The guard must not fire on ordinary use."""
    source = tmp_path / 'deck.md'
    source.write_text('# S\n', encoding='utf-8')
    done = run(script, str(source), '-o', str(tmp_path / 'deck.tex'))
    assert done.returncode == 0, done.stderr
    assert (tmp_path / 'deck.tex').exists()


def test_file_line_errors_are_reported(mdslides, tmp_path, capsys):
    """run_latex() passes -file-line-error, so an error with a line to blame
is rewritten as './deck.tex:150: ...' and does not start with '!'.  Matching
only '!' is how an undefined macro used to produce no message at all."""
    log = tmp_path / 'deck.log'
    log.write_text(doc("""
        This is pdfTeX, Version 3.141592653
        (./deck.tex
        LaTeX2e <2024-11-01>
        ./deck.tex:150: Undefined control sequence.
        l.150 \\nosuchmacro
        ! LaTeX Error: File `nope.sty' not found.
        (/usr/share/texlive/texmf-dist/tex/latex/base/size11.clo)
        Package hyperref Info: Option `colorlinks' set `true' on input line 12.
    """), encoding='utf-8')
    mdslides.report_latex_errors(str(log))
    err = capsys.readouterr().err
    assert './deck.tex:150: Undefined control sequence.' in err
    assert "! LaTeX Error: File `nope.sty' not found." in err
    # ordinary chatter must not be mistaken for an error
    assert 'size11.clo' not in err
    assert 'hyperref Info' not in err


@pytest.mark.parametrize('argv, code', [
    pytest.param(['-V', 'oops'], 2, id='malformed-variable'),
    pytest.param(['/no/such/deck.md'], 2, id='missing-input'),
    pytest.param(['-t', '/no/such/template.tpl'], 2, id='missing-template'),
])
def test_cli_bad_usage_exits_with_2(script, argv, code):
    assert run(script, *argv).returncode == code
