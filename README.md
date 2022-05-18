ipyshiny
================

Render [ipywidgets](https://github.com/jupyter-widgets/ipywidgets) inside a [PyShiny](https://github.com/rstudio/prism) app 

## Installation

First, [install Shiny](https://rstudio.github.io/pyshiny-site/install.html), then:

```sh
git clone https://github.com/rstudio/ipyshiny
pip install -e ipyshiny
```

## Usage

Coming soon. For now, see/run the `examples/`:

```sh
shiny run examples/outputs/appy.py
```

## Development

If you want to do development, run:

```sh
pip install -e .
cd js && yarn watch
```

Additionally, you can install pre-commit hooks which will automatically reformat and lint the code when you make a commit:

```sh
pre-commit install

# To disable:
# pre-commit uninstall
```
