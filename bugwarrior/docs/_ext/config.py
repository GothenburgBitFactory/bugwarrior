import functools

from ini2toml.api import Translator
from sphinx.directives.code import CodeBlock
from sphinx.util.docutils import SphinxDirective
from sphinx_inline_tabs._impl import TabDirective


@functools.cache
def _translator() -> Translator:
    # Translator() discovers its ini/toml plugins via importlib.metadata
    # entry points on every instantiation, which is expensive. The plugin
    # set is fixed for the lifetime of the process, so build one and reuse
    # it across every ``.. config::`` directive instead of once per call.
    return Translator()


class Config(SphinxDirective):
    optional_arguments = 1
    option_spec = {"fragment": str}  # section schema to stub
    has_content = True

    def _make_tab(self, lang: str):
        self.arguments = [lang]
        tab = TabDirective.run(self)[0]  # type: ignore[ty:arg-type]
        tab[1][0] = CodeBlock.run(self)[0]  # type: ignore[ty:arg-type]
        # While line breaks were previously separate elements, they're now
        # within the single CodeBlock element.
        del tab[1][1:]
        return tab

    def run(self):
        self.assert_has_content()

        ini = self._make_tab("ini")
        initext = "\n".join(self.content)

        if "fragment" in self.options:  # add stub
            stub_section = (
                "[some_section]\nservice = " + self.options["fragment"] + "\n"
            )
            initext = stub_section + initext
        tomltext = _translator().translate(initext, "bugwarriorrc")
        if "fragment" in self.options:  # remove stub
            stub_len = len(stub_section) + 2  # toml adds quotes to strings
            tomltext = tomltext[stub_len:]

        tomllines = tomltext.split("\n")
        for i in range(len(self.content)):  # mutate self.content
            # ini2toml removes newlines within sections, so we leave them as is
            if self.content[i] == "" and tomllines[0] != "":
                continue
            self.content[i] = tomllines.pop(0)
        if any(tomllines):
            raise ValueError(f"Unconsumed toml: {tomllines}")

        toml = self._make_tab("toml")

        return [toml, ini]


def setup(app):
    app.add_directive("config", Config)
