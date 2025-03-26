import type { AppProps } from 'next/app';
import { SessionProvider } from 'next-auth/react';
import Head from 'next/head';
import '../styles/globals.css';

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <SessionProvider session={pageProps.session}>
      <Head>
        <link rel="icon" href="/favicon.ico" type="image/x-icon" />
        <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon" />
      </Head>
      <style jsx global>{`
        /* Hide Next.js default badge/logo in the bottom-left corner */
        .nextjs-logo-container {
          display: none !important;
        }
        /* Target common classnames or selectors that Next.js uses for their badge */
        [rel="noopener noreferrer"][target="_blank"][href="https://vercel.com"] {
          display: none !important;
        }
        /* Hidden by style injection to ensure it's not displayed */
        body::after {
          content: none !important;
        }
      `}</style>
      <Component {...pageProps} />
    </SessionProvider>
  );
}

export default MyApp;