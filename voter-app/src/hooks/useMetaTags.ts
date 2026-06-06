import { useEffect } from 'react';

interface MetaTagsConfig {
  title: string;
  description: string;
  image?: string;
}

/** Sets or creates a <meta property="…"> element. */
function setOgMeta(property: string, content: string) {
  let el = document.querySelector<HTMLMetaElement>(`meta[property="${property}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute('property', property);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}

/** Sets or creates a <meta name="…"> element. */
function setNameMeta(name: string, content: string) {
  let el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute('name', name);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}

/**
 * Dynamically updates document.title and Open Graph / Twitter meta tags.
 *
 * Usage:
 *   useMetaTags({ title: 'Vote Lab — …', description: '…' });
 */
export function useMetaTags({ title, description, image }: MetaTagsConfig) {
  useEffect(() => {
    if (typeof document === 'undefined') return;

    document.title = title;

    const url = window.location.href;

    // Open Graph
    setOgMeta('og:title', title);
    setOgMeta('og:description', description);
    setOgMeta('og:url', url);
    if (image) setOgMeta('og:image', image);

    // Twitter / X
    setNameMeta('twitter:title', title);
    setNameMeta('twitter:description', description);
    setNameMeta('twitter:card', 'summary');
  }, [title, description, image]);
}
