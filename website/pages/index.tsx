
//import Image from 'next/image'
import Link from "next/link";
import styles from '../styles/Home.module.css'

import Layout from "../components/Layout";
import PdfUpload from '../components/pdfupload';

export default function Home() {
  const cardStyle = "m-4 p-6 text-left text-inherit border border-solid border-[#eaeaea] dark:border-[#222] rounded-lg transition-colors max-w-xs hover:text-[#0070f3] hover:border-[#0070f3]"
  return (
    <Layout>
      <h1 className="m-0 text-6xl text-center">
        Welcome <span className="text-blue-600 hover:underline hover:cursor-grab">Sam!</span>
      </h1>
      <PdfUpload />
      <div>
        <span>By using this service you agree to our </span>
        <Link href="/terms-of-service" className="text-blue-600">Terms Of Service</Link>
      </div>


      <p className="text-center my-16 text-2xl">
        Get started by editing{' '}
        <code className="bg-white border-2 p-3 text-lg font-code">pages/index.tsx</code>
      </p>

      <div className="w-full md:w-auto flex-col md:flex-row flex items-center justify-center flex-wrap max-w-4xl">
        <a href="https://nextjs.org/docs" className={cardStyle}>
          <h2 className="mb-4 text-2xl">Documentation &rarr;</h2>
          <p className="m-0 text-xl">Find in-depth information about Next.js features and API.</p>
        </a>

        <a href="https://nextjs.org/learn" className={cardStyle}>
          <h2 className="mb-4 text-2xl">Learn &rarr;</h2>
          <p className="m-0 text-xl"> Learn about Next.js in an interactive course with quizzes!</p>
        </a>

        <a
          href="https://github.com/vercel/next.js/tree/canary/examples"
          className={cardStyle}
        >
          <h2 className="mb-4 text-2xl">Examples &rarr;</h2>
          <p className="m-0 text-xl">Discover and deploy boilerplate example Next.js projects.</p>
        </a>

        <a
          href="https://vercel.com/new?utm_source=create-next-app&utm_medium=default-template&utm_campaign=create-next-app"
          target="_blank"
          rel="noopener noreferrer"
          className={cardStyle}
        >
          <h2 className="mb-4 text-2xl">Deploy &rarr;</h2>
          <p className="m-0 text-xl">
            Instantly deploy your Next.js site to a public URL with Vercel.
          </p>
        </a>
      </div>
    </Layout>
  )
}
