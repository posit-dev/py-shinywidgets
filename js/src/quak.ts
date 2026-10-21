/**
 * quak renders into a shadow root, so it can't be styled from Python/CSS, and
 * it caps its scrolling table at a fixed ~11 rows (an inline max-height).
 * To make render_quak() outputs fit a sized container (a filling layout, or an
 * explicit height on output_widget() or the widget), lift that cap and let the
 * table flex within the container instead.
 *
 * Returns a cleanup function that detaches the observer.
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
    // Without a height from the output or the widget, the table keeps its natural size
    if (!el.style.height && !lmWidget.style.height) return noop;
    lmWidget.style.height ||= '100%';
    impl.style.height = '100%';
  }

  Object.assign(quak.style, { display: 'flex', flexDirection: 'column', height: '100%', minHeight: '0', boxSizing: 'border-box' });
  Object.assign(scroller.style, { maxHeight: 'none', flex: '0 1 auto', minHeight: '0' });

  const observer = new ResizeObserver(() => {
    if (scroller.scrollHeight <= scroller.clientHeight) requestMoreRows(scroller);
  });
  // The scroller changes size with the container, and the table with each batch of rows
  observer.observe(scroller);
  observer.observe(table);

  return () => observer.disconnect();
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
