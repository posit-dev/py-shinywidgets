---
title: Fixture
extra: shinywidgets[plotly]
filters: [example-header.lua]
---

Whole file:

```{.python file="examples/a.py" files="helper.py"}
from helper import x

print(x)
```

Excerpt:

```{.python file="examples/b.py" collapse="true"}
def f():
    return json.dumps({})
```

1. A step

   ```{.python file="examples/a.py"}
   from helper import x

   print(x)
   ```

[`examples/a.py`](examples/a.py) renders the same thing. Also see [the template](examples/tpl.py).

<!-- snippet: skip -->
```python
y = 2
```

```sh
pip install shinywidgets
```
