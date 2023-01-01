# PDF Search

## Installation
```bash
cd website && npm install
```
Download pdflib [Prebuilt (older browsers)](https://mozilla.github.io/pdf.js/getting_started/) for Safari support and save folder as `pdfjs-3`

```bash
cd flaskapi && pip3 install -r requirements.txt
git clone git@github.com:djsamseng/pdfminer.six.git
cd pdfminer.six # edit layout.py LTChar self.fontsize e= fontsize
pip3 install -e .
```

## Running
```bash
cd website && npm run dev
```
```bash
cd flaskapi && flask --app main.py --debug run
# or python3 -m flask --app main.py --debug run
```

## TODO
- [pdfjs in react](https://pspdfkit.com/blog/2021/how-to-build-a-reactjs-viewer-with-pdfjs/)
- [nextjs head to include scripts](https://nextjs.org/docs/api-reference/next/head)
- [run python from react](https://python.plainenglish.io/python-in-react-with-pyodide-a9c45d4d38ff)
- [nextjs user authentication with supabase](https://dev.to/mryechkin/user-authentication-in-nextjs-with-supabase-4l12)
- [Learning nextjs progress](https://nextjs.org/learn/basics/create-nextjs-app?utm_source=next-site&utm_medium=homepage-cta&utm_campaign=next-website)
- [Learning effects in React](https://beta.reactjs.org/learn/synchronizing-with-effects#not-an-effect-initializing-the-application)
- [Deploy flask application on vercel](https://dev.to/yash_makan/4-best-python-web-app-hosting-services-for-freewith-complete-process-57nb)

## Coding work
### Backend Python
- Fast lookup of symbols by organzing pdf shapes to nearby shapes. Create a BTree keyed by x,y location
- Store known symbols and searches in a database per architect
### Fontend NextJS
- Sticky notes interface. Drill in per page/higlight and show on PDF
- PDF viewer interface. Click on A## and see all matches. Click on A21 and see all other windows
- Square feet calculator per room

## Data processing
- Make a request to the server, opens a websocket with time to response [AWS websocket API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)
- Rest API to upload PDF and store in S3
- AWS SQS to publish to queue
- EC2 workers with gpu pop off SQS queue
- [By using an API Gateway WebSocket API in front of Lambda, you don’t need a machine to stay always on, eating away your project budget. API Gateway handles connections and invokes Lambda whenever there’s a new event. Scaling is handled on the service side. To update our connected clients from the backend, we can use the API Gateway callback URL.](https://aws.amazon.com/blogs/compute/from-poll-to-push-transform-apis-using-amazon-api-gateway-rest-apis-and-websockets/)
  - **Good example of what we want**


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
