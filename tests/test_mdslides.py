"""Tests for mdslides.

    pytest                              # everything
    pytest -k frontmatter               # one area
    pytest -v                           # per-test names
"""

import os
import re
import string
import subprocess
import sys
import textwrap

import pytest


def doc(text):
    """doc(str) -> str: a readable inline document fixture."""
    return textwrap.dedent(text).lstrip('\n')


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
    pytest.param('Plain', ('Plain', []), id='no-attributes'),
    pytest.param('Algorithm {.fragile}', ('Algorithm', ['fragile']),
                 id='fragile'),
    pytest.param('T {.plain .allowframebreaks}',
                 ('T', ['plain', 'allowframebreaks']), id='two-classes'),
    pytest.param('T {label=intro}', ('T', ['label=intro']), id='key-value'),
    pytest.param('T {#intro}', ('T', ['label=intro']), id='identifier'),
    pytest.param('T {.nosuchoption}', ('T', []), id='unknown-class-dropped'),
    # a title may legitimately end in a braced LaTeX group
    pytest.param('A \\hlbl{Foo}', ('A \\hlbl{Foo}', []), id='latex-group'),
    pytest.param('\\texttt{x}', ('\\texttt{x}', []), id='only-a-latex-group'),
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


def test_render_block_quote(render):
    assert '\\begin{quote}' in render('# S\n\n> quoted\n')


def test_render_html_comments_are_dropped(render):
    """This is how the deck's commented-out slides disappear."""
    result = render('# S\n\n<!-- a comment -->\n\ntext\n')
    assert 'comment' not in result
    assert 'text' in result


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


def test_render_link(render):
    assert '\\href{http://x.org}{text}' in render('# S\n\n[text](http://x.org)\n')


def test_render_image(render):
    assert '\\includegraphics{fig.png}' in render('# S\n\n![](fig.png)\n')


###########################################
# The renderer: the committed deck
###########################################

def test_render_deck_produces_frames(mdslides, deck, render):
    _, body = mdslides.split_frontmatter(deck)
    result = render(body)
    # one frame per '#' heading in the source
    headings = len([line for line in body.splitlines()
                    if re.match(r'# \S', line)])
    assert result.count('\\begin{frame}') == headings
    assert result.count('\\begin{frame}') == result.count('\\end{frame}')


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
    variables = mdslides.build_variables({}, '')
    for name, value in mdslides.TEMPLATE_DEFAULTS.items():
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


def test_variables_short_institute_defaults_to_empty(mdslides):
    """The footline is cramped and a full affiliation rarely fits."""
    variables = mdslides.build_variables({'institute': 'Brno University'}, '')
    assert variables['shortinstitute'] == ''


@pytest.mark.parametrize('key', ['short-title', 'shorttitle'])
def test_variables_explicit_short_form_wins(mdslides, key):
    variables = mdslides.build_variables({'title': 'Long', key: 'Short'}, '')
    assert variables['shorttitle'] == 'Short'


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
                   '--dump-ast'):
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


@pytest.mark.parametrize('argv, code', [
    pytest.param(['-V', 'oops'], 2, id='malformed-variable'),
    pytest.param(['/no/such/deck.md'], 2, id='missing-input'),
    pytest.param(['-t', '/no/such/template.tpl'], 2, id='missing-template'),
])
def test_cli_bad_usage_exits_with_2(script, argv, code):
    assert run(script, *argv).returncode == code
