import { useEffect, useState } from "react";

// #/transactions?account=3 처럼 주소 # 뒤로 화면을 나눈다 (서버 설정 없이 새로고침·즐겨찾기가 된다).
export interface Route { path: string; params: URLSearchParams }

function parse(): Route {
  const raw = window.location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  return { path: path || "/", params: new URLSearchParams(query) };
}

export function navigate(path: string, params: Record<string, string | number | undefined> = {}) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") p.set(k, String(v));
  const q = p.toString();
  window.location.hash = `${path}${q ? `?${q}` : ""}`;
}

export function useRoute(): Route {
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    const on = () => { setRoute(parse()); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}
