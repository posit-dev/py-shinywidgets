# A multiplanar viewer for a public MNI152 template scan, fetched directly
# by the browser (nothing to download locally).
from ipyniivue import NiiVue, Volume
from shiny.express import ui
from shinywidgets import render_niivue

ui.page_opts(title="NiiVue quickstart", fillable=True)


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes([Volume(url="https://niivue.com/demos/images/mni152.nii.gz")])
    return nv
