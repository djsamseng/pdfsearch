import '../styles/globals.css'
import React from "react";
import type { AppProps } from 'next/app'

import { createBrowserSupabaseClient } from '@supabase/auth-helpers-nextjs';
import { SessionContextProvider, Session } from '@supabase/auth-helpers-react';

export default function App({ Component, pageProps }: AppProps<{
  initialSession: Session,
}>) {
  const [ supabase ] = React.useState(() => createBrowserSupabaseClient());
  return (
    <SessionContextProvider supabaseClient={supabase} initialSession={pageProps.initialSession}>
      <Component {...pageProps} />
    </SessionContextProvider>
  )
}
