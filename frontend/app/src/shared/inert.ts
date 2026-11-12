const owners = new WeakMap<HTMLElement, { count: number; wasInert: boolean }>();

// Drawers and dialogs can share a background, and may close in either order.
export function acquireInert(elements: Iterable<HTMLElement>) {
  const held = [...new Set(elements)].map((element) => {
    const state = owners.get(element) || { count: 0, wasInert: element.inert };
    state.count += 1;
    owners.set(element, state);
    element.inert = true;
    return { element, state };
  });
  let released = false;
  return () => {
    if (released) return;
    released = true;
    held.forEach(({ element, state }) => {
      state.count -= 1;
      if (state.count === 0) {
        owners.delete(element);
        element.inert = state.wasInert;
      }
    });
  };
}
