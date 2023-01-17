

export default function Footer() {
  return (
    <footer className="flex py-6 border-t border-solid border-[#eaeaea] dark:border-[#222] justify-center items-center">
      <a
        href="https://vercel.com?utm_source=create-next-app&utm_medium=default-template&utm_campaign=create-next-app"
        target="_blank"
        rel="noopener noreferrer"
        className="flex justify-center content-center items-center flex-grow"
      >
        Powered by{' '}
        <span className="h-4 ml-2">
          {/*<Image src="/vercel.svg" alt="Vercel Logo" width={72} height={16} />*/}
        </span>
      </a>
    </footer>
  );
}
