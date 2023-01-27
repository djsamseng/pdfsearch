
import React from "react";

import Header from "./header";
import Navbar from "./Navbar";
import Footer from "./Footer";

// TODO: pageProps https://nextjs.org/docs/basic-features/layouts
export default function Layout({ children }: { children: React.ReactNode}) {
  const cardStyle = "m-4 p-6 text-left text-inherit border border-solid border-[#eaeaea] dark:border-[#222] rounded-lg transition-colors max-w-xs hover:text-[#0070f3] hover:border-[#0070f3]"
  return (
    <>
      <div className="px-8 py-4">
        <Header />
        <Navbar />
        <main className="min-h-screen mx-auto py-2 flex flex-col items-center">
          {children}
        </main>
        <Footer />
      </div>
    </>
  )
}