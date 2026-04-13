interface PlotlyEventEmitter {
  on(eventName: string, callback: () => void): void;
  once(eventName: string, callback: () => void): void;
  removeListener(eventName: string, callback: () => void): void;
}

export function waitForPlotlyGraphDiv(root: HTMLElement): Promise<HTMLElement | null> {
  const existingPlotEl = findRenderedPlotlyGraphDiv(root);
  if (existingPlotEl) {
    return Promise.resolve(existingPlotEl);
  }

  return new Promise((resolve) => {
    const onRender = (evt: Event) => {
      const target = (evt as CustomEvent).detail?.element;
      if (!(target instanceof HTMLElement) || !root.contains(target)) return;
      cleanup();
      resolve(target);
    };

    const cleanup = () => {
      document.removeEventListener("plotlywidget-after-render", onRender);
      window.clearTimeout(timeoutId);
    };

    const timeoutId = window.setTimeout(() => {
      cleanup();
      resolve(findRenderedPlotlyGraphDiv(root));
    }, 1000);

    document.addEventListener("plotlywidget-after-render", onRender);
  });
}

export async function waitForPlotlyReadyToReveal(
  plotEl: HTMLElement,
  dispatchResize: () => void,
): Promise<void> {
  const plotly = (window as any).Plotly;
  await waitForPlotlyAfterPlot(plotEl);

  if (plotly?.Plots?.resize) {
    const afterResize = waitForPlotlyAfterPlot(plotEl);
    await plotly.Plots.resize(plotEl);
    await afterResize;
  } else {
    dispatchResize();
  }

  dispatchResize();
}

function findRenderedPlotlyGraphDiv(root: HTMLElement): HTMLElement | null {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  let currentNode: Node | null = root;

  while (currentNode) {
    if (currentNode instanceof HTMLElement && (currentNode as any)._fullLayout) {
      return currentNode;
    }
    currentNode = walker.nextNode();
  }

  return null;
}

function waitForPlotlyAfterPlot(plotEl: HTMLElement): Promise<void> {
  return new Promise((resolve) => {
    const handler = () => {
      cleanup();
      resolve();
    };

    const cleanup = () => {
      if (hasMethod<PlotlyEventEmitter, "removeListener">(plotEl, "removeListener")) {
        plotEl.removeListener("plotly_afterplot", handler);
      }
      window.clearTimeout(timeoutId);
    };

    const timeoutId = window.setTimeout(() => {
      cleanup();
      resolve();
    }, 1000);

    if (hasMethod<PlotlyEventEmitter, "once">(plotEl, "once")) {
      plotEl.once("plotly_afterplot", handler);
      return;
    }

    if (hasMethod<PlotlyEventEmitter, "on">(plotEl, "on")) {
      plotEl.on("plotly_afterplot", handler);
      return;
    }

    cleanup();
    resolve();
  });
}

function hasMethod<T, K extends keyof T>(
  x: unknown,
  key: K,
): x is T & Record<K, (...args: any[]) => unknown> {
  return !!x && typeof (x as any)[key] === "function";
}
