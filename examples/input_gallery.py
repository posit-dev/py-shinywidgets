import datetime
from typing import List

import ipywidgets as ipy
from shiny import *
from htmltools import *
from ipyshiny import *



dates = [datetime.date(2015, i, 1) for i in range(1, 13)]
rng_slider_options = [(i.strftime('%b'), i) for i in dates]


ui = ui.page_fluid(
    tags.h3("Sliders"),
    input_ipywidget(
      "IntSlider", 
      ipy.IntSlider(
          value=7,
          min=0,
          max=10,
          step=1,
          description='Test:',
          disabled=False,
          continuous_update=False,
          orientation='horizontal',
          readout=True,
          readout_format='d'
      )
    ),
    input_ipywidget(
        "FloatSlider",
        ipy.FloatSlider(
            value=7.5,
            min=0,
            max=10.0,
            step=0.1,
            description='Test:',
            disabled=False,
            continuous_update=False,
            orientation='vertical',
            readout=True,
            readout_format='.1f',
        )
    ),
    input_ipywidget(
        "FloatLogSlider",
        ipy.FloatLogSlider(
            value=10,
            base=10,
            min=-10,  # max exponent of base
            max=10,  # min exponent of base
            step=0.2,  # exponent step
            description='Log Slider'
        )
    ),
    # TODO: jquery-ui slider bug?
    #input_ipywidget(
    #    "IntRangeSlider",
    #    ipy.IntRangeSlider(
    #        value=[5, 7],
    #        min=0,
    #        max=10,
    #        step=1,
    #        description='Test:',
    #        disabled=False,
    #        continuous_update=False,
    #        orientation='horizontal',
    #        readout=True,
    #        readout_format='d',
    #    )
    #),
    #input_ipywidget(
    #    "FloatRangeSlider",
    #    ipy.FloatRangeSlider(
    #        value=[5, 7.5],
    #        min=0,
    #        max=10.0,
    #        step=0.1,
    #        description='Test:',
    #        disabled=False,
    #        continuous_update=False,
    #        orientation='horizontal',
    #        readout=True,
    #        readout_format='.1f',
    #    )
    #),
    ui.output_ui("sliders"),
    tags.h3("Progress"),
    input_ipywidget(
      "IntProgress",
      ipy.IntProgress(
          value=7,
          min=0,
          max=10,
          step=1,
          description='Loading:',
          bar_style='',  # 'success', 'info', 'warning', 'danger' or ''
          orientation='horizontal'
      )
    ),
    input_ipywidget(
        "FloatProgress",
        ipy.FloatProgress(
            value=7.5,
            min=0,
            max=10.0,
            step=0.1,
            description='Loading:',
            bar_style='info',
            orientation='horizontal'
        )
    ),
    ui.output_ui("progress"),
    tags.h3("Numeric"),
    input_ipywidget(
        "BoundedFloatText",
        ipy.BoundedFloatText(
            value=7.5,
            min=0,
            max=10.0,
            step=0.1,
            description='Text:',
            disabled=False
        )
    ),
    input_ipywidget(
        "Float text",
        ipy.FloatText(
            value=7.5,
            description='Any:',
            disabled=False
        )
    ),
    input_ipywidget(
        "IntText",
        ipy.IntText(
            value=7,
            description='Any:',
            disabled=False
        )
    ),
    ui.output_ui("numeric"),
    tags.h3("Boolean"),
    input_ipywidget(
        "Checkbox",
        ipy.Checkbox(
            value=False,
            description='Check me',
            disabled=False
        )
    ),
    input_ipywidget(
        "ToggleButton",
        ipy.ToggleButton(
            value=False,
            description='Click me',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Description',
            icon='check'
        )
    ),
    input_ipywidget(
      "Valid",
      ipy.Valid(
          value=False,
          description='Valid!',
      )
    ),
    ui.output_ui("boolean"),
    tags.h3("Selection"),
    input_ipywidget(
        "Dropdown",
        ipy.Dropdown(
            options=['1', '2', '3'],
            value='2',
            description='Number:',
            disabled=False,
        )
    ),
    input_ipywidget(
        "RadioButtons",
        ipy.RadioButtons(
            options=[('pepperoni', 'pep'), ('pineapple', 'pine'),
                     ('anchovies', 'anch')],
            value='pine',
            description='Pizza topping:',
            disabled=False
        )
    ),
    input_ipywidget(
        "Select",
        ipy.Select(
            options=['Linux', 'Windows', 'OSX'],
            value='OSX',
            # rows=10,
            description='OS:',
            disabled=False
        )
    ),
    input_ipywidget(
        "SelectionSlider",
        ipy.SelectionSlider(
            options=['scrambled', 'sunny side up', 'poached', 'over easy'],
            value='sunny side up',
            description='I like my eggs ...',
            disabled=False,
            continuous_update=False,
            orientation='horizontal',
            readout=True
        )
    ),
    # TODO: jquery-ui slider bug?
    input_ipywidget(
        "SelectionRangeSlider",
        ipy.SelectionRangeSlider(
            options=rng_slider_options,
            index=(0, 11),
            description='Months (2015)',
            disabled=False
        )
    ),
    input_ipywidget(
        "ToggleButtons",
        ipy.ToggleButtons(
            options=['Slow', 'Regular', 'Fast'],
            description='Speed:',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltips=['Description of slow',
                      'Description of regular', 'Description of fast'],
            #     icons=['check'] * 3
        )
    ),
    input_ipywidget(
        "SelectMultiple",
        ipy.SelectMultiple(
            options=['Apples', 'Oranges', 'Pears'],
            value=['Oranges'],
            #rows=10,
            description='Fruits',
            disabled=False
        )
    ),
    ui.output_ui("selection"),
    tags.h3("String widgets"),
    input_ipywidget(
        "Text",
        ipy.Text(
            value='Hello World',
            placeholder='Type something',
            description='String:',
            disabled=False
        ),
    ),
    input_ipywidget(
        "Textarea",
        ipy.Textarea(
            value='Hello World',
            placeholder='Type something',
            description='String:',
            disabled=False
        ),
    ),
    input_ipywidget(
        "Combobox",
        ipy.Combobox(
            placeholder='Choose Someone',
            options=['Paul', 'John', 'George', 'Ringo'],
            description='Combobox:',
            ensure_option=True,
            disabled=False
        )
    ),
    ui.output_ui("string"),
    tags.h3("HTML"),
    ipy.HTML(
        value="Hello <b>World</b>",
        placeholder='Some HTML',
        description='Some HTML',
    ),
    # TODO: does this not bring in MathJax?
    ipy.HTMLMath(
        value=r"Some math and <i>HTML</i>: \(x^2\) and $$\frac{x+1}{x-1}$$",
        placeholder='Some HTML',
        description='Some HTML',
    ),
    tags.h3("Buttons"),
    input_ipywidget(
        "Button",
        ipy.Button(
            description='Click me',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Click me',
            icon='check'
        ),
    ),
    input_ipywidget(
      "Play",
        ipy.Play(
            #     interval=10,
            value=50,
            min=0,
            max=100,
            step=1,
            description="Press play",
            disabled=False
        ),
        rate_policy_delay=1
    ),
    ui.output_ui("buttons"),
    tags.h3("Pickers"),
    input_ipywidget(
      "DatePicker",
      ipy.DatePicker(
          description='Pick a Date',
          disabled=False
      )
    ),
    input_ipywidget(
        "ColorPicker",
        ipy.ColorPicker(
            concise=False,
            description='Pick a color',
            value='blue',
            disabled=False
        )
    ),
    # TODO: probably doesn't make sense to support?
    input_ipywidget(
        "FileUpload",
        ipy.FileUpload(
            accept='',  # Accepted file extension e.g. '.txt', '.pdf', 'image/*', 'image/*,.pdf'
            multiple=False  # True to accept multiple files upload else False
        )
    ),
    # TODO: doesn't have a value attribute?
    #input_ipywidget(
    #  "Controller",
    #  ipy.Controller(index=0)
    #),
    ui.output_ui("pickers")
)


