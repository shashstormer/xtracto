# PYPX Documentation

## Overview

PYPX (Python Page eXtension) is a custom markup language designed for representing HTML code with a focus on extensibility, configurability, and ease of use. It serves as an integral part of the Xtracto module, offering an efficient way to create and organize automated components.

## File Extension

PYPX files use the extension `.pypx`, which stands for "PYthon Page eXtension."

## Syntax

PYPX follows indentation-based syntax. Xtracto automatically manages opening and closing tags based on your indentation structure.

### Basic Structure

```pypx
html
    head
        title
            Page Title
    body
        div
            h1
                Hello World
            p
                This is a paragraph.
```

Compiles to:
```html
<html><head><title>Page Title</title></head><body><div><h1>Hello World</h1><p>This is a paragraph.</p></div></body></html>
```

### Attributes

Attributes are defined using `;;...;;` syntax.

```pypx
a
    ;;href="https://example.com";;
    ;;class="link";;
    Click Here
```

### Comments

Comments that are removed during parsing use `::...::`.

```pypx
:: This is a comment that won't appear in the HTML ::
div
    Content
```

### Variables

Variables use Jinja2-compatible syntax `{{...}}`. You can specify defaults using `{{var=default}}`.

```pypx
p
    Hello, {{name=Guest}}!
```

### Imports (Components)

Import other `.pypx` files using `[[...]]`. You can pass variables to components.

```pypx
[[header.pypx]]
div
    [[card.pypx || title='My Card' ]]
```

### Layouts

If a `_layout.pypx` file exists in your pages directory, it will be used as a wrapper. It must contain `{{children}}` where the page content should be injected.

```pypx
:: _layout.pypx ::
html
    body
        nav
        {{children}}
        footer
```

### Jinja2 Logic

You can use standard Jinja2 control structures.

```pypx
ul
    {% for item in items %}
    li
        {{ item }}
    {% endfor %}
```

## Parsing Order

1. Structure normalization (indentation handling)
2. Comments removal
3. Block parsing (HTML structure)
4. Imports resolution (recursive)
5. Jinja2 variable conversion
6. Jinja2 rendering

## Key Benefits

1. **Extensibility:** Easy component reuse via imports.
2. **Configurability:** Variables and layouts allow for dynamic pages.
3. **Clean Syntax:** Indentation-based structure reduces boilerplate.
4. **Integration:** Seamlessly works with Python and Jinja2.
