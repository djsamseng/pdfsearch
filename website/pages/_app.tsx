import '../styles/globals.css'
import React from "react";
import type { AppProps } from 'next/app'

import { AwsConnectorContext } from '../components/AwsConnector'

export default function App({ Component, pageProps }: AppProps) {
  const [ processPdfLoadingStatus,  setProcessPdfLoadingStatus ] = React.useState(false);
  return (
    <AwsConnectorContext.Provider value={{ processPdfLoadingStatus, setProcessPdfLoadingStatus }}>
      <Component {...pageProps} />
    </AwsConnectorContext.Provider>
  )
}
