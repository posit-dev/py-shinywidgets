interface PlotlyEventEmitter {
  on(eventName: string, callback: () => void): void;
  once(eventName: string, callback: () => void): void;
  removeListener(eventName: string, callback: () => void): void;
}

const plotlyAfterPlotTimeoutMs = 5000;

export function findPlotlyGraphDiv(root: HTMLElement): HTMLElement | null {
  const plotlyEl = root.matches(".js-plotly-plot")
    ? root
    : root.querySelector(".js-plotly-plot");
  return plotlyEl instanceof HTMLElement ? plotlyEl : null;
}

export async function waitForPlotlyReadyToReveal(
  plotEl: HTMLElement,
  dispatchResize: () => void,
): Promise<void> {
  const plotly = (window as any).Plotly;
  await waitForPlotlyAfterPlot(plotEl);

  if (plotly?.Plots?.resize) {
    try {
      const afterResize = waitForPlotlyAfterPlot(plotEl);
      await plotly.Plots.resize(plotEl);
      await afterResize;
    } catch (err) {
      console.error("Error resizing Plotly widget before reveal:", err);
    }
  }

  dispatchResize();
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
    }, plotlyAfterPlotTimeoutMs);

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
