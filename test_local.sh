#!/bin/bash

curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{ "pdfId": "plan.pdf" }'
echo ""