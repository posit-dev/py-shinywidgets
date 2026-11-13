---
title: Installation
summary: >
  `pip install shinywidgets`, plus one extra for each widget library you use.
audience: >
  Anyone installing shinywidgets for the first time.
widgets: [plotly]
description: "`pip install shinywidgets`, plus one extra for each widget library you use."
---

shinywidgets needs Python 3.10 or newer.

```
pip install shinywidgets
```

That installs the core: `@render_widget`, `output_widget()`, and everything that connects a widget to your app.
It doesn't install any widget library. Each one is an optional extra, so you only pull in what you use:

```
pip install 'shinywidgets[plotly]'
```

An extra installs the widget library plus anything shinywidgets needs to work with it. Every widget's guide
shows its install command near the top (here's [plotly's](../../widgets/plotly/index.md#installation)). To install several at once,
separate them with commas:

```
pip install 'shinywidgets[plotly,itables]'
```

Deploying an app? List the same extras in its `requirements.txt`; see [Deployment](../deployment/index.md).
If a widget doesn't show up, see [Troubleshooting](../troubleshooting/index.md).
