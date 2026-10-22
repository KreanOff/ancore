/** Refresh visible dashboards without overlapping requests or retaining a departed screen. */
export function startAutoRefresh(seconds: number, refresh: () => Promise<void>) {
  if (![60, 300, 900].includes(seconds)) return () => {};
  let stopped = false;
  let running = false;
  let timer: ReturnType<typeof setTimeout>;
  function schedule() {
    clearTimeout(timer);
    if (!stopped && !running && document.visibilityState === 'visible')
      timer = setTimeout(tick, seconds * 1000);
  }
  async function tick() {
    if (stopped || document.visibilityState !== 'visible') return;
    running = true;
    try {
      await refresh();
    } catch {
      // The refresh action owns its error message; a failure must not stop later attempts.
    } finally {
      running = false;
      schedule();
    }
  }
  document.addEventListener('visibilitychange', schedule);
  schedule();
  return () => {
    stopped = true;
    clearTimeout(timer);
    document.removeEventListener('visibilitychange', schedule);
  };
}
