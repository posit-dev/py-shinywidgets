import type { DOMWidgetView, WidgetView } from '@jupyter-widgets/base';
import { MessageLoop, LuminoWidget } from 'shinywidgets-internals';
import { ShinyComm } from './comm';
import { WidgetLifecycle, newEventId } from './lifecycle/epoch';
import { shinyRequireLoader } from './lifecycle/loader';
import { MountScope, RootMount } from './lifecycle/mount';
import {
  parseEpochHello,
  parseWidgetValue,
  unpackComm,
} from './lifecycle/protocol';
import type {
  DisplayClaim,
  DisplayRelease,
  EpochIdentity,
  WidgetValue,
} from './lifecycle/types';
import { EpochRetiredError } from './lifecycle/types';
import { findPlotlyGraphDiv, waitForPlotlyReadyToReveal } from './plotly';
import { decodeBuffers } from './utils';
import type { ErrorsMessageValue } from 'rstudio-shiny/srcts/types/src/shiny/shinyapp';


/******************************************************************************
 * The document lifecycle controller (one per page).
 *
 * This line is the stable route-interception point for browser tests; the
 * factory is intentionally local (no shipped window registry).
 ******************************************************************************/
const lifecycle = createWidgetLifecycle();

function createWidgetLifecycle(): WidgetLifecycle {
  const controller = new WidgetLifecycle({
    loader: shinyRequireLoader,
    sendEvents: (packet) => {
      Shiny.setInputValue("shinywidgets_display", JSON.stringify(packet), {
        priority: "event",
      });
    },
  });

  // One document resize handler over active owned views (never one listener
  // per manager/mount).
  window.addEventListener("resize", () => {
    for (const view of controller.activeViews()) {
      const lumino = (view as any).luminoWidget ?? (view as any).pWidget;
      if (lumino !== undefined && !lumino.isDisposed) {
        MessageLoop.postMessage(lumino, LuminoWidget.ResizeMessage.UnknownSize);
      }
    }
  });

  return controller;
}


/******************************************************************************
 * Presentation helpers
 ******************************************************************************/

// An old task must never set or clear the identity attribute of a newer mount.
function setCurrentModelId(el: HTMLElement, mount: RootMount, modelId: string): void {
  el.dataset.shinywidgetsModelId = modelId;
}

function clearCurrentModelId(el: HTMLElement): void {
  delete el.dataset.shinywidgetsModelId;
}

// Package-specific view teardown (e.g., Plotly leaves DOM state and listeners
// behind unless destroy() runs before removal). Runs once per view.
function destroyViewAdapter(view: WidgetView): () => void {
  return () => {
    const v = view as any;
    if (typeof v.destroy === "function" && v.model !== undefined) {
      v.destroy();
      delete v.model;
    }
  };
}

function sendRelease(
  mount: RootMount,
  leaseId: string,
  reason: DisplayRelease["reason"],
  cleanup: DisplayRelease["cleanup"]
): void {
  lifecycle.sendDisplayEvent(
    {
      action: "release",
      event_id: newEventId(),
      output_id: mount.outputId,
      lease_id: leaseId as DisplayRelease["lease_id"],
      mount_id: mount.mountId,
      presentation_removed: true,
      reason,
      cleanup,
    },
    false
  );
}

function sendCancelClaim(mount: RootMount, claimSeq: number): void {
  lifecycle.sendDisplayEvent(
    {
      action: "cancel-claim",
      event_id: newEventId(),
      output_id: mount.outputId,
      mount_id: mount.mountId,
      claim_seq: claimSeq,
    },
    false
  );
}

function reportTerminalTask(error: unknown): void {
  if (error instanceof EpochRetiredError) {
    // Expected retirement cancellation, not a user-visible failure.
    return;
  }
  console.error("shinywidgets presentation task failed:", error);
}


/******************************************************************************
 * The output binding
 ******************************************************************************/

class IPyWidgetOutput extends Shiny.OutputBinding {
  find(scope: HTMLElement): JQuery<HTMLElement> {
    return $(scope).find(".shiny-ipywidget-output");
  }

  onValueError(el: HTMLElement, err: ErrorsMessageValue): void {
    // Invalidate admission synchronously; cleanup/release is a tracked task
    // (Shiny doesn't await onValueError). The error markup is presented only
    // after the mount has removed the old presentation: replacing the
    // element's content first would break Lumino's detach precondition.
    clearCurrentModelId(el);
    Shiny.unbindAll(el);
    el.style.visibility = "inherit";
    const mount = lifecycle.existingMountFor(el);
    const present = () => this.renderError(el, err);
    if (mount === null) {
      present();
      return;
    }
    void mount
      .retirePresentation()
      .catch((error) => {
        console.error("shinywidgets: cleanup failed after output error:", error);
        return null;
      })
      .then((lease) => {
        present();
        if (lease !== null) {
          sendRelease(mount, lease, "error", "complete");
        }
      });
  }

