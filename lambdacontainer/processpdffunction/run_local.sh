#!/bin/bash

if docker build -t processpdf . ; then
  echo "=== Build Success ==="
else
  echo "=== Build Failure ==="
  exit 1
fi
docker run -p 9000:8080 processpdf
