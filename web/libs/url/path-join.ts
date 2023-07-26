export const pathJoin = (base: string, ...parts: string[]) => {
  let url: URL | null = null;
  let pathname = base;
  try {
    url = new URL(base);
    pathname = url.pathname;
  } catch {
    // noop
  }

  let components = pathname.split("/");

  parts.forEach((part) => {
    if (part) {
      components.push(...part.split("/"));
    }
  });

  components = components.filter((i) => i);

  if (url) {
    url.pathname = components.join("/");
    return url.toString();
  } else {
    return components.join("/");
  }
};

export default pathJoin;
