# pylint: disable=invalid-name,too-few-public-methods
"""This file is for `sphinx-build` configuration"""
import os
import sys

# import pygments.styles
# from pygments.style import Style
# from pygments.token import (
#     Text,
#     Other,
#     Comment,
#     Keyword,
#     Name,
#     Literal,
#     String,
#     Number,
#     Operator,
#     Generic,
#     Punctuation,
# )


sys.path.insert(0, os.path.abspath(".."))

# -- General configuration ------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autosummary",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    # "rst2pdf.pdfbuilder",  # for local pdf builder support
    "sphinx_immaterial",
]

# Uncomment the below if you use native CircuitPython modules such as
# digitalio, micropython and busio. List the modules you use. Without it, the
# autodoc module docs will fail to generate with a warning.
autodoc_mock_imports = ["logging"]
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://docs.python-requests.org/en/latest", None),
}

html_baseurl = "https://check-python-sources.readthedocs.io/"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
# pylint: disable=redefined-builtin
copyright = "2021 Brendan Doherty"
# pylint: enable=redefined-builtin
project = "check-python-sources Github Action"
author = "Brendan Doherty"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = "1.0.0"
# The full version, including alpha/beta/rc tags.
release = "1.0.0"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    ".env",
    "CODE_OF_CONDUCT.md",
    "requirements.txt",
]

# The reST default role (used for this markup: `text`) to use for all
# documents.
default_role = "any"

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# If this is True, todo emits a warning for each TODO entries. The default is False.
todo_emit_warnings = False

napoleon_numpy_docstring = False

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_immaterial"
# Material theme options

html_theme_options = {
    "features": [
        "navigation.expand",
        "navigation.tabs",
        "navigation.tabs.sticky"
        # "toc.integrate",
        "navigation.sections",
        "navigation.instant",
        # 'header.autohide',
        "navigation.top",
        # 'search.highlight',
        "search.share",
    ],
    "palette": [
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "green",
            "accent": "light blue",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to light mode",
            },
        },
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "green",
            "accent": "light blue",
            "toggle": {
                "icon": "material/lightbulb-outline",
                "name": "Switch to dark mode",
            },
        },
    ],
    # Set the repo location to get a badge with stats
    "repo_url": "https://github.com/2bndy5/check-python-sources/",
    "repo_name": "check-python-sources",
    "repo_type": "github",
    # If False, expand all TOC entries
    "globaltoc_collapse": False,
    # "edit_uri": "blob/master/docs",
}
# Set link name generated in the top bar.
html_title = "check-python-sources Github Action"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
# html_css_files = [
#     "custom_material.css",
# ]

# The name of an image file (relative to this directory) to use as a favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#
html_favicon = "_static/favicon.png"

# project logo
# html_logo = "_static/Logo large.png"

# Output file base name for HTML help builder.
htmlhelp_basename = "check_python_sources_action_doc"
# html_copy_source = True
# html_show_sourcelink = True

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    #
    # The paper size ('letterpaper' or 'a4paper').
    "papersize": "letterpaper",
    #
    # The font size ('10pt', '11pt' or '12pt').
    "pointsize": "12pt",
    #
    # Additional stuff for the LaTeX preamble.
    "preamble": "",
    #
    # Latex figure (float) alignment
    "figure_align": "htbp",
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        "check_python_sourcesGithub_Action.tex",
        "check-python-sources Github Action Documentation",
        author,
        "manual",
    ),
]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (
        master_doc,
        "check_python_sourcesGithub_Action",
        "check_python_sources Github Action Documentation",
        [author],
        1,
    )
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "check_python_sourcesGithub_Action",
        " check_python_sources Github Action Documentation",
        author,
        "check_python_sourcesGithub_Action",
        "check-python-sources in Github Actions.",
        "Continuous Integration",
    ),
]

# ---Options for PDF output-----------------------------------------
# requires `rst2pdf` module which is not builtin to Python 3.4 nor
# readthedocs.org's docker)

# pdf_documents = [
#     (
#         "index",
#         "check_python_sources",
#         "check-python-sources Github Action documentation",
#         "Brendan Doherty",
#     ),
# ]
