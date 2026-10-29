"""Prototype: in-place coordination updates for the vitessce widget.

Updating the viewer from Python today means reassigning the ``_config``
trait, which the viewer only applies via a full remount of the view-config
store (keyed on ``config.uid``), resetting zoom/pan/selections and
re-creating loaders.

This prototype applies coordination edits directly to the live zustand
view-config store -- no remount, so viewport/selections survive:

1. ``InplaceVitessceWidget.set_coordination()`` sets a synced
   ``pending_coordination_edit`` trait.
2. A small patch to the wrapper ESM (see PATCHED_ESM) forwards trait
   changes to a ``window`` CustomEvent -- the wrapper owns the anywidget
   model but lives *outside* the view-config store provider, so it cannot
   touch the store itself.
3. A ``VitesscePlugin`` contributes a ``coordination-bridge`` plugin *view*
   (plugin views render *inside* the store provider -- the only official
   in-tree extension point in grid mode). It listens for the window event
   and applies the edit via the ``useCoordination`` setters (which call the
   store's ``setCoordinationValue`` action). The store's ``onConfigChange``
   subscription then echoes the updated config back to ``_config`` as usual.

Caveats this prototype surfaces for the upstream proposal
(https://github.com/vitessce/vitessce-python/issues/524):

- Children of ``<Vitessce/>`` render only in page mode
  (VitessceGridLayout drops them in grid mode), so a non-visual bridge
  can't be mounted that way.
- Plugin views are the only in-tree host, but they are *visual* (a grid
  panel with title bar) and have no access to the anywidget model, so
  Python->JS pushes need a side channel (the window event here). A
  built-in command (option (a) in the issue) would avoid both problems.
"""

import itertools

from traitlets import Dict
from vitessce.widget import ESM, VitesscePlugin, VitessceWidget

# The bridge plugin view (runs INSIDE the view-config store provider).
BRIDGE_PLUGIN_ESM = """
function createPlugins(utilsForPlugins) {
    const { React, PluginViewType, useCoordination } = utilsForPlugins;
    const e = React.createElement;

    function CoordinationBridgeView(props) {
        const [edit, setEdit] = React.useState(null);

        React.useEffect(() => { console.log('[bridge] view mounted'); }, []);

        React.useEffect(() => {
            function handler(ev) {
                const pending = ev.detail;
                console.log('[bridge] window event', JSON.stringify(pending));
                if (pending && pending.parameter) {
                    setEdit(pending);
                }
            }
            window.addEventListener('vitessce:coordination-edit', handler);
            return () => window.removeEventListener('vitessce:coordination-edit', handler);
        }, []);

        const parameters = React.useMemo(() => (edit ? [edit.parameter] : []), [edit]);
        const scopes = React.useMemo(() => (edit ? { [edit.parameter]: edit.scope } : {}), [edit]);
        const [values, setters] = useCoordination(parameters, scopes);

        React.useEffect(() => {
            if (!edit) return;
            // Setter names are `set` + capitalized parameter (e.g. setFeatureSelection).
            const setterName = 'set' + edit.parameter.charAt(0).toUpperCase() + edit.parameter.slice(1);
            const setter = setters[setterName];
            console.log('[bridge] applying', setterName, JSON.stringify(edit.value), 'setter found:', !!setter);
            if (setter) {
                setter(edit.value);
            }
        }, [edit, setters]);

        return e('div', { style: { fontSize: '10px', padding: '2px' } },
            'coordination bridge (spike)');
    }

    return {
        pluginViewTypes: [new PluginViewType('coordination-bridge', CoordinationBridgeView, [])],
    };
}
export default { createPlugins };
"""

# The wrapper ESM patch: forward the synced trait to a window event (the
# wrapper owns the model; the plugin view owns the store access).
DISPATCHER_JS = """    // [spike] forward pending_coordination_edit trait changes to the
    // coordination-bridge plugin view via a window event.
    view.model.on('change:pending_coordination_edit', () => {
        const edit = view.model.get('pending_coordination_edit');
        console.log('[spike] dispatching edit', JSON.stringify(edit));
        window.dispatchEvent(new CustomEvent('vitessce:coordination-edit', { detail: edit }));
    });

"""

PATCHED_ESM = "console.log('[spike] patched ESM loading');\n" + ESM.replace(
    "    const root = createRoot(view.el);",
    DISPATCHER_JS + "    const root = createRoot(view.el);",
    1,
)

# Fail loudly if a future vitessce release changes the ESM so the patch
# no longer applies.
assert PATCHED_ESM.count("vitessce:coordination-edit") >= 1, "ESM patch did not apply"


class CoordinationBridgePlugin(VitesscePlugin):
    """Plugin contributing the in-tree coordination-bridge view."""

    plugin_esm = BRIDGE_PLUGIN_ESM
    commands = {}


class InplaceVitessceWidget(VitessceWidget):
    """A VitessceWidget that supports in-place coordination updates.

    Construct directly (rather than via ``VitessceConfig.widget()``), pass
    ``plugins=[CoordinationBridgePlugin()]``, and add a
    ``"coordination-bridge"`` view to the config layout (see app.py)::

        widget = InplaceVitessceWidget(vc, height=640,
                                       plugins=[CoordinationBridgePlugin()])
    """

    _esm = PATCHED_ESM

    #: Internal: the edit the bridge view should apply. Written by
    #: set_coordination(); the bridge applies it to the store, which echoes
    #: the result back to `_config` through the usual onConfigChange path.
    pending_coordination_edit = Dict({}).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._edit_nonce = itertools.count(1)
        super().__init__(*args, **kwargs)

    def set_coordination(self, parameter, value, scope="A"):
        """Update a coordination value in the viewer, in place (no remount).

        Parameters
        ----------
        parameter
            The coordination type, e.g. ``"featureSelection"``,
            ``"spatialZoom"``, ``"obsSetSelection"``.
        value
            The new value, e.g. ``["CR2"]`` for ``featureSelection``.
        scope
            The coordination scope name (``"A"`` for most configs; inspect
            ``widget._config["coordinationSpace"][parameter]`` for others).
        """
        print(
            f"[spike] set_coordination({parameter!r}, {value!r}, scope={scope!r})",
            flush=True,
        )
        self.pending_coordination_edit = {
            # Forces a traitlets change event even for repeated identical
            # parameter/scope/value edits.
            "nonce": next(self._edit_nonce),
            "parameter": parameter,
            "scope": scope,
            "value": value,
        }
