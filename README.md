# AI Trend Dashboard (Streamlit + Dify)

Streamlit 単一サービスで「AI 最新技術 / AI 副業 / Qiita 人気」を Dify Workflow から取得・日次キャッシュして 3 ペイン表示します。FastAPI/React は使いません。

## 必要ソフト
- Docker / Docker Compose

## 環境変数 (.env)
`.env.example` をコピーして `.env` を作成します。

```
# Dify
DIFY_API_BASE=https://api.dify.ai
DIFY_WORKFLOW_API_KEY=wf_xxx
DIFY_WORKFLOW_ID=

# App
CACHE_DIR=/data/cache
PORT=8501
TZ=Asia/Tokyo
```

> キーは Streamlit サーバー側のみで使用。ブラウザに露出しません。

## 起動

```
docker compose up -d --build
```

- アプリ: http://localhost:8501

初回アクセス時に Dify を呼び出し、`./data/cache/daily-YYYY-MM-DD.json` へ保存。同日内はキャッシュを返し、サイドバーの「更新 (Force)」で再取得します。

## 画面要件
- 左上: AI 最新技術（5件）
- 左下: AI 副業（5件）
- 右: Qiita 人気（10件）
- タイトルクリックで新規タブ、最終更新表示、Force 更新ボタンあり

## Dify Workflow 作成（Publish 必須）
名前: `daily_ai_trend_aggregator`

- ノード例:
  1. Tool: Tavily Search ×2（"AI 最新技術"／"AI 副業"、24h以内、各20件、去重）
  2. （任意）Tool: Google Search フォールバック
  3. LLM: 整形サマライザ（tech/side 各5件の JSON）
  4. Tool: Qiita（7日以内の人気上位10件）
  5. LLM: Qiita 整形（同様に JSON）
  6. 出力ノード（厳密 JSON）:

```json
{
  "tech": [{"title":"","url":"","gist":"","source":""}],
  "side": [{"title":"","url":"","gist":"","source":""}],
  "qiita": [{"title":"","url":"","gist":"","source":""}]
}
```

- サマライザ プロンプト例:
```
重複/広告/薄い情報を除外し、今日性（24h）・信頼性・実務有用性で上位5件を JSON で返す。
```

> Publish 後の Workflow API Key を `.env` の `DIFY_WORKFLOW_API_KEY` に設定してください。Dify のレスポンスは `data` または `outputs` 配下に入る可能性があるため、どちらにも対応しています。

## Dify 疎通確認（curl）

```
export DIFY_API_BASE=https://api.dify.ai
export DIFY_WORKFLOW_API_KEY=wf_xxx

curl -s -X POST "$DIFY_API_BASE/v1/workflows/run" \
  -H "Authorization: Bearer $DIFY_WORKFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "inputs": {},
        "response_mode": "blocking",
        "user": "demo"
      }'
```

期待レスポンス例:
```
{
  "data": {
    "tech": [ {"title":"...","url":"...","gist":"...","source":"..."} ],
    "side": [ ... ],
    "qiita": [ ... ]
  }
}
```

## トラブルシュート
- 400: Workflow not published → Dify 側で Publish 済みか、Workflow 用 API Key かを確認
- 401: invalid key → `.env` のキー誤り/権限不足を確認
- 502/504: タイムアウト → 再試行、もしくは Dify 側で処理軽量化
- 画面が空 → コンソールログと `data/cache` の JSON 生成状況を確認

## 既知の制約
- ランキングの厳密性は Dify（Tavily/Qiita）レスポンスに依存
- 同日キャッシュはファイルベース（DB なし）
