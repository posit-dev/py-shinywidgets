import * as assert from "node:assert/strict";

import { waitForPlotlyReadyToReveal } from "../src/plotly";

async function testResizeFailureStillResolves(): Promise<void> {
  const globalWindow = globalThis as typeof globalThis & {
    Plotly?: { Plots?: { resize?: (_plotEl: HTMLElement) => Promise<void> } };
    window?: Window & typeof globalThis;
    setTimeout?: typeof setTimeout;
    clearTimeout?: typeof clearTimeout;
  };
  const oldWindow = globalWindow.window;
  const oldPlotly = globalWindow.Plotly;
  const oldSetTimeout = globalWindow.setTimeout;
  const oldClearTimeout = globalWindow.clearTimeout;
  const oldConsoleError = console.error;

  globalWindow.window = globalWindow as Window & typeof globalThis;
  globalWindow.Plotly = {
    Plots: {
      resize: async () => {
        throw new Error("Injected Plotly resize failure");
      },
    },
  };
  globalWindow.setTimeout = (() => 1) as typeof setTimeout;
  globalWindow.clearTimeout = (() => undefined) as typeof clearTimeout;
  console.error = () => undefined;

  try {
    const plotEl = {
      once(_eventName: string, callback: () => void) {
        Promise.resolve().then(callback);
      },
      removeListener() {
        return undefined;
      },
    } as unknown as HTMLElement;

    let resizeDispatchCount = 0;

    await assert.doesNotReject(
      waitForPlotlyReadyToReveal(plotEl, () => {
        resizeDispatchCount += 1;
      })
    );
    assert.equal(resizeDispatchCount, 1);
  } finally {
    globalWindow.window = oldWindow;
    globalWindow.Plotly = oldPlotly;
    globalWindow.setTimeout = oldSetTimeout;
    globalWindow.clearTimeout = oldClearTimeout;
    console.error = oldConsoleError;
  }
}

async function main(): Promise<void> {
  await testResizeFailureStillResolves();
  console.log("plotly tests passed");
}

void main();