  renderValue(el: HTMLElement, data: unknown): void {
    // Synchronously start/record the candidate task and return; Shiny's
    // dispatch queue must not wait on later protocol/model messages.
    if (!data) {
      // A null value can arrive before any widget (or epoch hello) exists,
      // and doesn't need one: hide and release any existing presentation.
      clearCurrentModelId(el);
      el.style.visibility = "hidden";
      const mount = lifecycle.existingMountFor(el);
      if (mount !== null) {
        void mount
          .retirePresentation()
          .then((lease) => {
            if (lease !== null) {
              sendRelease(mount, lease, "null", "complete");
            }
          })
          .catch(reportTerminalTask);
      }
      return;
    }

    const value = parseWidgetValue(data);
    const mount = lifecycle.mountFor(el);
    mount.outputId = value.output_id;
    const candidate = mount.startCandidate();
    const task = this._prepareCandidate(el, mount, candidate, value);
    mount.trackTask(task);
    task.catch(reportTerminalTask);
  }

  /**
   * Prepare a replacement candidate: claim its display lease and prepare its
   * view concurrently. Once the current candidate has a claimed lease and a
   * prepared view, the old presentation is removed and the new one attaches.
   */
  private async _prepareCandidate(
    el: HTMLElement,
    mount: RootMount,
    candidate: MountScope,
    value: WidgetValue
  ): Promise<void> {
    const epoch = mount.epoch;
    const claimSeq = mount.nextClaimSeq();
    const claim: DisplayClaim = {
      action: "claim",
      event_id: newEventId(),
      output_id: value.output_id,
      offer_id: value.offer_id,
      candidate_lease_id: value.candidate_lease_id,
      generation_id: value.generation_id,
      root_id: value.model_id,
      mount_id: mount.mountId,
      claim_seq: claimSeq,
    };
    const claimResult = lifecycle.sendDisplayEvent(claim, true);
    if (claimResult === null) {
      throw new EpochRetiredError("no active epoch for display claim");
    }

    // Prepare the view concurrently with the claim round-trip.
    const model = await epoch.get_model(value.model_id);
    candidate.checkAdmission("prepare");
    const view = await epoch.create_view(model as any, {
      lifecycle_scope: candidate,
    });
    candidate.onDispose(destroyViewAdapter(view));
    candidate.checkAdmission("prepare");

    const result = await claimResult;
    candidate.checkAdmission("prepare");
    if (!("claimed" in result.outcome)) {
      mount.retireCandidate(candidate);
      if (
        result.outcome.refused === "root-closed" ||
        result.outcome.refused === "stale-offer"
      ) {
        // A cached replay of a collected widget can never be resurrected.
        this.renderError(el, {
          message:
            "This widget's render lifetime has ended. Create reusable " +
            "widgets inside session_lifetime(), or re-render the output.",
        } as ErrorsMessageValue);
      }
      return;
    }
    const leaseId = result.outcome.claimed;

    // Accept: remove the old presentation (through its mount), attach the
    // prepared view, then release the old lease after observable cleanup.
    const oldLease = mount.acceptedLease;
    clearCurrentModelId(el);
    await mount.retireAccepted();
    mount.acceptCandidate(candidate, value, leaseId, view);
    try {
      this._attach(el, view, value);
    } catch (error) {
      // Attachment failure releases the candidate lease and removes any
      // partial presentation.
      mount.retireCandidate(candidate);
      await mount.retireAccepted();
      sendRelease(mount, leaseId, "error", "failed");
      throw error;
    }
    setCurrentModelId(el, mount, value.model_id);
    if (oldLease !== null) {
      sendRelease(mount, oldLease, "replaced", "complete");
    }
    this._postAttach(el, candidate, value);
  }

  private _attach(el: HTMLElement, view: WidgetView, value: WidgetValue): void {
    // Clear stale error markup/residual content before attaching the new
    // presentation (#246 recovery ordering).
    el.replaceChildren();
    const lumino = (view as any).luminoWidget ?? (view as any).pWidget;
    LuminoWidget.attach(lumino, el);
  }

