import React from "react";
import Link from "next/link";

export default function NavBreadcrumb({
  links,
}: {
  links: Array<{
    text: string;
    icon?: React.ReactNode;
    href: string;
  }>
}) {
  if (links.length === 0) {
    return (
      <></>
    )
  }
  return (
    <nav>
      <ol className="inline-flex items-center space-x-1 md:space-x-3">
        { links.map((link, idx) => {
          if (idx === 0 && idx < links.length - 1) {
            return (
              <li className="inline-flex items-center">
                <Link href={link.href} className="inline-flex items-center text-sm font-medium text-gray-700 hover:text-blue-600">
                  { link.icon }
                  { link.text }
                </Link>
              </li>
            );
          }
          else if (idx < links.length - 1) {
            return (
              <li>
                <div className="flex items-center">
                  <svg aria-hidden="true" className="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"></path></svg>
                  { link.icon }
                  <Link href={link.href} className="ml-1 text-sm font-medium text-gray-700 hover:text-blue-600 md:ml-2">{link.text}</Link>
                </div>
              </li>
            );
          }
          else {
            return (
              <li aria-current="page">
                <div className="flex items-center">
                  <svg aria-hidden="true" className="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"></path></svg>
                  <span className="ml-1 text-sm font-medium text-gray-500 md:ml-2">{link.text}</span>
                </div>
              </li>
            )
          }
        })}
      </ol>
    </nav>
  )
}