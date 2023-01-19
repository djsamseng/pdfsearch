
import React, { useState } from "react";

import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";

// https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-lambda/
const lambda_client = new LambdaClient({
  endpoint: "http://localhost:9000",
  region: "us-east-1",
  credentials: {
    accessKeyId: "DUMMY",
    secretAccessKey: "DUMMY",
  },
});

export async function lambdaTriggerPdfProcessing(pdfId: string) {
  // https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-lambda/classes/invokecommand.html
  try {
    const utf8Encode = new TextEncoder();
    const payload = utf8Encode.encode(JSON.stringify({
      pdfId: pdfId,
    }))
    console.log("Invoking lambda");
    const command = new InvokeCommand({
      FunctionName: "function",
      Payload: payload,
      InvocationType: "Event" // Event=Async, RequestResponse=Sync
    });
    lambda_client.send(command)
    .then(res => {
      console.log("Lambda client response:", res);
    })
    .catch(error => {
      // TODO: invoking lambda fails if already running (might just be due to local)
      console.error("Failed to invoke lambda:", error);
    })

    return true;
  }
  catch (error) {
    console.error("Failed to Invoke pdfProcessing:", error);
    return false;
  }
}

