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
DECK = os.path.join(ROOT, 'simplified.md')


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
def deck_path():
    return DECK


@pytest.fixture(scope='session')
def deck():
    """The committed presentation, as an end-to-end fixture."""
    return _read(DECK)


@pytest.fixture
def opts():
    """Factory for a stand-in of the parsed command line options."""
    def make(**overrides):
        values = {'dump_ast': False, 'slide_level': 1, 'variable': {}}
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
