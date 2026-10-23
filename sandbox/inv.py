import pandas as pd
import pygwalker, inspect
from pygwalker.api import anywidget as aw
print(pygwalker.__version__, [n for n in dir(aw) if not n.startswith('_')])
print(inspect.signature(aw.walk))
df = pd.DataFrame({"a":[1,2,3],"b":["x","y","z"]})
w = aw.walk(df)
print(type(w), type(w).__mro__)
print(w.layout, getattr(w,'layout',None) and w.layout.height)
print(w.trait_names())
print(w._esm[:300] if hasattr(w,'_esm') else None)
print(w._css[:300] if hasattr(w,'_css') else None)
