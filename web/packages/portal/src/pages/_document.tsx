import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html lang="en" className="h-full">
      <Head>
        <link
          rel="icon"
          type="image/x-icon"
          sizes="48x48"
          href="/favicon.ico"
        />
      </Head>
      <body className="font-sans antialiased text-gray-800 min-h-full flex flex-col [overflow-anchor:none]">
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
