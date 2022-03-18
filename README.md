ipyshiny
================

Render [ipywidgets](https://github.com/jupyter-widgets/ipywidgets) inside a [PyShiny](https://github.com/rstudio/prism) app 

## Installation

```sh
pip install ipywidgets
pip install shiny==0.0.0.9001 --extra-index-url=https://rstudio.github.io/pyshiny-site/pypi
pip install -e .
```

## Usage

Coming soon. For now, see/run the `examples/`:

```sh
shiny run examples.outputs
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