  private _postAttach(
    el: HTMLElement,
    candidate: MountScope,
    value: WidgetValue
  ): void {
    const isPlotlyWidget = value.widget_pkg === "plotly";
    el.style.visibility = isPlotlyWidget ? "hidden" : "inherit";

    // Only forward the potential to fill if `output_widget(fillable=True)`
    // _and_ the widget instance wants to fill
    const fill = value.fill && el.classList.contains("html-fill-container");
    if (fill) el.classList.add("forward-fill-potential");

    // The ipywidgets container (.lm-Widget)
    const lmWidget = el.children[0] as HTMLElement;

    if (fill) {
      this._onImplementation(lmWidget, candidate, () =>
        this._doAddFillClasses(lmWidget)
      );
    }
    if (!isPlotlyWidget) {
      this._onImplementation(lmWidget, candidate, () => this._doResize());
    } else {
      this._onImplementation(lmWidget, candidate, () => {
        if (!candidate.accepting) {
          return;
        }

        const plotEl = findPlotlyGraphDiv(lmWidget);
        if (!plotEl) {
          this._doResize();
          if (candidate.accepting) {
            el.style.visibility = "inherit";
          }
          return;
        }

        // Plotly FigureWidget may first render at its internal 360px fallback,
        // then resize after paint. Keep it hidden until a direct Plotly resize
        // completes so the first visible paint is already settled.
        const reveal = waitForPlotlyReadyToReveal(plotEl, () => this._doResize());
        candidate.onDispose(() => {
          void reveal;
        });
        void reveal.finally(() => {
          if (candidate.accepting) {
            el.style.visibility = "inherit";
          }
        });
      });
    }
  }

  _onImplementation(
    lmWidget: HTMLElement,
    candidate: MountScope,
    callback: () => void
  ): void {
    if (this._hasImplementation(lmWidget)) {
      callback();
      return;
    }

    // Some widget implementation (e.g., ipyleaflet, pydeck) won't actually
    // have rendered to the DOM at this point, so wait until they do
    const mo = new MutationObserver((_mutations) => {
      if (this._hasImplementation(lmWidget)) {
        mo.disconnect();
        callback();
      }
    });
    candidate.onDispose(() => mo.disconnect());

    mo.observe(lmWidget, { childList: true });
  }

  // In most cases, we can get widgets to fill through Python/CSS, but some widgets
  // (e.g., quak) don't have a Python API and use shadow DOM, which can only access
  // from JS
  _doAddFillClasses(lmWidget: HTMLElement): void {
    const impl = lmWidget.children[0];
    const isQuakWidget = impl && !!impl.shadowRoot?.querySelector(".quak");
    if (isQuakWidget) {
      impl.classList.add("html-fill-container", "html-fill-item");
      const quakWidget = impl.shadowRoot.querySelector(".quak") as HTMLElement;
      quakWidget.style.maxHeight = "unset";
    }
  }

  _doResize(): void {
    // Trigger resize event to force layout (setTimeout() is needed for altair)
    setTimeout(() => {
      window.dispatchEvent(new Event("resize"));
    }, 0);
  }

  _hasImplementation(lmWidget: HTMLElement): boolean {
    const impl = lmWidget.children[0];
    return impl && (impl.children.length > 0 || impl.shadowRoot?.children.length > 0);
  }
}

Shiny.outputBindings.register(new IPyWidgetOutput(), "shiny.IPyWidgetOutput");

// Release the exact server lease when an output element is unbound (e.g.,
// dynamic UI removal). Admission is invalidated synchronously first.
$(document).on("shiny:unbound", (event: any) => {
  if (event.bindingType !== "output") {
    return;
  }
  const el = event.target as HTMLElement;
  if (!el.classList || !el.classList.contains("shiny-ipywidget-output")) {
    return;
  }
  const mount = lifecycle.existingMountFor(el);
  if (mount === null) {
    return;
  }
  clearCurrentModelId(el);
  void mount
    .retirePresentation()
    .then((lease) => {
      if (lease !== null) {
        sendRelease(mount, lease, "unbound", "complete");
      }
      lifecycle.forgetMount(el);
    })
    .catch(reportTerminalTask);
});

// Due to the way widget implementations get loaded (via require.js), the
// binding registration above can happen _after_ Shiny has already bound the
// DOM, especially in the dynamic UI case (i.e., output_binding()'s
// dependencies don't come in until after initial page load). And, in the
// dynamic UI case, UI is rendered asychronously via Shiny.shinyapp.taskQueue,
// so if it exists, we probably need to re-bind the DOM after the taskQueue is
// done.
const taskQueue = Shiny?.shinyapp?.taskQueue;
if (taskQueue) {
  taskQueue.enqueue(() => Shiny.bindAll(document.body));
}

