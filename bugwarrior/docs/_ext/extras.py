import pathlib

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

try:
    import tomllib  # python>=3.11
except ImportError:
    import tomli as tomllib  # backport


class Extras(SphinxDirective):
    """List extra dependency groups."""

    optional_arguments = 0
    has_content = False

    def run(self) -> list[nodes.Node]:
        with open(pathlib.Path(__file__).parent / '../../../pyproject.toml', 'rb') as f:
            pyproject = tomllib.load(f)
        list_node = nodes.bullet_list()
        for extra in pyproject['project']['optional-dependencies'].keys():
            list_node.append(nodes.list_item('', nodes.paragraph(text=extra)))
        return [list_node]


def setup(app):
    app.add_directive('extras', Extras)
