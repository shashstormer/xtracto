
# Xtracto Web Development Framework
eXtensible, Configurable, and Reusable Automation Component Tool and Organizer <sub>for html through pypx</sub>


Xtracto is a lightweight web development framework designed to simplify the process of creating dynamic web pages using Python.

> **This module is a parser for pypx (custom markup language) to html**
> ****
> **read [pypx.md](https://github.com/shashstormer/xtracto/blob/master/xtracto/pypx.md) to understand the custom markup language**

## Features

- **Parser Class:** Easily parse and transform content using the `Parser` class.
- **Automatic Server Setup:** Use the `App` class for hassle-free server setup with FastAPI and Uvicorn.
- **Testing Support:** Conduct tests on your content or files using the `Tests` class.

> **It is recommended that you use python 3.9 (as of 3rd january 2024) for best compatibility**

### Usage

#### 1. Parser Class

Initialize the `Parser` class with the content or file path:


#### Example with content
```python
from xtracto import Parser
content = "Your content here"
parser = Parser(content=content)
```


#### Example with a file path
```python
from xtracto import Parser
file_path = "path/to/your/file.pypx"
parser = Parser(path=file_path)
```

#### 2. Automatic Server Setup

Use the `App` class for automatic server setup:

```python
from xtracto import App
app = App()
```

#### 3. Compilation

Compile non-dynamic pages to HTML:


#### Example
```python
from xtracto import Parser
parser = Parser()
parser.compile(start_path_for_map="/")
```


## Configuration


project root is determined using the presence of `xtracto.config.py` it must be present otherwise will raise error.

Paths in the pypx files are relative to the project root.

Paths in the config file are relative to the project root.

The config file can be empty.

Customize project-specific configurations in the `xtracto.config.py` file. Update the following parameters:

- `modules_dir`: Directory for modules (default: "xtractocomponents").
- `pages_dir`: Directory for pages (default: "xtractopages").
- `strip_imports`: Whether to strip imports (default: True).
- `raise_value_errors_while_importing`: Whether to raise value errors during imports (default: True).
