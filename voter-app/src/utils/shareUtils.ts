/** Encode an object to a URL-safe base64 string. */
export function encodeShareConfig(config: object): string {
  try {
    return btoa(encodeURIComponent(JSON.stringify(config)));
  } catch {
    return '';
  }
}

/** Decode a base64 URL config string back to an object, or return null on error. */
export function decodeShareConfig<T>(encoded: string): T | null {
  try {
    return JSON.parse(decodeURIComponent(atob(encoded))) as T;
  } catch {
    return null;
  }
}

/** Build a shareable URL for the current page with the config encoded. */
export function buildShareURL(config: object): string {
  const encoded = encodeShareConfig(config);
  const { origin, pathname } = window.location;
  return `${origin}${pathname}?cfg=${encoded}`;
}

/** Copy a shareable URL to the clipboard. */
export async function copyShareURL(config: object): Promise<void> {
  const url = buildShareURL(config);
  await navigator.clipboard.writeText(url);
}

/** Read the ?cfg= query param from the current URL. */
export function readShareParam(): string | null {
  return new URLSearchParams(window.location.search).get('cfg');
}
