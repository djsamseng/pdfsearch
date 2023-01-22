
import React from "react";

import Header from "./header";
import Navbar from "./Navbar";
import Footer from "./Footer";

// TODO: pageProps https://nextjs.org/docs/basic-features/layouts
export default function Layout({ children }: { children: React.ReactNode}) {
  const cardStyle = "m-4 p-6 text-left text-inherit border border-solid border-[#eaeaea] dark:border-[#222] rounded-lg transition-colors max-w-xs hover:text-[#0070f3] hover:border-[#0070f3]"
  return (
    <>
      <div className="px-8">
        <Header />
        <Navbar />
        <main className="min-h-screen container mx-auto py-16 flex flex-col justify-center items-center">
          <h1 className="m-0 text-6xl text-center">
            Welcome <span className="text-blue-600 hover:underline hover:cursor-grab">Sam!</span>
          </h1>
          {children}
        </main>
        <Footer />
      </div>
    </>
  )
}