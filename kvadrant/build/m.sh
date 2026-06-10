#!/usr/bin/env bash
# usage: echo '<graphql-json-body>' | m.sh   (posts to /metadata with API key)
KEY="$(cat "$(dirname "$0")/.apikey")"
curl -s -X POST http://localhost:3000/metadata -H "Authorization: Bearer $KEY" -H 'content-type: application/json' --data-binary @-
