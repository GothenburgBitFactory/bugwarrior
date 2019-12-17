import importlib

from docutils import nodes
from docutils.parsers.rst import Directive

TYPES = {
    'string': 'Text (string)',
    'numeric': 'Number (numeric)',
    'date': 'Date & Time (date)',
}


class UDAs(Directive):
    required_arguments = 1
    has_content = True

    def run(self):

        package = '.'.join(self.arguments[0].split('.')[:-1])
        klass = self.arguments[0].split('.')[-1]

        pkg = importlib.import_module(package)
        klass = getattr(pkg, klass)
        table = nodes.table()
        tgroup = nodes.tgroup()
        table += tgroup
        tgroup += nodes.colspec(colwidth=33)
        tgroup += nodes.colspec(colwidth=33)
        tgroup += nodes.colspec(colwidth=33)
        thead = nodes.thead()
        tgroup += thead
        thead += mkrow('Field Name', 'Description', 'Type')
        tbody = nodes.tbody()
        tgroup += tbody
        for uda, uda_attrs in sorted(klass.UDAS.items()):
            label = uda_attrs['label']
            type = uda_attrs['type']
            if type in TYPES:
                type = TYPES[type]
            tbody += mkrow(nodes.literal(text=uda), label, type)
        return [table]


def mkrow(*args):
    row = nodes.row()
    for arg in args:
        entry = nodes.entry()
        entry += nodes.paragraph(text=arg) if isinstance(arg, str) else arg
        row += entry
    return row


def setup(app):
    app.add_directive("udas", UDAs)
