from setuptools import setup, find_packages

version = '0.5.8'

f = open('bugwarrior/README.rst')
long_description = f.read().strip()
long_description = long_description.split('split here', 1)[1]
f.close()

setup(name='bugwarrior',
      version=version,
      description="Sync github, bitbucket, and trac issues with taskwarrior",
      long_description=long_description,
      classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python :: 2",
        "Topic :: Software Development :: Bug Tracking",
        "Topic :: Utilities",
      ],
      keywords='task taskwarrior todo github ',
      author='Ralph Bean',
      author_email='ralph.bean@gmail.com',
      url='http://github.com/ralphbean/bugwarrior',
      license='GPLv3+',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "twiggy",
          "bitlyapi",
          # We use requests ourselves, but we limit the version just so
          # jira-python can use it correctly.
          "requests<=0.14.2",
          "offtrac",
          "python-bugzilla",
          "jira-python",
          "taskw >= 0.4.2",
          "dogpile.cache",
      ],
      entry_points="""
      [console_scripts]
      bugwarrior-pull = bugwarrior:pull
      """,
      )
