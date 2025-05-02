# 技術コンテキスト：YouTube データ分析可視化サービス

## 開発環境

- **OS**: Windows 11
- **デフォルトシェル**: C:\WINDOWS\system32\cmd.exe
- **作業ディレクトリ**: c:/project/youtube_highlight_analyzer_frontend

## 主要技術スタック

### フロントエンド

1. **Streamlit**:

   - バージョン: 最新安定版
   - 目的: Web インターフェース構築、データ可視化
   - 主な機能: マルチページアプリ、セッション状態管理、コンポーネント表示

2. **Plotly**:

   - バージョン: 最新安定版
   - 目的: インタラクティブなグラフ表示
   - 主な機能: 時系列グラフ、イベント処理

3. **streamlit_plotly_events**:

   - 目的: Plotly グラフのクリックイベント取得
   - 主な機能: クリック座標情報の取得と処理

4. **HTML/JavaScript**:
   - 目的: YouTube プレイヤーとの連携、カスタム UI コンポーネント
   - 主な機能: iFrame API、postMessage 通信

### バックエンド

1. **Supabase**:

   - URL: https://crzdckxjivovcvtnrmwg.supabase.co
   - API Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyemRja3hqaXZvdmN2dG5ybXdnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzc3NzEsImV4cCI6MjA2MDcxMzc3MX0.mfvta0xzbnTc_PQWlIb9mSvBUr4c7GsNZydV7vgAKsQ
   - 目的: データストレージとクエリ
   - 主な機能: RPC 関数、テーブルクエリ

2. **supabase-py**:

   - バージョン: 最新安定版
   - 目的: Supabase への Python クライアント
   - 主な機能: テーブルクエリ、RPC 呼び出し

3. **PostgreSQL**:
   - バージョン: Supabase が提供するもの
   - 目的: データベース
   - 主な機能: SQL 関数、集計クエリ

### デプロイ

- **Streamlit Cloud**:
  - 目的: アプリケーションのホスティング
  - 主な機能: GitHub との連携、シークレット管理

## データ構造

### 主要テーブル

1. **youtube_channels**: チャンネル情報テーブル

   - 主キー: id (bigint)
   - 主要フィールド: channel_id, title, description

2. **videos**: 動画情報テーブル

   - 主キー: id (bigint)
   - 外部キー: channel_id (youtube_channels.id)
   - 主要フィールド: video_id, title, description, duration, published_at

3. **video_timestamps**: チャプター情報テーブル

   - 主キー: id (bigint)
   - 外部キー: video_id (videos.id)
   - 主要フィールド: time_seconds, timestamp, title, is_auto

4. **chat_messages**: コメント情報テーブル

   - 主キー: id (bigint)
   - 外部キー: video_id (videos.id)
   - 主要フィールド: timestamp, name, message, time_seconds

5. **transcriptions**: 文字起こし情報テーブル

   - 主キー: id (bigint)
   - 外部キー: video_id (videos.id)
   - 主要フィールド: time_seconds, transcription, timestamp

6. **audio_emotion_analysis**: 音声感情分析テーブル

   - 主キー: id (bigint)
   - 外部キー: video_id (videos.id)
   - 主要フィールド: time_seconds, emotion_type, confidence_score, normalized_score

7. **volume_analysis**: 音量分析テーブル

   - 主キー: id (bigint)
   - 外部キー: video_id (videos.id)
   - 主要フィールド: time_seconds, volume_db, normalized_score

8. **volume_analysis_secondly**: 詳細音量分析テーブル
   - 主キー: id (bigint)
   - 外部キー: video_id (videos.id)
   - 主要フィールド: time_seconds, analysis_second, abs_db_mean, is_peak

## RPC 関数

1. **metrics_agg**: メトリクスデータ集計

   - パラメータ: \_vid (動画 ID), \_g (粒度)
   - 戻り値: 時間単位での音量、コメント数などの集計データ

2. **multi_term_comment_hist**: 複数検索語のコメント頻度集計

   - パラメータ: \_vid (動画 ID), \_terms (検索語配列), \_g (粒度)
   - 戻り値: 各検索語ごとの時間単位での出現回数

3. **search_comments_multi**: 複数検索語でのコメント検索
   - パラメータ: \_vid (動画 ID), \_terms (検索語配列), \_match_type (一致条件)
   - 戻り値: マッチしたコメントと検索語情報

## 技術的制約

1. **Streamlit の制約**:

   - 状態管理: ページリロード時に状態が初期化される
   - 対応策: `st.session_state`による状態管理
   - コンポーネント更新: 特定の操作でページ全体が再レンダリングされる
   - 対応策: キャッシュと部分的な HTML/JS コンポーネントの活用

2. **YouTube プレイヤー連携の制約**:

   - クロスドメイン通信: ドメイン間のセキュリティ制限
   - 対応策: postMessage API による安全な通信
   - イベント連携: YouTube プレイヤーからのイベント取得と処理
   - 対応策: IFrame API とイベントリスナーの実装

3. **Supabase の制約**:
   - クエリのパフォーマンス: 大量データ処理時の速度
   - 対応策: RPC 関数での集計処理とクライアント側キャッシュ
   - 同時接続数: 無料プランでの同時接続数制限
   - 対応策: 接続プールの適切な管理

## 開発ツール

1. **バージョン管理**:

   - Git: コード管理
   - GitHub: リポジトリホスティング

2. **エディタ**:

   - Visual Studio Code: 主要開発環境
   - 拡張機能: Python, Streamlit, SQL

3. **テスト**:
   - ローカル環境での Streamlit 開発サーバー
   - Streamlit Cloud 開発環境

## 依存関係

```
streamlit==1.30.0
supabase==2.2.0
plotly==5.18.0
streamlit-plotly-events==0.0.6
pandas==2.1.3
streamlit-javascript==0.1.5
python-dotenv==1.0.0
```

## パフォーマンス考慮事項

1. **データロード最適化**:

   - `@st.cache_data`デコレータによるデータキャッシュ
   - TTL 設定によるキャッシュ更新戦略
   - Supabase 側での集計処理の活用

2. **UI 応答性**:

   - 適切な粒度設定によるデータ量調整
   - ページネーションによる大量データの分割表示
   - バックグラウンドでのデータロード

3. **資源利用効率**:
   - 不要なデータ再取得の回避
   - 必要に応じたデータ粒度の調整
   - キャッシュクリア戦略の最適化
