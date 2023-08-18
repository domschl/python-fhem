import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="fhem",
    version="0.7.0",
    author="Dominik Schloesser",
    author_email="dsc@dosc.net",
    description="Python API for FHEM home automation server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://github.com/domschl/python-fhem",
    project_urls={"Bug Tracker": "https://github.com/domschl/python-fhem/issues"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "."},
    packages=setuptools.find_packages(where="."),
    python_requires=">=3.6",
)
