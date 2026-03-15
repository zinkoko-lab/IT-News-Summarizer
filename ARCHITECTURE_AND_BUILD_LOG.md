# IT News Summarizer 開発記録（Global/Japan + Gemini + LINE + AWS Lambda）

## 1. はじめに
本記事は、以下を目的に構築したアプリの実装内容を、最初から現在まで整理した記録です。

- ITニュースを自動収集する
- Geminiで日本語要約する
- LINEに毎日自動配信する
- GitHub管理し、変更が本番に反映される体制を作る

現在の実装は **AWS Lambda 本番運用可能** な状態です。

---

## 2. アプリの全体像

### 2.1 何をするアプリか
毎日、Global/JapanのITニュースを収集し、Geminiで要約してLINEに送信します。

- Global: NewsAPI `everything` を中心に取得
- Japan: NewsAPI `top-headlines(country=jp, category=technology)` を中心に取得
- 要約: Gemini（日本語で読みやすく要約）
- 配信: LINE Messaging API（テキスト配信）

### 2.2 現在の処理フロー
1. NewsAPIから各カテゴリ最大50件取得
2. 重複除去（URL正規化ベース）
3. Geminiに候補を渡し、各カテゴリTop5を選定・要約
4. LINEへ `Global Top 5 / Japan Top 5` を送信
5. AWS Scheduler経由で毎日自動実行

---

## 3. 実装構成（コード構造）

主要ファイル:

- `app/sources.py`
  - ニュース取得ロジック
  - Global/Japanを分離
  - 取得不足時のフォールバック
- `app/summarizer.py`
  - Geminiプロンプト生成
  - JSON形式レスポンス解析
  - フォールバック要約
- `app/formatter.py`
  - LINE配信用テキスト整形
  - 連番フォーマット化
- `app/line_client.py`
  - LINE Push API呼び出し
- `app/pipeline.py`
  - 取得→要約→配信を統合
- `lambda_function.py`
  - Lambdaエントリポイント
- `deploy/lambda_package.sh`
  - Lambda配布ZIP作成
- `deploy/lambda_deploy.sh`
  - Lambda本番反映（待機処理込み）

---

## 4. 要件変更の反映履歴（重要ポイント）

### 4.1 取得カテゴリ分離
- `fetch_global_it_news`
- `fetch_japan_it_news`

### 4.2 件数変更
- 初期: 5件取得 → 仕様変更で **最大50件取得**
- 最終出力: Gemini選定で **Top5配信**

### 4.3 要約フォーマット変更
複数回の要件変更を経て、現在は以下形式:

```text
1. [日本語タイトル]
- [要約]
URL: [記事URL]
```

### 4.4 URL仕様
- 一時期URL非表示に変更
- 最終的に「URLを含める」仕様へ再変更し本番反映済み

---

## 5. AWS Lambda の仕組み（このアプリ文脈で理解する）

### 5.1 Lambdaとは
Lambdaは「サーバーを常時立てずに関数を実行する」仕組みです。

- コードをZIPで配置
- 実行イベントが来た時だけ起動
- 実行時間に応じて課金

### 5.2 このアプリでのLambda実行
- 関数名: `it-news-summarizer-lambda`
- ハンドラ: `lambda_function.handler`
- 実行時に環境変数からAPIキーを読む
- 処理結果をJSONで返す

### 5.3 Scheduler連携
自動実行は Lambda 自身ではなく **EventBridge Scheduler** が行います。

- Scheduler が指定時刻にLambdaをInvoke
- Scheduler用IAMロールが必要
- ロールには `lambda:InvokeFunction` 権限が必要
- 信頼ポリシーで `scheduler.amazonaws.com` を許可する必要がある

### 5.4 デプロイで詰まりやすい点

1. `ResourceConflictException`
- Lambda更新中に連続更新すると発生
- 対策: `aws lambda wait function-updated` を挟む（実装済み）

2. Schedulerロールエラー
- `The execution role ... must allow AWS EventBridge Scheduler to assume the role`
- 対策: 信頼ポリシーに `scheduler.amazonaws.com`

