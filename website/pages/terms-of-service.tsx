

import Layout from "../components/Layout"

export default function TermsOfService() {
  return (
    <Layout>
      <div className="text-center">
        <span>By using this service you agree to the following</span>
        <div className="my-2">
          <ul className="list-decimal list-inside">
            <li>
              My sister sells your house
            </li>
            <li>
              Frank builds your next house
            </li>
            <li>
              You move in a happy customer
            </li>
          </ul>
        </div>
      </div>
    </Layout>

  )
}