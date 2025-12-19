# Xtracto Web Development Framework
eXtensible, Configurable, and Reusable Automation Component Tool and Organizer <sub>for html through pypx</sub>

Xtracto is a lightweight web development framework designed to simplify the process of creating dynamic web pages using Python. It uses a custom markup language called `pypx` (Python Page eXtension) that compiles to HTML with Jinja2 templating support.

> **This module is a parser for pypx (custom markup language) to html**
> ****
> **read [pypx.md](xtracto/pypx.md) to understand the custom markup language**

## Features

- **Parser Class:** Easily parse and transform `pypx` content using the `Parser` class.
- **Component System:** Build reusable components and import them into your pages.
- **Layout Support:** Define layouts to wrap your pages with consistent headers, footers, etc.
- **Jinja2 Integration:** Use Jinja2 syntax for variables, loops, and logic.
- **Tailwind CSS Support:** Automatically generates Tailwind CSS based on your usage.
- **Build System:** Pre-render your pages to HTML for production.

> **It is recommended that you use python 3.9+ for best compatibility**

## Installation

```bash
pip install xtracto
```

## Sample project

You can view a sample project at [shashstormer/xtracto_website](https://github.com/shashstormer/xtracto_website).

### Usage

#### 1. Parser Class

Initialize the `Parser` class with the content or file path:

#### Example with content
```python
from xtracto import Parser
content = "html\n    body\n        h1\n            Hello World"
parser = Parser(content=content)
parser.render()
print(parser.html_content)
```

#### Example with a file path
```python
from xtracto import Parser
# Assuming you have configured xtracto.config.py
parser = Parser(path="index.pypx")
parser.render()
print(parser.html_content)
```

#### 2. Building for Production

Use the `Builder` class to compile all your pages to HTML:

```python
from xtracto import Builder
builder = Builder()
builder.build()
```

## Configuration

The project root is determined by the presence of `xtracto.config.py`. It must be present in your project root directory.

Paths in the pypx files are relative to the project root.

Customize project-specific configurations in the `xtracto.config.py` file:

```python
# xtracto.config.py
modules_dir = "xtractocomponents" # Directory for reusable components
pages_dir = "xtractopages"       # Directory for your pages
build_dir = "build"              # Directory for built HTML files
log_level = "info"               # Logging level
reparse_tailwind = False         # Whether to regenerate Tailwind CSS on render
production = False               # Production mode flag
```
