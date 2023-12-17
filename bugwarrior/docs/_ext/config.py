from ini2toml.api import Translator
from sphinx.util.docutils import SphinxDirective
from sphinx.directives.code import CodeBlock
from sphinx_inline_tabs._impl import TabDirective


class Config(SphinxDirective):
    optional_arguments = 1
    option_spec = {'fragment': str}  # section schema to stub
    has_content = True

    def _make_tab(self, lang: str):
        self.arguments = [lang]
        tab = TabDirective.run(self)[0]
        tab[1][0] = CodeBlock.run(self)[0]
        # While line breaks were previously separate elements, they're now
        # within the single CodeBlock element.
        del tab[1][1:]
        return tab

    def run(self):
        self.assert_has_content()

        ini = self._make_tab('ini')
        initext = '\n'.join(self.content)

        if 'fragment' in self.options:  # add stub
            stub_section = (
                '[some_section]\nservice = ' + self.options['fragment'] + '\n')
            initext = stub_section + initext
        tomltext = Translator().translate(initext, 'bugwarriorrc')
        if 'fragment' in self.options:  # remove stub
            stub_len = len(stub_section) + 2  # toml adds quotes to strings
            tomltext = tomltext[stub_len:]

        tomllines = tomltext.split('\n')
        for i in range(0, len(self.content)):  # mutate self.content
            # ini2toml removes newlines within sections, so we leave them as is
            if self.content[i] == '' and tomllines[0] != '':
                continue
            self.content[i] = tomllines.pop(0)
        if any(tomllines):
            raise ValueError(f'Unconsumed toml: {tomllines}')

        toml = self._make_tab('toml')

        return [ini, toml]


def setup(app):
    app.add_directive('config', Config)
