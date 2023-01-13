# PDF Search

## Installation
```bash
cd website && npm install
```
Download pdflib [Prebuilt (older browsers)](https://mozilla.github.io/pdf.js/getting_started/) for Safari support and save folder as `pdfjs-3`

```bash
cd flaskapi && pip3 install -r requirements.txt
pip3 install git+https://github.com/pdfminer/pdfminer.six
```

```bash
ln -s ~/dev/pdfsearch/pdfextract/ ~/dev/pdfsearch/lambdacontainer/processpdffunction/pdfextract
cd website && npx supabase start
```
- Docker Desktop no longer creates /var/run/docker.sock [See this issue](https://github.com/supabase/cli/issues/167#issuecomment-1291465761)
- To fix
```bash
npx supabase start --debug # Outputs /var/run/docker.sock
sudo ln -s ~/.docker/desktop/docker.sock /var/run/docker.sock
```
### Generate database types from local database
```bash
sudo ln -s ~/.docker/desktop/docker.sock /var/run/docker.sock # May need to rerun
npx supabase gen types typescript --local > utils/database.types.ts
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
- [nextjs user authentication with supabase](https://dev.to/mryechkin/user-authentication-in-nextjs-with-supabase-4l12)
- [Learning nextjs progress](https://nextjs.org/learn/basics/create-nextjs-app?utm_source=next-site&utm_medium=homepage-cta&utm_campaign=next-website)
- [Learning effects in React](https://beta.reactjs.org/learn/synchronizing-with-effects#not-an-effect-initializing-the-application)
- [Deploy flask application on vercel](https://dev.to/yash_makan/4-best-python-web-app-hosting-services-for-freewith-complete-process-57nb)
- [Create test lambda function and run locally with python](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
  - [More in depth tutorial - Deploy lambda using containers](https://aws.amazon.com/blogs/aws/new-for-aws-lambda-container-image-support/)
  - [Learning about AWS Lambda progress](https://docs.aws.amazon.com/lambda/latest/dg/foundation-progmodel.html)
  - [Clean up Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/getting-started.html#gettingstarted-cleanup)
  - [Example auto cleanup script](https://github.com/awsdocs/aws-lambda-developer-guide/blob/main/sample-apps/blank-python/5-cleanup.sh)
- [Supabase NextJS](https://supabase.com/docs/guides/getting-started/tutorials/with-nextjs)

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

## Production
- [Vercel Free tier](https://vercel.com/pricing)
  - Any file inside the folder pages/api is mapped to /api/* and will be treated as an API endpoint (a serverless function)
    - serverless functions: 100GB-hours = 360,000 requests with 1 second duration = 8 requests/minute
    - GB-hours = duration * memory allocated [link](https://vercel.com/guides/what-are-gb-hrs-for-serverless-function-execution)
      - default = 1GB memory [configuration](https://vercel.com/docs/project-configuration#project-configuration/functions)
  - Middleware becomes edge functions [nextjs deployment reference](https://nextjs.org/docs/deployment)
    - [Middleware matching requests](https://nextjs.org/docs/advanced-features/middleware)
    - edge functions: 500_000 execution units, 1 million invocations
  - 100 GB Bandwidth
- [AWS Free tier](https://aws.amazon.com/free/?all-free-tier.sort-by=item.additionalFields.SortRank&all-free-tier.sort-order=asc&awsf.Free%20Tier%20Types=*all&awsf.Free%20Tier%20Categories=*all)
  - Amazon DynamoDB always free
    - 25GB storage
    - 200M requests per month
    - DynamoDB streams for monitoring database changes
  - AWS Lambda always free
    - 1 millions requests/month = 20 requests/minute
    - 3.2 million seconds compute time/month = 53_333 minutes = 888 hours = 37 days
  - AWS S3 storage
    - $0.023/GB + $0.005 per 1000 requests
- [Firebase Free tier](https://firebase.google.com/pricing)
  - Realtime database
    - 1 GB storage
    - 10 GB transfer
  - Firebase database
    - 1 GB storage
    - 50,000 reads
    - 20,000 writes
    - 20,000 deletes
    - charged for listening/realtime updates each time the query results change (awesome for a websocket)
  - Cloud storage
    - 5 GB storage
    - 30GB/day
    - 2,100,000 operations
  - Cloud functions [pricing](https://cloud.google.com/functions/pricing)
    - [Python support](https://cloud.google.com/functions/docs/concepts/python-runtime)
    - first 2 million invocations free
    - 400,000 GB-seconds
    - 200,000 GHz-seconds compute time
    - 5GB Internet traffic outbound
- AWS has better reviews, better performance, better pricing, better documentation and python support, better configuration UI

### Workflow
- User uploads pdf to dynamodb. Return key
  - [Javascript API for dynamodb](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStarted.WriteItem.html)
  - [NextJS API Routes with dynamodb](https://github.com/vercel/examples/tree/main/solutions/aws-dynamodb)
- User triggers pdf processing by sending a POST request to lambda
  - [Https endpoint to invoke lambda function](https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html)
  - [Lambda getting started](https://docs.aws.amazon.com/lambda/latest/dg/getting-started.html)
  - Lambda function timeout default 3 seconds, max 15 minutes [configuration](https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-common.html#configuration-timeout-console)
- Lambda writes to dynamodb with progress
  - [Python API for dynamodb](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html)
  - [Dynamodb streams for monitoring progress](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)

## Accounts
- Gmail: devcider@gmail.com
- AWS: devcider@gmail.com
- Docker

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
