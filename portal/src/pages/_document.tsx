import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html lang="en" className="h-full">
      <Head />
      <body className="font-sans antialiased text-gray-800 min-h-full flex flex-col [overflow-anchor:none]">
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
