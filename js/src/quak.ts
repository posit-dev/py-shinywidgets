// quak's scroll listener loads rows within 1.5 pages (of its default 11.5
// rows, 22px each) of the bottom
const QUAK_LOAD_DISTANCE = 1.5 * 11.5 * 22;

/**
 * quak renders into a shadow root, so it can't be styled from Python/CSS, and
 * it caps its scrolling table at a fixed ~11 rows (an inline max-height).
 * To make render_quak() outputs fit a sized container (a filling layout, or an
 * explicit height on output_widget() or the widget), lift that cap and let the
 * table flex within the container instead.
 *
 * Returns a cleanup function that detaches the observer and listener.
 */
export function setupQuakFit(el: HTMLElement, lmWidget: HTMLElement, fill: boolean): () => void {
  const noop = () => {};
  const impl = lmWidget.children[0] as HTMLElement | undefined;
  const quak = impl?.shadowRoot?.querySelector<HTMLElement>('.quak');
  const scroller = quak?.querySelector<HTMLElement>('.table-container');
  const table = scroller?.firstElementChild;
  if (!impl || !quak || !scroller || !table) return noop;

  if (fill) {
    impl.classList.add('html-fill-container', 'html-fill-item');
  } else {
    // Without a height from the output or the widget, the table keeps its natural
    // size. "auto" is no constraint: with the cap lifted the table would grow with
    // every batch, and the ResizeObserver below would keep loading rows.
    const heightOf = (s: CSSStyleDeclaration) => (s.height === 'auto' ? '' : s.height);
    const widgetHeight = heightOf(lmWidget.style);
    if (!heightOf(el.style) && !widgetHeight) return noop;
    lmWidget.style.height = widgetHeight || '100%';
    impl.style.height = '100%';
  }

  Object.assign(quak.style, { display: 'flex', flexDirection: 'column', height: '100%', minHeight: '0', boxSizing: 'border-box' });
  Object.assign(scroller.style, { maxHeight: 'none', flex: '0 1 auto', minHeight: '0' });

  // quak's own scroll listener only loads rows within QUAK_LOAD_DISTANCE of
  // the bottom, which a taller scroll area never gets to. So also load them
  // within a screenful of the bottom, but not when quak's listener does too:
  // concurrent loads garble the rows.
  const onScroll = () => {
    const remaining = scroller.scrollHeight - scroller.scrollTop;
    if (remaining >= QUAK_LOAD_DISTANCE && remaining < 2 * scroller.clientHeight) {
      requestMoreRows(scroller);
    }
  };
  scroller.addEventListener('scroll', onScroll);

  const observer = new ResizeObserver(() => {
    // A hidden output (e.g., an inactive tab) has no height; don't load rows for it
    if (scroller.clientHeight > 0 && scroller.scrollHeight <= scroller.clientHeight) {
      requestMoreRows(scroller);
    }
  });
  // The scroller changes size with the container, and the table with each batch of rows
  observer.observe(scroller);
  observer.observe(table);

  return () => {
    observer.disconnect();
    scroller.removeEventListener('scroll', onScroll);
  };
}

/**
 * quak fetches the next batch of rows from a scroll listener that only
 * triggers near the bottom of overflowing content, so a table taller than its
 * rows would never fill. Run that listener as if scrolled to the bottom (it's a
 * no-op once every row is loaded). Its check runs synchronously.
 */
function requestMoreRows(scroller: HTMLElement): void {
  Object.defineProperty(scroller, 'scrollHeight', { value: 0, configurable: true });
  try {
    scroller.dispatchEvent(new Event('scroll'));
  } finally {
    Reflect.deleteProperty(scroller, 'scrollHeight');
  }
}
