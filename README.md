# YouTube 動画ハイライト分析ツール

YouTube チャンネルや動画のデータを可視化し、分析するための Web アプリケーションです。チャンネル一覧から動画を選択し、コメント傾向、感情分析、ハイライトセグメントなどの詳細なデータを閲覧できます。

## 機能

- **チャンネル一覧表示**: 登録された YouTube チャンネルの一覧を表示
- **動画一覧**: チャンネルごとの動画一覧を表示（公開日、再生回数などでソート可能）
- **動画分析**:
  - YouTube 動画プレイヤー（再生位置連動）
  - メトリクスグラフ（時系列データの可視化）
  - チャプター情報の表示
  - コメント検索と分析（複数キーワード対応）
  - 文字起こしデータの表示と検索
  - 音声の感情分析データの可視化
  - 自動検出されたハイライトセグメントの表示

## 技術スタック

- **フロントエンド**: Streamlit
- **バックエンド**: Supabase (PostgreSQL)
- **データ処理**: Python, Pandas
- **可視化**: Plotly
- **その他**: streamlit-plotly-events, streamlit-javascript

## セットアップ

### 前提条件

- Python 3.8 以上
- Supabase アカウントとプロジェクト

### インストール手順

1. リポジトリをクローン

```bash
git clone <repository-url>
cd youtube_highlight_analyzer_frontend
```

2. 仮想環境の作成（オプション）

```bash
python -m venv venv
# Windowsの場合
venv\Scripts\activate
# macOS/Linuxの場合
source venv/bin/activate
```

3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

4. 環境設定

`.env`ファイルをプロジェクトのルートディレクトリに作成し、以下の内容を設定：

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

または、Streamlit Cloud にデプロイする場合は、Streamlit のシークレット設定で以下を設定：

```toml
[supabase]
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_key"
```

### 実行方法

```bash
streamlit run Home.py
```

## 使い方

1. **チャンネル選択**: ホーム画面で YouTube チャンネルを選択
2. **動画選択**: チャンネルの動画一覧から分析したい動画を選択
3. **分析機能**:
   - メトリクスグラフをクリックして特定の時間にジャンプ
   - チャプターリストから特定の部分に移動
   - キーワード検索でコメントを分析
   - 文字起こしデータで会話内容を確認
   - 感情分析データでハイライトシーンを確認
   - 自動検出されたハイライトセグメントを閲覧

## ディレクトリ構造

```
youtube_highlight_analyzer_frontend/
├── .streamlit/              # Streamlit設定ファイル
├── components/              # 再利用可能なUIコンポーネント
│   ├── metrics_graph.py     # メトリクスグラフコンポーネント
│   └── youtube_player.py    # YouTubeプレイヤーコンポーネント
├── pages/                   # アプリケーションのページ
│   ├── 01_Videos.py         # 動画一覧ページ
│   └── 02_Analysis.py       # 動画分析ページ
├── utils/                   # ユーティリティ関数
│   ├── data_utils.py        # データ処理ユーティリティ
│   ├── formatting.py        # フォーマット関連ユーティリティ
│   └── supabase_client.py   # Supabase接続クライアント
├── Home.py                  # メインアプリケーション（チャンネル一覧）
├── requirements.txt         # 依存パッケージリスト
└── README.md                # このファイル
```

## データベース構造

このアプリケーションは以下の Supabase テーブルを使用しています：

- `youtube_channels`: YouTube チャンネル情報
- `videos`: 動画メタデータ
- `chat_messages`: 動画のコメントデータ
- `video_timestamps`: チャプターマーカー情報
- `transcriptions`: 文字起こしデータ
- `audio_emotion_analysis`: 音声の感情分析データ
- `volume_analysis`: 音量分析データ
- `volume_analysis_secondly`: 詳細な音量分析データ
- `highlight_segments`: 自動検出されたハイライトセグメント

## 貢献方法

1. このリポジトリをフォークする
2. 新しいブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成する

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。
