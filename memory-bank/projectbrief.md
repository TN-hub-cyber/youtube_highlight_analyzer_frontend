# プロジェクト概要：YouTube 動画分析可視化サービス

## プロジェクトの目的

YouTube 動画のデータ（メタデータ、コメント、音声感情分析、文字起こしなど）を分析し、ユーザーに分かりやすく可視化する Web アプリケーションを開発することを目的としています。動画クリエイターやマーケターが動画内のハイライトや視聴者の反応を効率的に把握できるツールを提供します。

## 主要要件

1. **Streamlit による Web インターフェース開発**

   - チャンネル一覧、動画一覧、動画分析画面の 3 つの主要画面構成
   - レスポンシブデザイン対応

2. **Supabase 連携**

   - データベースへのアクセス
   - RPC 関数の開発と利用
   - 認証機能は不要

3. **動画分析機能**

   - YouTube プレイヤーとのインタラクティブな連携
   - 時系列データ（音量、コメント頻度など）の可視化
   - チャプター、コメント、文字起こし、感情分析の表示

4. **デプロイ先**
   - Streamlit Cloud

## 技術スタック

- **フロントエンド**: Streamlit
- **バックエンド**: Supabase (PostgreSQL)
- **データ可視化**: Plotly
- **デプロイ環境**: Streamlit Cloud

## プロジェクト範囲

- YouTube データの初期登録は別環境で行われ、本プロジェクトには含まれない
- Supabase の RPC 開発はフロントエンド開発に含める
- 認証機能は不要

## Supabase 接続情報

```
SUPABASE_URL=https://crzdckxjivovcvtnrmwg.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyemRja3hqaXZvdmN2dG5ybXdnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzc3NzEsImV4cCI6MjA2MDcxMzc3MX0.mfvta0xzbnTc_PQWlIb9mSvBUr4c7GsNZydV7vgAKsQ
```

## 成功基準

1. ユーザーがチャンネル → 動画 → 分析画面と直感的に移動できること
2. 動画プレイヤーとグラフが双方向連携していること（クリック → シーク、再生 → グラフ更新）
3. 複数の分析データ（音量、コメント、感情など）を視覚的に表示できること
4. 設計書とワイヤーフレーム通りの機能と見た目を実現すること
5. Streamlit Cloud でスムーズに動作すること
