import { useLayoutEffect, useState, type RefObject } from "react";

/** 컨테이너 너비를 따라가는 반응형 SVG 용. */
export function useWidth(ref: RefObject<HTMLElement | null>, fallback = 640): number {
  const [w, setW] = useState(fallback);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setW(el.clientWidth || fallback);
    const ro = new ResizeObserver(([e]) => setW(Math.max(240, Math.floor(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref, fallback]);
  return w;
}
