# PDF Search

## Installation
```bash
npm install
```
Download pdflib [Prebuilt (older browsers)](https://mozilla.github.io/pdf.js/getting_started/) for Safari support and save folder as `pdfjs-3`

## TODO
- [pdfjs in react](https://pspdfkit.com/blog/2021/how-to-build-a-reactjs-viewer-with-pdfjs/)
- [nextjs head to include scripts](https://nextjs.org/docs/api-reference/next/head)
- [run python from react](https://python.plainenglish.io/python-in-react-with-pyodide-a9c45d4d38ff)
- [nextjs user authentication with supabase](https://dev.to/mryechkin/user-authentication-in-nextjs-with-supabase-4l12)

1. [Create Flask server](https://flask.palletsprojects.com/en/2.2.x/quickstart/)
2. Use [test.html](test.html) to render the pdf. [Render without uploading](https://stackoverflow.com/questions/56916887/access-file-before-upload-using-pdf-js)
3. Use [drawexample.html](drawexample.html) to highlight a region
4. Send the region to the flask server
5. Use [miner_test.py](https://github.com/djsamseng/floorplanreader/blob/main/miner_test.py) to find similar elements
6. [Deploy flask application on vercel](https://dev.to/yash_makan/4-best-python-web-app-hosting-services-for-freewith-complete-process-57nb)


## Getting Started

Open test.html to test pdfjs and pdflib working together

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `pages/index.tsx`. The page auto-updates as you edit the file.

[API routes](https://nextjs.org/docs/api-routes/introduction) can be accessed on [http://localhost:3000/api/hello](http://localhost:3000/api/hello). This endpoint can be edited in `pages/api/hello.ts`.

The `pages/api` directory is mapped to `/api/*`. Files in this directory are treated as [API routes](https://nextjs.org/docs/api-routes/introduction) instead of React pages.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js/) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/deployment) for more details.
