"""Tests for mdslides.

    pytest                              # everything
    pytest -k frontmatter               # one area
    pytest -v                           # per-test names
"""

import subprocess
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
    import sys
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


def test_convert_leaves_unknown_placeholders_alone(convert):
    """safe_substitute(): a variable we cannot fill yet is not fatal."""
    assert '$shorttitle' in convert('# Slide\n')


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
    return subprocess.run([script] + list(argv), input=stdin,
                          capture_output=True, text=True)


def test_cli_is_executable(script):
    import os
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


@pytest.mark.parametrize('argv, code', [
    pytest.param(['-V', 'oops'], 2, id='malformed-variable'),
    pytest.param(['/no/such/deck.md'], 2, id='missing-input'),
    pytest.param(['-t', '/no/such/template.tpl'], 2, id='missing-template'),
])
def test_cli_bad_usage_exits_with_2(script, argv, code):
    assert run(script, *argv).returncode == code