def server(input, output, session: Session):

    def display_values(ids: List[str]) -> TagList:
      inputs = [tags.p(input[id]()) for id in ids]
      return TagList(tags.br(), tags.p(tags.b("Values:")), *inputs)

    @output(name="sliders")
    @render_ui()
    def _():
      return display_values([
          "IntSlider",
          "FloatSlider",
          "FloatLogSlider",
          "IntRangeSlider",
          "FloatRangeSlider"
      ])

    @output(name="progress")
    @render_ui()
    def _():
        return display_values(["IntProgress", "FloatProgress"])

    @output(name="numeric")
    @render_ui()
    def _():
        return display_values([
            "BoundedFloatText",
            "Float text",
            "IntText",
        ])

    @output(name="boolean")
    @render_ui()
    def _():
        return display_values([
                "Checkbox",
                "ToggleButton",
                "Valid",
            ])

    @output(name="selection")
    @render_ui()
    def _():
        return display_values([
            "Dropdown",
            "RadioButtons",
            "Select",
            "SelectionSlider",
            "SelectionRangeSlider",
            "ToggleButtons",
            "SelectMultiple",
        ])

    @output(name="string")
    @render_ui()
    def _():
        return display_values([
            "Text",
            "Textarea",
            "Combobox",
        ])

    @output(name="buttons")
    @render_ui()
    def _():
        return display_values(["Button", "Play"])

    @output(name="pickers")
    @render_ui()
    def _():
        return display_values([
            "DatePicker",
            "ColorPicker",
            "FileUpload",
            "Controller",
        ])

app = App(ui, server)
