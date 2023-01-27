
//import Image from 'next/image'
import Link from "next/link";
import styles from '../styles/Home.module.css'

import Layout from "../components/Layout";
import PdfUpload from '../components/pdfupload';
import MyPdfsView from "../components/MyPdfsView";

export default function Home() {
  const cardStyle = "m-4 p-6 text-left text-inherit border border-solid border-[#eaeaea] dark:border-[#222] rounded-lg transition-colors max-w-xs hover:text-[#0070f3] hover:border-[#0070f3]"
  return (
    <Layout>

      <PdfUpload />
      <div>
        <span>By using this service you agree to our </span>
        <Link href="/terms-of-service" className="text-blue-600">Terms Of Service</Link>
      </div>
      <MyPdfsView />
    </Layout>
  )
}
