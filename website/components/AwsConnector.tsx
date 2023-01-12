
import React, { useState } from "react";

import { DynamoDBClient, GetItemCommand, } from "@aws-sdk/client-dynamodb";
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";
import { maxHeaderSize } from "http";

export const AwsConnectorContext = React.createContext({
  processPdfLoadingStatus: false,
  setProcessPdfLoadingStatus: (val: boolean) => {}
});

// https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-dynamodb/index.html
const db_client = new DynamoDBClient({
  endpoint: "http://localhost:8000",
  region: "us-east-1",
  credentials: {
    accessKeyId: "DUMMY",
    secretAccessKey: "DUMMY",
  }
});
// https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-lambda/
const lambda_client = new LambdaClient({
  endpoint: "http://localhost:9000",
  region: "us-east-1",
  credentials: {
    accessKeyId: "DUMMY",
    secretAccessKey: "DUMMY",
  },
  disableHostPrefix: true,
  tls: false,
})

const TableNames = {
  STREAMING_PROGRESS: "streaming_progress",
}

async function triggerPdfProcessingImpl(pdfId: string, setProcessPdfLoadingStatus: Function) {
  // https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-lambda/classes/invokecommand.html
  try {
    // This is sending the request but CORS is blocking the response
    // https://github.com/lambci/docker-lambda/issues/256
    const resp = await fetch("http://localhost:9000/2015-03-31/functions/function/invocations", {
      method: "post",
      body: JSON.stringify({
        pdfkey: "plan.pdf"
      })
    });
    console.log(resp);
    return;
    const command = new InvokeCommand({
      FunctionName: "processpdf",
      Payload: {
        // @ts-ignore
        pdfkey: "plan.pdf",
      }
    });
    const res = await lambda_client.send(command);
  }
  catch (error) {
    console.error("Failed to Invoke pdfProcessing:", error);
    setProcessPdfLoadingStatus(false);
    return false;
  }
}

async function waitForPdfProcessingImpl(pdfId: string, timeSoFar: number, setProcessPdfLoadingStatus: Function) {
  if (timeSoFar > 10) {
    setProcessPdfLoadingStatus(false);
    return;
  }

  const command = new GetItemCommand({
    TableName: TableNames.STREAMING_PROGRESS,
    Key: {
      "value": {
        "S": pdfId
      }
    },
  });
  try {
    const res = await db_client.send(command);
    console.log(res);
    const timeoutMs = 1000;
    setTimeout(() => {
      waitForPdfProcessingImpl(pdfId, timeSoFar + timeoutMs, setProcessPdfLoadingStatus);
    }, timeoutMs);
  }
  catch (error) {
    console.error("Failed to get loading status", error);
    setProcessPdfLoadingStatus(false);
  }
}

export async function triggerPdfProcessing(pdfId: string, setProcessPdfLoadingStatus: Function) {
  setProcessPdfLoadingStatus(true);
  const triggered = await triggerPdfProcessingImpl(pdfId, setProcessPdfLoadingStatus);
  if (triggered) {
    // waitForPdfProcessingImpl(pdfId, 0);
  }

}

