# PYPX Documentation

## Overview

PYPX (Python Page eXtension) is a custom markup language designed for representing HTML code with a focus on extensibility, configurability, and ease of use. It serves as an integral part of the eXTRACTO module, offering an efficient way to create and organize automated components.

## File Extension

PYPX files use the extension `.pypx`, which stands for "PYthon Page eXtension."

## Syntax

PYPX follows indetnation based syntax

while eXTRAXTO parses the file, it automatically puts end tags after the end of the block,
so you can stop worrying about end tags

so now let's look at a basic html file written in pypx

```pypx
::
./xtractopages/index.pypx
::
html
    head
        title
            Page Title
        meta
            ;charset="UTF-8";
        meta
            ;name="viewport";
            ;content="width=device-width, initial-scale=1.0"; 
    body
        [header.pypx]
        div
            This content will be in the div
            p
                ;style="color:red;text-align:center;";
                This content will be in the p element and in red color and center aligned.
        <div>you can include comments in the markup using ::comment content::</div>
        
        now if you see the source file you will see that the content with &colon;&colon;...&colon;&colon; is not parsed into the html
        
        but it is not impossible to include comments into the hmtl
        
        :: to include comments into the html you can use ?:inclusive comment?: so now if you see the rendered content you will be able to see the content between ?&colon;...?&colon; is included into the html as a comment. (functionality changed)::
         ?:home.css ::this will include the home.css into the page (new functionality)::?:        
        <footer>you may also use html elements directly but they must end within a single line and you need to close them yourself.</footer>
```

```pypx
::
./xtractocomponents/header.pypx
you can define your header component here so that you can reuse it at all pages
::
header
    PYPX page
    welcome to {username=User}
```

```pypx
::
./xtractopages/_layout.pypx
sample _layout file
::
<!DOCTYPE html>
html
    head
        title
            {title=shashstorm's website} ::this is parsed automatically from the page (can be absent in the page)::
        :: you can include your favicon here::
        {headcontent=} ::this is parsed automatically from the page (can be absent in the page)::
    body
        :: {preheader=} (feature removed):: ::this is parsed automatically from the page (can be absent in the page)::
        [header.pypx] ::if you want to define a header compont and use for all your pages you can do this::
        {children} ::this is parsed automatically from the page layout and it is necessary that atleast one element is present in the page::
        [footer.pypx] ::if you want to define a footer compont and use for all your pages you can do this::
        :: {postfooter=} (feature removed):: ::this is parsed automatically from the page (can be absent in the page)::
        
:: you can skip this by passing render_layout=False while initializing parser::
```

Lines with children will be converted to a regular element with separate start and end tag (attributes also if specified).

Lines with no children will be converted to empty elements.

Lines without any attributes or children will be converted into plain text.

Lines starting with `<` will not be edited (pypx comments will be parsed tho i.e., removed / converted to html comments). 

| symbol  |                                                                                       description                                                                                        |               usage                |
|:--------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|:----------------------------------:|
| []      |                                                  imports and embeds the file content from components directory into the generated file                                                   |       [filename(.extension)]       |
| {}      | this checks all scopes for the variable name (spefied before =) if present uses value of that else uses default value provided (when deefault value is not provided it raises NameError) |   {variable_name(=defaultvalue)}   |
| ::      |                                                                     pypx comment which will be removed after parsing                                                                     |       :: comment content ::        |
| ?:      |                                                     a file which will be included as an asset (mainly useful when using app router)                                                      |           ?: home.css ?:           |
| ;...;   |                                                                 this method is used to specify attributes for an element                                                                 | ;attribute_name="attribute_value"; |
| #       |                                                                this method is used to escape characters in the pypx file                                                                 |             #{# or #:#             |
| #&n#    |                                                         this is a escape sequence to create a new line in the generated content                                                          |                #&n#                |
| +$...$+ |                                                             this will load a python variable into the context of the render                                                              |      +$test_var=test_value$+       |

to include `{` symbol within the pypx file use `#{#`

the # # group can escape up to two characters at once (recomended to use only one character).

the escape sequences are used internally when importing css and js files.
 when you want to add css or js manually, you will have to escape it by yourself.

it is recomended you keep separate files for mainance purpose and ease of writing.

when you import js/css/pypx files using `[]` import method they will be embedded into the generated content.
if you use the src /href attribute, they will be fetched seperately.

`[]` import method imports the spefied file
if an extension is not mentioned it will use pypx extension.

to make a variable optional while mentioning it using `{}` you can just do `{variable_name=}` this will make the variable optional.

for dynamic imports, you can use variables and create dynamic imports like `[{name_of_file_to_import=default.pypx}]`

you can also use variables for dynamic class names, text or whatever you want.

# order for parsing of features:
1. comments
2. variable
3. markdown (yet to be added)
4. imports
5. conversion to html

this order lets you leverage dynamic imports.

The upcomming markdown feature will allow you to create html tables like in markdown with ease (support for integration with html attributes and cell spanning may be added).


## Key Benefits of Using PYPX in Web Development

1. **Extensibility:**
   - PYPX allows for easy extension through its import mechanism, enabling the reuse of components across multiple pages.

2. **Configurability:**
   - Variables and dynamic imports provide a way to configure and customize components based on specific requirements.
   - You may also define _layout.pypx for rendering pages within a layout.

3. **Ease of Maintenance:**
   - Keeping separate files for components enhances maintainability, making it simpler to update or modify individual components.

4. **Clear Structure:**
   - The syntax and order of parsing in PYPX provide a clear structure for defining HTML elements, making the code more readable and organized.

5. **Dynamic Content:**
   - Variables and dynamic imports enable the creation of dynamic content, adapting to different scenarios without repetitive coding.
