let configuration: { base: string; token: string };
export async function config() {
  if (!configuration)
    configuration = window.desktop
      ? await window.desktop.config()
      : {
          base: "http://127.0.0.1:8765",
          token: import.meta.env.VITE_RESEARCHOS_TOKEN || "",
        };
  return configuration;
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const c = await config();
  const response = await fetch(c.base + path, {
    method,
    headers: {
      "X-ResearchOS-Token": c.token,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return response.json();
}
export async function openLink(url: string) {
  if (!/^https?:\/\//i.test(url))
    throw new Error("Only HTTP(S) links are supported");
  if (window.desktop) await window.desktop.openExternal(url);
  else window.open(url, "_blank", "noopener,noreferrer");
}
