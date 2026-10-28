import type { DOMWidgetView, WidgetModel, WidgetView } from '@jupyter-widgets/base';

// nglview's view (not its model) exposes setSize(), which resizes the stage
interface NglviewView {
  setSize(width: string, height: string): void;
  stage: { viewer: { container: HTMLElement } };
}

/**
 * Size nglview's stage to the output container, tracking it as it resizes.
 * Observes the output rather than the widget so the stage's own size changes
 * don't create a feedback loop. With `trackHeight = false` (for a widget with
 * a height of its own), only the width follows the output.
 *
 * Returns a cleanup function that detaches the observer.
 */
export function setupNglviewAutoSize(
  el: HTMLElement,
  view: DOMWidgetView,
  model: WidgetModel,
  trackHeight = true
): () => void {
  // Package-based dispatch also routes non-viewer nglview widgets here (e.g.
  // RepresentationControl, which renders as an ordinary ipywidgets Box).
  // Those views have no NGL stage or setSize(), so don't observe them.
  if (model.get('_view_name') !== 'NGLView') {
    return () => {};
  }
  const stage = view as unknown as NglviewView;
  const observer = new ResizeObserver(() => {
    // nglview stores an `NGLWidget(width=...)` argument on the synced
    // `_view_width` trait (default '') and sizes the stage to it, so an
    // explicit width opts out of tracking the output's width. Otherwise the
    // stage's own fixed pixel width would overflow or underfill the output.
    const width = model.get('_view_width') || `${el.clientWidth}px`;
    const height = trackHeight
      ? `${el.clientHeight}px`
      : stage.stage.viewer.container.style.height;
    stage.setSize(width, height);
  });
  observer.observe(el);
  return () => observer.disconnect();
}

// The model name of nglview's process-global ColormakerRegistry widget
export const NGLVIEW_COLORMAKER_REGISTRY_MODEL = 'ColormakerRegistryModel';

interface ModelViewManager {
  get_model(modelId: string): Promise<WidgetModel | undefined>;
  create_view(model: WidgetModel): Promise<WidgetView>;
}

/**
 * Render the ColormakerRegistry's view, hidden, when its model opens.
 *
 * nglview registers custom color schemes (ColormakerRegistry.add_selection_scheme()
 * and friends) from the registry's *view*: BaseView.render() wires the msg:custom
 * handler those calls arrive on, and the Python side queues `_call()`s until the
 * synced `_ready` trait flips (render() sets it once `displayed` resolves). The
 * registry is eagerly opened in every session (EAGERLY_SHARED_PACKAGES) but has
 * no visible output, so without this its view never exists and scheme messages
 * are silently dropped.
 */
export async function renderHiddenColormakerRegistry(
  manager: ModelViewManager,
  modelId: string
): Promise<void> {
  const model = await manager.get_model(modelId);
  if (!model) {
    return;
  }
  const view = await manager.create_view(model);
  // Historical `_call()`s (e.g. schemes registered at import time, before any
  // browser existed) are synced in `_msg_ar`, but the frontend replays them
  // only in embed mode. Replay them here so a first render can use a custom
  // scheme without waiting on the post-_ready flush to deliver its
  // registration (re-registering a scheme is idempotent)
  const onMsg = (view as unknown as { on_msg?: (msg: unknown) => void }).on_msg;
  if (onMsg) {
    for (const msg of (model.get('_msg_ar') as unknown[] | undefined) ?? []) {
      onMsg.call(view, msg);
    }
  }
  const el = (view as DOMWidgetView).el;
  if (el) {
    el.style.display = 'none';
    document.body.appendChild(el);
  }
  // A real display would get this from Lumino's after-attach message
  view.trigger('displayed');
}
