import docutils.core
import glob
import os.path
import pathlib
import pkg_resources
import re
import socket
import subprocess
import tempfile
import unittest

from bugwarrior import config

from .base import ConfigTest

DOCS_PATH = pathlib.Path(__file__).parent / '../bugwarrior/docs'

try:
    socket.create_connection(('1.1.1.1', 80))
    INTERNET = True
except OSError:
    INTERNET = False


class ReadmeTest(unittest.TestCase):
    def test_service_list(self):

        # GET README LISTED SERVICES
        def is_services(node):
            try:
                return 'services' in node.attributes['classes']
            except AttributeError:  # not all nodes have attributes
                return False

        with open('README.rst', 'r') as f:
            readme = f.read()

        readme_document = docutils.core.publish_doctree(readme)
        service_list_search = readme_document.traverse(condition=is_services)
        self.assertEqual(len(service_list_search), 1)
        service_list_element = service_list_search.pop()
        readme_listed_services = set(
            list_item.astext() for list_item in service_list_element.children)

        # GET TITLES FROM SERVICE DOCUMENTATION FILES
        documented_services = set()
        for service in glob.iglob(str(DOCS_PATH / 'services' / '*.rst')):
            with open(service, 'r') as f:
                firstline = f.readline().strip()
                # ignore directives or empty lines
                while firstline.startswith('.. _') or firstline == '':
                    firstline = f.readline().strip()
                documented_services.add(firstline)

        self.assertEqual(documented_services,  readme_listed_services)


class DocsTest(unittest.TestCase):
    @unittest.skipIf(not INTERNET, 'no internet')
    def test_docs_build_without_warning(self):
        with tempfile.TemporaryDirectory() as buildDir:
            subprocess.run(
                ['sphinx-build', '-n', '-W', '-v', str(DOCS_PATH), buildDir],
                check=True)

    @unittest.skipIf(not INTERNET, 'no internet')
    def test_manpage_build_without_warning(self):
        with tempfile.TemporaryDirectory() as buildDir:
            subprocess.run(
                ['sphinx-build', '-b', 'man', '-n', '-W', '-v', str(DOCS_PATH), buildDir],
                check=True)

    def test_registered_services_are_documented(self):
        registered_services = set(
            e.name for e in
            pkg_resources.iter_entry_points(group='bugwarrior.service'))

        documented_services = set()
        services_paths = os.listdir(DOCS_PATH / 'services')
        for p in services_paths:
            if re.match(r'.*\.rst$', p):
                documented_services.add(re.sub(r'\.rst$', '', p))

        self.assertEqual(registered_services, documented_services)


class ExampleBugwarriorrcTest(ConfigTest):
    def test_example_bugwarriorrc(self):
        os.environ['BUGWARRIORRC'] = os.path.join(
            DOCS_PATH, 'example-bugwarriorrc')
        config.load_config('general', False, False)