3. invoke時のpayload JSONエラー
- AWS CLI v2は `--cli-binary-format raw-in-base64-out` が必要

---

## 6. 本番反映の運用方式

### 6.1 現在可能な反映方法
- 直接デプロイ: `deploy/lambda_deploy.sh`
- GitHub Actions: `push main` で自動デプロイ（設定済み）

### 6.2 GitHub Actions方式
ワークフロー:
- `.github/workflows/deploy-lambda-prod.yml`

トリガー:
- `push` to `main`
- `workflow_dispatch`

必要Secrets:
- `AWS_ROLE_TO_ASSUME`
- `AWS_REGION`
- `LAMBDA_FUNCTION_NAME`
- `NEWS_API_KEY`
- `GEMINI_API_KEY`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`
- 任意: `GEMINI_MODEL`, `TOP_N`, `REQUEST_TIMEOUT_SECONDS`

---

## 7. Prompt Engineering 実践知見（このプロジェクトで効いたこと）

このアプリは、要件変更が多かったため、プロンプト設計の良し悪しが結果に直結しました。

### 7.1 うまくいくプロンプトの原則

1. 役割（ペルソナ）を明確にする
- 例: 「あなたはITニュース専門の編集者です」

2. 出力形式を機械可読に固定する
- JSONを強制し、キー名を固定
- 例: `index`, `title_ja`, `summary`

3. 禁止事項を明記する
- URLを含めない（または含める）
- 事実を創作しない

4. 入力情報を必要最小限にする
- タイトルとdescriptionのみ
- ノイズを減らす

5. フォールバック前提で設計する
- 解析失敗時にルールベース要約へ切替

### 7.2 実運用で使いやすいプロンプト例（本アプリ向け）

```text
あなたはITニュース専門の編集者です。候補記事から重要度順に上位を選び、各記事を要約してください。

ルール:
- 出力はビジネスパーソン向けの自然な日本語
- 技術用語は正確に維持
- 英語記事は文脈を踏まえて日本語に意訳
- 候補外の事実を創作しない
- 出力はJSONのみ

JSON形式:
{"items":[{"index":1,"title_ja":"...","summary":"..."}]}
```

### 7.3 「うまくアプリを作る」ための依頼プロンプト例（開発AI向け）

```text
目的:
NewsAPIからGlobal/Japanのニュースを最大50件ずつ取得し、Geminiで各カテゴリTop5を選んで要約し、LINEに送るPythonアプリを作成してください。

必須要件:
- モジュール分割（sources/summarizer/formatter/pipeline）
- 失敗時フォールバック（API失敗、Gemini失敗）
- Lambda実行可能なエントリポイント
- デプロイスクリプト（パッケージ作成 + 更新）
- 更新競合回避の wait 処理を入れる
- READMEに環境変数と本番手順を記載

制約:
- APIキーは環境変数のみ
- URL重複除去
- ログで候補件数/送信件数を返す
```

---

## 8. 現在の到達点

- Lambda本番デプロイ可能
- Scheduler連携で定期実行可能
- GitHub管理 + 自動反映の土台を整備済み
- 取得50件 → Gemini Top5選定 → LINE配信の要件達成
- URL付き配信仕様に反映済み

---

## 9. 今後の改善候補

1. ニュースドメインのホワイトリスト導入
- ノイズ記事の除外（特にJapan）

2. スコアリングの明示化
- Gemini選定理由の内部ログ保存

3. 観測性の強化
- CloudWatchメトリクス・失敗通知（Slack/LINE）

4. CI/CDの固定化
- GitHub Actionsの認証を安定運用（OIDCロール最小権限化）

---

## 10. まとめ
このプロジェクトは「ニュース取得」「生成AI要約」「メッセージ配信」「サーバーレス運用」を1本に繋げた実用構成です。

特に重要だったのは、
- 仕様変更に耐えるモジュール分割
- 失敗を前提にしたフォールバック
- プロンプトの構造化
- デプロイ自動化（と待機処理）

この4点でした。
