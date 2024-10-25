from setuptools import setup

setup(
    name="tksheet",
    version="7.2.18",
    description="Python 2 backport of Tkinter table / sheet widget",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="ragardner, Hierosoft",
    author_email="github@ragardner.simplelogin.com, 7557867+Poikilos@users.noreply.github.com",
    url="https://github.com/Hierosoft/tksheet",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=2.7",
    keywords=["tkinter", "table", "widget", "sheet", "grid", "tk"],
    project_urls={
        "Homepage": "https://github.com/Hierosoft/tksheet",
        "Bug Reports": "https://github.com/Hierosoft/tksheet/issues",
        "Funding": "https://github.com/Hierosoft",
    },
)
