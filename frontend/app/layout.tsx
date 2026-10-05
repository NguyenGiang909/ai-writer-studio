import React from "react";
import "./globals.css";
import { getLang } from "../lib/lang-server";

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const lang = await getLang();
  return (
    <html lang={lang}>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{if(['dark','black'].includes(localStorage.getItem('writer-theme')))document.documentElement.dataset.theme='dark'}catch(e){}",
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
