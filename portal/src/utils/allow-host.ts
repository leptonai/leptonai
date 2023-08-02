export const allowHost = (url?: string): url is string => {
  try {
    if (!url) {
      return false;
    }
    const { hostname } = new URL(url);
    // use regex to allow all subdomains of lepton.ai
    const allowedHosts = [/^(.+\.)?lepton\.ai$/i];
    if (process.env.NODE_ENV !== "production") {
      allowedHosts.push(
        ...[/^lepton-.+-leptonai\.vercel\.app$/i, /^localhost$/i],
      );
    }
    return allowedHosts.some((allowedHost) => allowedHost.test(hostname));
  } catch {
    return false;
  }
};
