#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   AWS_REGION=ap-northeast-1 FUNCTION_NAME=it-news-summarizer-lambda \
#   ./deploy/lambda_deploy.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
FUNCTION_NAME="${FUNCTION_NAME:-it-news-summarizer-lambda}"
ROLE_ARN="${ROLE_ARN:-}"
ZIP_PATH="$ROOT_DIR/build/lambda/news_summarizer_lambda.zip"

wait_until_updated() {
  aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION"
}

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

if [[ ! -f "$ZIP_PATH" ]]; then
  "$ROOT_DIR/deploy/lambda_package.sh"
fi

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --zip-file "fileb://$ZIP_PATH" >/dev/null
  wait_until_updated

  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --handler lambda_function.handler \
    --runtime python3.11 \
    --timeout 60 \
    --environment "Variables={NEWS_API_KEY=$NEWS_API_KEY,GEMINI_API_KEY=$GEMINI_API_KEY,LINE_CHANNEL_ACCESS_TOKEN=$LINE_CHANNEL_ACCESS_TOKEN,LINE_USER_ID=$LINE_USER_ID,GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.5-flash},TOP_N=${TOP_N:-5},REQUEST_TIMEOUT_SECONDS=${REQUEST_TIMEOUT_SECONDS:-20}}" >/dev/null
  wait_until_updated

  echo "Updated Lambda: $FUNCTION_NAME ($AWS_REGION)"
else
  if [[ -z "$ROLE_ARN" ]]; then
    echo "ROLE_ARN is required when creating a new Lambda function"
    exit 1
  fi

  aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --runtime python3.11 \
    --role "$ROLE_ARN" \
    --handler lambda_function.handler \
    --timeout 60 \
    --zip-file "fileb://$ZIP_PATH" \
    --environment "Variables={NEWS_API_KEY=$NEWS_API_KEY,GEMINI_API_KEY=$GEMINI_API_KEY,LINE_CHANNEL_ACCESS_TOKEN=$LINE_CHANNEL_ACCESS_TOKEN,LINE_USER_ID=$LINE_USER_ID,GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.5-flash},TOP_N=${TOP_N:-5},REQUEST_TIMEOUT_SECONDS=${REQUEST_TIMEOUT_SECONDS:-20}}" >/dev/null
  wait_until_updated

  echo "Created Lambda: $FUNCTION_NAME ($AWS_REGION)"
fi
