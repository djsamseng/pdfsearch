
import React, { useState } from "react";

import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";
import { maxHeaderSize } from "http";

export const AwsConnectorContext = React.createContext({
  processPdfLoadingStatus: false,
  setProcessPdfLoadingStatus: (val: boolean) => {}
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

export async function triggerPdfProcessing(pdfId: string) {
  // https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/clients/client-lambda/classes/invokecommand.html
  try {
    // This is sending the request but CORS is blocking the response
    // https://github.com/lambci/docker-lambda/issues/256
    if (true) {
      await fetch("http://localhost:9000/2015-03-31/functions/function/invocations", {
        method: "post",
        mode: "no-cors", // For dev
        body: JSON.stringify({
          pdfId: pdfId,
        }),
      });
    }
    else {
      // Configure CORS https://github.com/aws/aws-lambda-runtime-interface-emulator/issues/16
      // In the AWS console you can indeed configure CORS for HTTP requests to lambda. By default it allows all origins
      // For local development it seems we'd just need to [add the headers](https://stackoverflow.com/questions/12830095/setting-http-headers)
      // if [r.Method == Post](https://github.com/aws/aws-lambda-runtime-interface-emulator/blob/2ca3e4aec8ef5cec6139c531f8dd8c31dffc5bcd/cmd/aws-lambda-rie/handlers.go#L60).
      // Should be able to compile https://github.com/aws/aws-lambda-runtime-interface-emulator/blob/develop/Makefile#L23
      // then pull in the image in my own docker
      // See make integ-tests-and-compile
      const command = new InvokeCommand({
        FunctionName: "processpdf",
        Payload: {
          // @ts-ignore
          pdfkey: "plan.pdf",
        }
      });
      const res = await lambda_client.send(command);
      console.log(res);
    }

  }
  catch (error) {
    console.error("Failed to Invoke pdfProcessing:", error);
    return false;
  }
}

