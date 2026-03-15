#!/usr/bin/env bash
set -euo pipefail

# Build deployment zip for AWS Lambda (x86_64)
# Usage:
#   ./deploy/lambda_package.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/lambda"
PKG_DIR="$BUILD_DIR/package"
ZIP_PATH="$BUILD_DIR/news_summarizer_lambda.zip"

rm -rf "$BUILD_DIR"
mkdir -p "$PKG_DIR"

python3 -m pip install -r "$ROOT_DIR/requirements.txt" -t "$PKG_DIR"

cp -R "$ROOT_DIR/app" "$PKG_DIR/"
cp "$ROOT_DIR/lambda_function.py" "$PKG_DIR/"

(
  cd "$PKG_DIR"
  zip -r "$ZIP_PATH" . >/dev/null
)

echo "Lambda zip created: $ZIP_PATH"
