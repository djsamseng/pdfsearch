

export default function Footer() {
  return (
    <footer className="flex py-6 border-t border-solid border-[#eaeaea] dark:border-[#222] justify-center items-center">
      <a
        href="https://vercel.com?utm_source=create-next-app&utm_medium=default-template&utm_campaign=create-next-app"
        target="_blank"
        rel="noopener noreferrer"
        className="flex justify-center content-center items-center flex-grow"
      >
        <div className="w-[32px] h-[25px]">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512">
            <linearGradient id="colorFill" gradientTransform="rotate(90)">
              <stop offset="5%" stop-color="#FE544E" />
              <stop offset="95%" stop-color="#B23230" />
            </linearGradient>
            <path fill="url('#colorFill')" d="M381 114.9L186.1 41.8c-16.7-6.2-35.2-5.3-51.1 2.7L89.1 67.4C78 73 77.2 88.5 87.6 95.2l146.9 94.5L136 240 77.8 214.1c-8.7-3.9-18.8-3.7-27.3 .6L18.3 230.8c-9.3 4.7-11.8 16.8-5 24.7l73.1 85.3c6.1 7.1 15 11.2 24.3 11.2H248.4c5 0 9.9-1.2 14.3-3.4L535.6 212.2c46.5-23.3 82.5-63.3 100.8-112C645.9 75 627.2 48 600.2 48H542.8c-20.2 0-40.2 4.8-58.2 14L381 114.9zM0 480c0 17.7 14.3 32 32 32H608c17.7 0 32-14.3 32-32s-14.3-32-32-32H32c-17.7 0-32 14.3-32 32z"/>
          </svg>
        </div>
        <span className="h-4 ml-2">
          {/*<Image src="/vercel.svg" alt="Vercel Logo" width={72} height={16} />*/}
        </span>
      </a>
    </footer>
  );
}
