

import { useRouter } from "next/router";
import Layout from "../../components/Layout";

export default function Profile() {
  const router = useRouter();
  const {
    userid: userId,
  } = router.query;
  return (
    <Layout>
      <h1 className="text-6xl text-center">
        Welcome <span className="text-blue-600 hover:underline hover:cursor-grab">Sam!</span>
      </h1>
    </Layout>
  )
}