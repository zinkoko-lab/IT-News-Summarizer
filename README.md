# IT News Summarizer (Global & Japan)

NewsAPI から Global/Japan の IT ニュースを取得し、Gemini で要約して LINE に配信する Python アプリです。

## 構成

- `app/sources.py`: Global/Japan のニュース取得（各カテゴリ最大50件）
- `app/summarizer.py`: Gemini による Top 5 選定と要約
- `app/formatter.py`: LINE テキストメッセージ生成（URLなし）
- `app/line_client.py`: LINE Messaging API Push
- `app/pipeline.py`: 一連処理の統合
- `main.py`: ローカル実行
- `cloud_function.py`: Google Cloud Functions 用エントリ
- `lambda_function.py`: AWS Lambda 用エントリ

## セットアップ

```bash
cd /Users/zinkoko/projects/news_summarizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` に以下を設定してください。

- `NEWS_API_KEY`
- `GEMINI_API_KEY`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`
- 任意: `GEMINI_MODEL`, `TOP_N`, `REQUEST_TIMEOUT_SECONDS`

## 実行

```bash
python main.py
```

成功時は、取得候補数・送信件数を標準出力に JSON で表示し、LINE に通知します。

## 実装済み要件対応

- 取得カテゴリ分離:
  - `fetch_global_it_news`（検索語: `AI OR Technology OR "Global Trend"`）
  - `fetch_japan_it_news`（`country=jp`, `category=technology`）
- 24時間フィルタ: `published_at` を UTC 基準で判定
- 取得件数: `global` と `japan` をそれぞれ最大50件
- Top 5 選定: Gemini が各カテゴリから重要度順に5件を選定
- Gemini入力: タイトルとdescriptionのみ（URLは渡さない）
- LINE配信: URLなし、要約テキストのみ
- 出力形式:
  - `Global Top 5: [タイトル] + [要約]`
  - `Japan Top 5: [タイトル] + [要約]`
- 障害耐性: 取得失敗時はカテゴリ単位で空配列、Gemini失敗時はdescriptionベース要約へフォールバック

## デプロイの要点

### Google Cloud Functions

- エントリポイント: `run`
- ソースルート: このディレクトリ
- 実行環境変数: `.env` と同等のキーを設定
- Cloud Scheduler から HTTP トリガーで毎日実行

```bash
cd /Users/zinkoko/projects/news_summarizer
set -a; source .env; set +a
PROJECT_ID=your-gcp-project-id REGION=asia-northeast1 FUNCTION_NAME=it-news-summarizer \
./deploy/cloud_functions_deploy.sh
```

Cloud Scheduler 例（毎日 08:00 JST）:

```bash
gcloud scheduler jobs create http it-news-summarizer-daily \
  --location=asia-northeast1 \
  --schedule="0 8 * * *" \
  --time-zone="Asia/Tokyo" \
  --uri="https://<region>-<project>.cloudfunctions.net/it-news-summarizer" \
  --http-method=GET
```

### AWS Lambda

- ハンドラ: `lambda_function.handler`
- 依存ライブラリ込み ZIP またはコンテナでデプロイ
- EventBridge Scheduler で毎日実行

```bash
cd /Users/zinkoko/projects/news_summarizer
set -a; source .env; set +a
./deploy/lambda_package.sh
AWS_REGION=ap-northeast-1 FUNCTION_NAME=it-news-summarizer-lambda ROLE_ARN=arn:aws:iam::<account-id>:role/<lambda-exec-role> \
./deploy/lambda_deploy.sh
```

EventBridge Scheduler 例（毎日 08:00 JST）:

```bash
aws scheduler create-schedule \
  --name it-news-summarizer-daily \
  --schedule-expression "cron(0 23 * * ? *)" \
  --schedule-expression-timezone "Asia/Tokyo" \
  --flexible-time-window "{\"Mode\":\"OFF\"}" \
  --target "{\"Arn\":\"arn:aws:lambda:ap-northeast-1:<account-id>:function:it-news-summarizer-lambda\",\"RoleArn\":\"arn:aws:iam::<account-id>:role/<scheduler-invoke-role>\"}"
```

## 補足

- LINE Push API は1リクエスト最大5メッセージのため、クライアント側で分割送信しています。

## GitHub 管理 + 自動本番反映（Lambda）

`main` ブランチへの push ごとに本番 Lambda を自動デプロイする設定を追加済みです。

- Workflow: `.github/workflows/deploy-lambda-prod.yml`
- Trigger: `push` (`main`) / `workflow_dispatch`

### 1) GitHub リポジトリ作成と push

```bash
cd /Users/zinkoko/projects/news_summarizer
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin git@github.com:<your-account>/<your-repo>.git
git push -u origin main
```

### 2) GitHub Secrets を設定

`GitHub > Settings > Secrets and variables > Actions` に以下を登録:

- `AWS_ROLE_TO_ASSUME` (OIDCでAssumeするIAMロールARN)
- `AWS_REGION` (例: `ap-northeast-1`)
- `LAMBDA_FUNCTION_NAME` (例: `it-news-summarizer-lambda`)
- `NEWS_API_KEY`
- `GEMINI_API_KEY`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`
- 任意: `GEMINI_MODEL`, `TOP_N`, `REQUEST_TIMEOUT_SECONDS`

### 3) OIDC 用 IAM ロールの条件

`AWS_ROLE_TO_ASSUME` は少なくとも以下を許可:

- `lambda:UpdateFunctionCode`
- `lambda:UpdateFunctionConfiguration`
- `lambda:GetFunction`

信頼ポリシーは GitHub OIDC (`token.actions.githubusercontent.com`) からの `AssumeRoleWithWebIdentity` を許可してください。
