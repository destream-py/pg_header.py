from setuptools import setup

setup(
    name = "pgheader",
    version = "1.0",
    author = "Cecile Tonglet",
    author_email = "cecile.tonglet@gmail.com",
    description = ("Retrieve information in the Postgres custom dump header "
                   "using Python"),
    license = "MIT",
    keywords = "postgres database dump header",
    url = "https://github.com/cecton/pg_header.py",
    py_modules=['pgheader'],
    scripts=['pgheader.py'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Database",
        "License :: OSI Approved :: MIT License",
    ],
)