/******************************************************************************
* Handle messages from the server-side Widget
******************************************************************************/

Shiny.addCustomMessageHandler("shinywidgets_epoch", (message) => {
  const identity = parseEpochHello(
    typeof message === "string" ? JSON.parse(message) : message
  );
  lifecycle.handleEpochHello(identity);
});

Shiny.addCustomMessageHandler("shinywidgets_display_result", (message) => {
  lifecycle.handleDisplayResult(
    typeof message === "string" ? JSON.parse(message) : message
  );
});

// Initialize the comm and model when a new widget is created
// This is basically our version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1144-L1176
Shiny.addCustomMessageHandler("shinywidgets_comm_open", (msg_txt) => {
  setBaseURL();
  const epoch = lifecycle.currentEpoch();
  const msg = unpackComm(epoch.identity, JSON.parse(msg_txt));
  decodeBuffers(msg);
  Shiny.renderDependencies((msg.content as any).html_deps);
  // Parse, validate, and enqueue epoch-owned work synchronously; never return
  // the model initialization promise (a parent's deserialization may need a
  // later child's comm_open, and Shiny awaits handler promises).
  const comm = new ShinyComm((msg.content as any).comm_id, epoch.identity);
  void epoch.handle_comm_open(comm, msg as any).catch((error: unknown) => {
    reportTerminalTask(error);
  });
});

// Handle any mutation of the model (e.g., add a marker to a map, without a full redraw)
// Basically out version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1200-L1215
Shiny.addCustomMessageHandler("shinywidgets_comm_msg", (msg_txt) => {
  const epoch = lifecycle.currentEpoch();
  const msg = unpackComm(epoch.identity, JSON.parse(msg_txt));
  decodeBuffers(msg);
  const id = (msg.content as any).comm_id;
  void (async () => {
    if (!epoch.has_model(id)) {
      console.error(`Couldn't handle message for model ${id} because it doesn't exist.`);
      return;
    }
    try {
      const m = await epoch.get_model(id);
      (m.comm as any).handle_msg(msg);
    } catch (err) {
      if (err instanceof EpochRetiredError) {
        return;
      }
      console.error("Error handling message:", err);
    }
  })();
});

// Handle the closing of a widget/comm/model
Shiny.addCustomMessageHandler("shinywidgets_comm_close", (msg_txt) => {
  const epoch = lifecycle.currentEpoch();
  const msg = unpackComm(epoch.identity, JSON.parse(msg_txt));
  const id = (msg.content as any).comm_id;
  void (async () => {
    if (!epoch.has_model(id)) {
      console.error(`Couldn't close model ${id} because it doesn't exist.`);
      return;
    }
    try {
      const m = await epoch.get_model(id);

      // Some widget views need explicit teardown before model.close() removes
      // them (e.g., Plotly leaves DOM state and listeners behind).
      if (m.views) {
        await Promise.all(
          Object.values(m.views).map(async (viewPromise) => {
            try {
              const view = await viewPromise;
              destroyViewAdapter(view)();
              view.remove();
            } catch (err) {
              console.error("Error cleaning up view:", err);
            }
          })
        );
      }

      // View removal updates _view_count. Mark the comm as inactive first so
      // that save_changes() does not try to send those updates after the comm
      // is gone.
      m.comm_live = false;

      // Close model after all views are cleaned up.
      await m.close();

      // Releases the model from its epoch registry on comm:close.
      m.trigger("comm:close");
    } catch (err) {
      if (err instanceof EpochRetiredError) {
        return;
      }
      console.error("Error during model cleanup:", err);
    }
  })();
});

$(document).on("shiny:disconnected", () => {
  lifecycle.handleDisconnected();
});

// When in filling layout, some widgets (specifically, altair) incorrectly think their
// height is 0 after it's shown, hidden, then shown again. As a workaround, trigger a
// resize event when a tab is shown.
// TODO: This covers the 95% use case, but it's definitely not an ideal way to handle
// this situation. A more robust solution would use IntersectionObserver to detect when
// the widget becomes visible. Or better yet, we'd get altair to handle this situation
// better.
// https://github.com/posit-dev/py-shinywidgets/issues/172
document.addEventListener('shown.bs.tab', event => {
  window.dispatchEvent(new Event('resize'));
})

// Our version of https://github.com/jupyter-widgets/widget-cookiecutter/blob/9694718/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js#L8
function setBaseURL(x: string = '') {
  const base_url = document.querySelector('body').getAttribute('data-base-url');
  if (!base_url) {
    document.querySelector('body').setAttribute('data-base-url', x);
  }
}
