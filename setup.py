from setuptools import setup, find_packages
with open("readme.md", "r") as fh:
    long_description = fh.read()

setup(
    name='xtracto',
    version='0.0.3',
    author='shashstormer',
    description='Xtracto is a lightweight web development framework designed to simplify the process of creating dynamic web pages using Python and pypx. ',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "fastapi", "uvicorn", "beautifulsoup4", "requestez"
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries',
        'Topic :: Database',
    ],
    project_urls={
        'GitHub': 'https://github.com/shashstormer/xtracto',
    },
)
