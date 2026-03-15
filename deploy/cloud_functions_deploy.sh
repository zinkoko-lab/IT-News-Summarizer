#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   PROJECT_ID=xxx REGION=asia-northeast1 FUNCTION_NAME=it-news-summarizer \
#   ./deploy/cloud_functions_deploy.sh

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-asia-northeast1}"
FUNCTION_NAME="${FUNCTION_NAME:-it-news-summarizer}"
RUNTIME="${RUNTIME:-python311}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID is required"
  exit 1
fi

required_envs=(
  NEWS_API_KEY
  GEMINI_API_KEY
  LINE_CHANNEL_ACCESS_TOKEN
  LINE_USER_ID
)

for name in "${required_envs[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "Environment variable missing: $name"
    exit 1
  fi
done

gcloud functions deploy "$FUNCTION_NAME" \
  --gen2 \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --runtime "$RUNTIME" \
  --source . \
  --entry-point run \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars "NEWS_API_KEY=$NEWS_API_KEY,GEMINI_API_KEY=$GEMINI_API_KEY,LINE_CHANNEL_ACCESS_TOKEN=$LINE_CHANNEL_ACCESS_TOKEN,LINE_USER_ID=$LINE_USER_ID,GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.5-flash},TOP_N=${TOP_N:-5},REQUEST_TIMEOUT_SECONDS=${REQUEST_TIMEOUT_SECONDS:-20}"

echo "Deployed Cloud Function: $FUNCTION_NAME ($REGION)"
