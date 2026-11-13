# Any 3D numpy array can become a volume: wrap it as a NIfTI image with
# nibabel, write it to an in-memory buffer, and pass the bytes straight to
# `Volume(data=...)` -- no file on disk required.
from io import BytesIO

import nibabel as nib
import numpy as np
from ipyniivue import NiiVue, Volume
from shiny.express import ui
from shinywidgets import render_niivue

ui.page_opts(title="Volume from a numpy array", fillable=True)

# A smooth synthetic blob: a Gaussian bump off-center in a 64^3 volume.
grid = np.linspace(-1, 1, 64)
x, y, z = np.meshgrid(grid, grid, grid, indexing="ij")
data = np.exp(-(((x - 0.3) ** 2 + y**2 + (z + 0.2) ** 2) / 0.15)).astype(np.float32)

img = nib.Nifti1Image(data, affine=np.eye(4))
buffer = BytesIO()
img.to_file_map({"image": nib.FileHolder(fileobj=buffer)})


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes(
        [Volume(data=buffer.getvalue(), name="blob.nii", colormap="viridis")]
    )
    return nv
