ipyshiny
================

Render [ipywidgets](https://github.com/jupyter-widgets/ipywidgets) inside a [PyShiny](https://github.com/rstudio/prism) app 

## Usage

First, you'll need to install `htmltools` and `shiny`, then `ipyshiny` by hand

```sh
git clone https://github.com/rstudio/py-htmltools.git
cd py-htmltools
pip install -r requirements.txt
make install
cd ..

git clone https://github.com/rstudio/prism.git
cd prism
pip install -r requirements.txt
make install
cd ..

git clone https://github.com/rstudio/ipyshiny.git
cd ipyshiny
pip install -r requirements.txt
make install
```

To run an example app:

```sh
python3 examples/01_hello.py
```

Then visit the app by pointing a web browser to http://localhost:8000/.

## Development

If you want to do development, run:

```sh
cd js && yarn run build && cd ..
make install
```

Additionally, you can install pre-commit hooks which will automatically reformat and lint the code when you make a commit:

```sh
pre-commit install

# To disable:
# pre-commit uninstall
```
