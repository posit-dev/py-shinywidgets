// JupyterLab reports its theme's lightness as the `data-jp-theme-light`
// attribute on <body> ("true"/"false"; dark iff "false"), and widgets like
// ipydatagrid sniff it to choose their light/dark palette -- ipydatagrid does
// so once, when a grid view is created (see its `_initializeTheme`), and then
// freezes the palette. Shiny never sets the attribute, so dark-mode apps got
// light-palette grids (CSS variables can't fix this: it's an attribute read,
// not a var read). Emulate JupyterLab here, deriving the value from the app's
// bslib color mode (`data-bs-theme` on <html>, falling back to
// `prefers-color-scheme` when no explicit mode is set) and keeping it in
// sync, so widgets whose JS loads later still see the current mode. This runs
// at output.js evaluation (in <head>), before any widget JS loads (widget JS
// loads lazily via require.js at first render).
export function installJpThemeLightShim(): void {
  const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');

  const sync = (): void => {
    if (!document.body) return;
    const theme = document.documentElement.getAttribute('data-bs-theme');
    const dark = theme ? theme === 'dark' : darkQuery.matches;
    document.body.dataset.jpThemeLight = dark ? 'false' : 'true';
  };

  const observe = (): void => {
    new MutationObserver(sync).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-bs-theme'],
    });
    darkQuery.addEventListener('change', sync);
  };

  // output.js is parsed in <head>, so <body> may not exist yet
  if (document.readyState === 'loading') {
    document.addEventListener(
      'DOMContentLoaded',
      () => {
        sync();
        observe();
      },
      { once: true }
    );
  } else {
    sync();
    observe();
  }
}
