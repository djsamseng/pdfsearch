#!/bin/bash

if docker compose build; then
  echo "=== Build Success ==="
else
  echo "=== Build Failure ==="
  exit 1
fi

docker compose up -d
