# Training Disclosure for tksheet2
This Training Disclosure, which may be more specifically titled above here (and in this document possibly referred to as "this disclosure"), is based on **Training Disclosure version 2.0.0** at https://github.com/Hierosoft/training-disclosure by Jake Gustafson. Jake Gustafson is probably *not* an author of the project unless listed as a project author, nor necessarily the disclosure editor(s) of this copy of the disclosure unless this copy is the original which among other places I, Jake Gustafson, state IANAL. The original disclosure is released under the [CC0](https://creativecommons.org/public-domain/cc0/) license, but regarding any text that differs from the original:

This disclosure also functions as a claim of copyright to the scope described in the paragraph below since potentially in some jurisdictions output not of direct human origin, by certain means of generation at least, may not be copyrightable (again, IANAL):

Various author(s) may make claims of authorship to content in the project not mentioned in this disclosure, which this disclosure by way of omission unless stated elsewhere implies is of direct human origin unless stated elsewhere. Such statements elsewhere are present and complete if applicable to the best of the disclosure editor(s) ability. Additionally, the project author(s) hereby claim copyright and claim direct human origin to any and all content in the subsections of this disclosure itself, where scope is defined to the best of the ability of the disclosure editor(s), including the subsection names themselves, unless where stated, and unless implied such as by context, being copyrighted or trademarked elsewhere, or other means of statement or implication according to law in applicable jurisdiction(s).

Disclosure editor(s): Hierosoft LLC

Project author: Hierosoft LLC

This disclosure is a voluntary of how and where content in or used by this project was produced by LLM(s) or any tools that are "trained" in any way.

The main section of this disclosure lists such tools. For each, the version, install location, and a scope of their training sources in a way that is specific as possible.

Subsections of this disclosure contain prompts used to generate content, in a way that is complete to the best ability of the disclosure editor(s).

tool(s) used:
- GPT-4-Turbo (Version 4o, chatgpt.com)

Scope of use: code described in subsections--typically modified by hand to improve logic, variable naming, integration, etc.

## setup.py
- 2024-10-25
what is the last version of tksheet to support Python 2? Cite sources. Hint: if release notes say "requires Python 3" point something, and does not mention Python 2 at all, the release before that is the last version to support Python 2.

Ok lets convert the latest git version to python2. First, convert this pyproject.toml to setup.py:
```
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "tksheet"
description = "Tkinter table / sheet widget"
readme = "README.md"
version = "7.2.18"
authors = [{ name = "ragardner", email = "github@ragardner.simplelogin.com" }]
requires-python = ">=3.8"
license = {file = "LICENSE.txt"}
keywords = ["tkinter", "table", "widget", "sheet", "grid", "tk"]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

[project.urls]
"Homepage" = "https://github.com/ragardner/tksheet"
"Bug Reports" = "https://github.com/ragardner/tksheet/issues"
"Funding" = "https://github.com/ragardner"

[tool.black]
line-length = 120

[tool.ruff]
line-length = 120
```

- author above is upstream author, not Hierosoft

Downgrade requirement to python 2.7 and add a classifier as well but keep python 3 classifiers.

The repo URL is now https://github.com/Hierosoft so change links to reflect that. Also add a second author, Poikilos, 7557867+Poikilos@users.noreply.github.com
