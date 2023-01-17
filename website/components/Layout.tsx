
import React from "react";

import Header from "./header";
import Navbar from "./Navbar";
import Footer from "./Footer";

export default function Layout({ children }: { children: React.ReactNode}) {
  return (
    <>
      <div className="px-8">
        <Header />
        <Navbar />
        <main className="min-h-screen py-16 flex flex-col justify-center items-center">
          {children}
        </main>
        <Footer />
      </div>
    </>
  )
}