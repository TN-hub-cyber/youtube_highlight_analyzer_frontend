# Supabase データベーステーブル定義書

**プロジェクト名:** t.nakagawa.gm@gmail.com's Project  
**プロジェクト ID:** crzdckxjivovcvtnrmwg  
**作成日:** 2025 年 6 月 14 日  
**データベースバージョン:** PostgreSQL 15.8.1.073

---

## 概要

このデータベースは、YouTube 動画の分析システムを構築するためのテーブル構成となっています。動画の音量分析、感情分析、コメント分析、キーワード分析、ハイライト抽出など、包括的な動画分析機能をサポートしています。

---

## テーブル一覧

### 1. youtube_channels

**説明:** YouTube チャンネルの基本情報を管理

| カラム名         | データ型    | NULL | デフォルト値 | 説明                  |
| ---------------- | ----------- | ---- | ------------ | --------------------- |
| id               | bigint      | NO   | (IDENTITY)   | プライマリキー        |
| channel_id       | text        | NO   |              | YouTube チャンネル ID |
| title            | text        | YES  |              | チャンネルタイトル    |
| description      | text        | YES  |              | チャンネル説明        |
| created_at       | timestamptz | YES  | now()        | 作成日時              |
| updated_at       | timestamptz | YES  | now()        | 更新日時              |
| custom_url       | text        | YES  |              | カスタム URL          |
| thumbnail_url    | text        | YES  |              | サムネイル URL        |
| view_count       | bigint      | YES  |              | 総視聴回数            |
| subscriber_count | bigint      | YES  |              | 登録者数              |
| video_count      | bigint      | YES  |              | 動画数                |
| country          | text        | YES  |              | 国コード              |

**主キー:** id  
**関連:** videos.channel_id → youtube_channels.id

---

### 2. videos

**説明:** 動画の基本情報とメタデータを管理

| カラム名           | データ型    | NULL | デフォルト値 | 説明                      |
| ------------------ | ----------- | ---- | ------------ | ------------------------- |
| id                 | bigint      | NO   | (IDENTITY)   | プライマリキー            |
| video_id           | text        | NO   |              | YouTube 動画 ID           |
| channel_id         | bigint      | YES  |              | チャンネル ID（外部キー） |
| title              | text        | YES  |              | 動画タイトル              |
| description        | text        | YES  |              | 動画説明                  |
| duration           | bigint      | YES  |              | 動画長（秒）              |
| published_at       | timestamptz | YES  |              | 公開日時                  |
| downloaded_at      | timestamptz | YES  |              | ダウンロード日時          |
| processed_at       | timestamptz | YES  |              | 処理完了日時              |
| created_at         | timestamptz | YES  | now()        | 作成日時                  |
| updated_at         | timestamptz | YES  | now()        | 更新日時                  |
| comment_count      | bigint      | YES  |              | コメント数                |
| thumbnail_url      | text        | YES  |              | サムネイル URL            |
| tags               | text[]      | YES  |              | タグ配列                  |
| category_id        | text        | YES  |              | カテゴリ ID               |
| actual_start_time  | timestamptz | YES  |              | 実際の開始時間            |
| actual_end_time    | timestamptz | YES  |              | 実際の終了時間            |
| concurrent_viewers | bigint      | YES  |              | 同接視聴者数              |

**主キー:** id  
**外部キー:** channel_id → youtube_channels.id

---

### 3. id_mapping

**説明:** YouTube 動画 ID と内部 ID のマッピング

| カラム名         | データ型    | NULL | デフォルト値   | 説明            |
| ---------------- | ----------- | ---- | -------------- | --------------- |
| youtube_video_id | text        | NO   |                | YouTube 動画 ID |
| internal_id      | bigint      | NO   |                | 内部 ID         |
| source           | text        | YES  | 'videos_table' | ソース情報      |
| created_at       | timestamptz | YES  | now()          | 作成日時        |

**主キー:** youtube_video_id

---

### 4. highlight_candidates

**説明:** ハイライト候補の情報

| カラム名    | データ型    | NULL | デフォルト値 | 説明                |
| ----------- | ----------- | ---- | ------------ | ------------------- |
| id          | bigint      | NO   | (IDENTITY)   | プライマリキー      |
| video_id    | bigint      | NO   |              | 動画 ID（外部キー） |
| start_time  | bigint      | YES  |              | 開始時間（秒）      |
| end_time    | bigint      | YES  |              | 終了時間（秒）      |
| score       | float8      | YES  |              | スコア              |
| title       | text        | YES  |              | タイトル            |
| description | text        | YES  |              | 説明                |
| factors     | text        | YES  |              | 要因                |
| is_auto     | boolean     | YES  |              | 自動検出フラグ      |
| created_at  | timestamptz | YES  | now()        | 作成日時            |
| updated_at  | timestamptz | YES  | now()        | 更新日時            |

**主キー:** id  
**外部キー:** video_id → videos.id

---

### 5. video_timestamps

**説明:** 動画のタイムスタンプ情報

| カラム名     | データ型    | NULL | デフォルト値 | 説明                 |
| ------------ | ----------- | ---- | ------------ | -------------------- |
| id           | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id     | bigint      | NO   |              | 動画 ID（外部キー）  |
| time_seconds | bigint      | YES  |              | 時間（秒）           |
| timestamp    | text        | YES  |              | タイムスタンプ文字列 |
| title        | text        | YES  |              | タイトル             |
| description  | text        | YES  |              | 説明                 |
| is_auto      | boolean     | YES  |              | 自動生成フラグ       |
| created_at   | timestamptz | YES  | now()        | 作成日時             |
| updated_at   | timestamptz | YES  | now()        | 更新日時             |

**主キー:** id  
**外部キー:** video_id → videos.id

---

### 6. analysis_results

**説明:** 分析結果の統合データ

| カラム名      | データ型    | NULL | デフォルト値 | 説明                 |
| ------------- | ----------- | ---- | ------------ | -------------------- |
| id            | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id      | bigint      | NO   |              | 動画 ID（外部キー）  |
| time_seconds  | bigint      | NO   |              | 時間（秒）           |
| timestamp     | text        | NO   |              | タイムスタンプ文字列 |
| volume_db     | float8      | YES  |              | 音量（dB）           |
| comment_count | bigint      | YES  |              | コメント数           |
| stamp_count   | bigint      | YES  |              | スタンプ数           |
| keyword_count | bigint      | YES  |              | キーワード数         |
| created_at    | timestamptz | YES  | now()        | 作成日時             |
| updated_at    | timestamptz | YES  | now()        | 更新日時             |

**主キー:** id  
**外部キー:** video_id → videos.id

---

### 7. volume_analysis

**説明:** 音量分析の詳細データ

| カラム名         | データ型    | NULL | デフォルト値 | 説明                 |
| ---------------- | ----------- | ---- | ------------ | -------------------- |
| id               | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id         | bigint      | NO   |              | 動画 ID（外部キー）  |
| time_seconds     | bigint      | YES  |              | 時間（秒）           |
| timestamp        | text        | YES  |              | タイムスタンプ文字列 |
| volume_db        | float8      | YES  |              | 音量（dB）           |
| normalized_score | float8      | YES  |              | 正規化スコア         |
| created_at       | timestamptz | YES  | now()        | 作成日時             |
| updated_at       | timestamptz | YES  | now()        | 更新日時             |
| relative_change  | float8      | YES  |              | 相対音量             |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 26,306 行のデータ、16MB

---

### 8. volume_analysis_secondly

**説明:** 音量分析の秒単位集計データ

| カラム名              | データ型    | NULL | デフォルト値 | 説明                                 |
| --------------------- | ----------- | ---- | ------------ | ------------------------------------ |
| id                    | bigint      | NO   | (IDENTITY)   | プライマリキー                       |
| video_id              | bigint      | NO   |              | 動画 ID（外部キー）                  |
| time_seconds          | bigint      | NO   |              | 時間（秒）                           |
| timestamp             | text        | NO   |              | タイムスタンプ文字列                 |
| analysis_second       | bigint      | NO   |              | 分析秒                               |
| rel_net_change        | float8      | YES  |              | 相対純変化                           |
| rel_max_positive_diff | float8      | YES  |              | 相対最大正差                         |
| rel_sum_of_abs_diff   | float8      | YES  |              | 相対絶対差合計                       |
| abs_db_mean           | float8      | YES  |              | 絶対 dB 平均値                       |
| abs_db_max            | float8      | YES  |              | 絶対 dB 最大値                       |
| abs_db_min            | float8      | YES  |              | 絶対 dB 最小値                       |
| created_at            | timestamptz | YES  | now()        | 作成日時                             |
| updated_at            | timestamptz | YES  | now()        | 更新日時                             |
| inter_mean_delta      | float4      | YES  |              | 前秒比の平均音量差                   |
| inter_max_delta       | float4      | YES  |              | 前秒比の最大音量差                   |
| inter_min_delta       | float4      | YES  |              | 前秒比の最小音量差                   |
| dynamic_range         | float4      | YES  |              | 同一秒内の音量振れ幅                 |
| norm_mean             | float4      | YES  |              | 0-1 に正規化された平均音量           |
| smooth_mean           | float4      | YES  |              | 3 秒移動平均音量                     |
| is_peak               | int4        | YES  | 0            | 盛り上がりポイント判定 (-3dB 以上=1) |
| is_silent             | int4        | YES  | 0            | 無音区間判定 (-50dB 以下=1)          |
| overall_loud          | float4      | YES  |              | 総合音量レベル                       |
| loud_percentile       | float4      | YES  |              | 音量パーセンタイル                   |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 2,630 行のデータ、2MB

---

### 9. audio_emotion_analysis

**説明:** 音声感情分析データ

| カラム名         | データ型    | NULL | デフォルト値 | 説明                 |
| ---------------- | ----------- | ---- | ------------ | -------------------- |
| id               | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id         | bigint      | NO   |              | 動画 ID（外部キー）  |
| time_seconds     | bigint      | YES  |              | 時間（秒）           |
| timestamp        | text        | YES  |              | タイムスタンプ文字列 |
| emotion_type     | text        | YES  |              | 感情タイプ           |
| confidence_score | float8      | YES  |              | 信頼度スコア         |
| normalized_score | float8      | YES  |              | 正規化スコア         |
| detection_mode   | text        | YES  | 'standard'   | 検出モード           |
| start_time       | float8      | YES  |              | 開始時間             |
| end_time         | float8      | YES  |              | 終了時間             |
| created_at       | timestamptz | YES  | now()        | 作成日時             |
| updated_at       | timestamptz | YES  | now()        | 更新日時             |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 52 行のデータ、192KB

---

### 10. comment_analysis

**説明:** コメント分析データ

| カラム名         | データ型    | NULL | デフォルト値 | 説明                 |
| ---------------- | ----------- | ---- | ------------ | -------------------- |
| id               | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id         | bigint      | NO   |              | 動画 ID（外部キー）  |
| time_seconds     | bigint      | YES  |              | 時間（秒）           |
| timestamp        | text        | YES  |              | タイムスタンプ文字列 |
| comment_count    | bigint      | YES  |              | コメント数           |
| normalized_score | float8      | YES  |              | 正規化スコア         |
| created_at       | timestamptz | YES  | now()        | 作成日時             |
| updated_at       | timestamptz | YES  | now()        | 更新日時             |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 2,607 行のデータ、1.7MB

---

### 11. keyword_analysis

**説明:** キーワード分析データ

| カラム名         | データ型    | NULL | デフォルト値 | 説明                 |
| ---------------- | ----------- | ---- | ------------ | -------------------- |
| id               | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id         | bigint      | NO   |              | 動画 ID（外部キー）  |
| time_seconds     | bigint      | YES  |              | 時間（秒）           |
| timestamp        | text        | YES  |              | タイムスタンプ文字列 |
| keyword          | text        | YES  |              | キーワード           |
| keyword_count    | bigint      | YES  |              | キーワード出現数     |
| normalized_score | float8      | YES  |              | 正規化スコア         |
| created_at       | timestamptz | YES  | now()        | 作成日時             |
| updated_at       | timestamptz | YES  | now()        | 更新日時             |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 2,607 行のデータ、1.8MB

---

### 12. keyword_settings

**説明:** キーワード設定

| カラム名   | データ型    | NULL | デフォルト値 | 説明                |
| ---------- | ----------- | ---- | ------------ | ------------------- |
| id         | bigint      | NO   | (IDENTITY)   | プライマリキー      |
| video_id   | bigint      | NO   |              | 動画 ID（外部キー） |
| keyword    | text        | YES  |              | キーワード          |
| created_at | timestamptz | YES  | now()        | 作成日時            |
| updated_at | timestamptz | YES  | now()        | 更新日時            |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 10 行のデータ、80KB

---

### 13. stamp_analysis

**説明:** スタンプ分析データ

| カラム名         | データ型    | NULL | デフォルト値 | 説明                 |
| ---------------- | ----------- | ---- | ------------ | -------------------- |
| id               | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id         | bigint      | NO   |              | 動画 ID（外部キー）  |
| time_seconds     | bigint      | YES  |              | 時間（秒）           |
| timestamp        | text        | YES  |              | タイムスタンプ文字列 |
| stamp_code       | text        | YES  |              | スタンプコード       |
| stamp_count      | bigint      | YES  |              | スタンプ数           |
| normalized_score | float8      | YES  |              | 正規化スコア         |
| created_at       | timestamptz | YES  | now()        | 作成日時             |
| updated_at       | timestamptz | YES  | now()        | 更新日時             |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 2,607 行のデータ、1.9MB

---

### 14. stamp_settings

**説明:** スタンプ設定

| カラム名   | データ型    | NULL | デフォルト値 | 説明                |
| ---------- | ----------- | ---- | ------------ | ------------------- |
| id         | bigint      | NO   | (IDENTITY)   | プライマリキー      |
| video_id   | bigint      | NO   |              | 動画 ID（外部キー） |
| stamp_code | text        | YES  |              | スタンプコード      |
| created_at | timestamptz | YES  | now()        | 作成日時            |
| updated_at | timestamptz | YES  | now()        | 更新日時            |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 9 行のデータ、80KB

---

### 15. chat_messages

**説明:** チャットメッセージ

| カラム名     | データ型    | NULL | デフォルト値 | 説明                 |
| ------------ | ----------- | ---- | ------------ | -------------------- |
| id           | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id     | bigint      | NO   |              | 動画 ID（外部キー）  |
| timestamp    | text        | YES  |              | タイムスタンプ文字列 |
| name         | text        | YES  |              | ユーザー名           |
| message      | text        | YES  |              | メッセージ内容       |
| message_type | text        | YES  |              | メッセージタイプ     |
| time_seconds | bigint      | YES  |              | 時間（秒）           |
| created_at   | timestamptz | YES  | now()        | 作成日時             |
| updated_at   | timestamptz | YES  | now()        | 更新日時             |
| stamps       | jsonb       | YES  |              | スタンプ種類：数     |
| emotion      | text        | YES  |              | 感情                 |
| strength     | numeric     | YES  |              | 強度                 |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 506 行のデータ、2.6MB

---

### 16. transcriptions

**説明:** 音声書き起こしデータ

| カラム名          | データ型    | NULL | デフォルト値 | 説明                 |
| ----------------- | ----------- | ---- | ------------ | -------------------- |
| id                | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id          | bigint      | NO   |              | 動画 ID（外部キー）  |
| time_seconds      | bigint      | NO   |              | 時間（秒）           |
| transcription     | text        | NO   |              | 書き起こしテキスト   |
| refined_text      | text        | YES  |              | 精製されたテキスト   |
| created_at        | timestamptz | YES  | now()        | 作成日時             |
| updated_at        | timestamptz | YES  | now()        | 更新日時             |
| timestamp         | text        | YES  |              | タイムスタンプ文字列 |
| summary           | text        | YES  |              | 要約                 |
| topics            | jsonb[]     | YES  |              | トピック配列         |
| emotions          | jsonb[]     | YES  |              | 感情配列             |
| events            | jsonb[]     | YES  |              | イベント配列         |
| analysis_raw_json | jsonb       | YES  |              | 分析生 JSON データ   |
| rarity            | float4      | YES  |              | 希少性               |
| impact            | float4      | YES  |              | インパクト           |
| emotion           | float4      | YES  |              | 感情                 |
| overall           | float4      | YES  |              | 総合評価             |
| percentile        | float4      | YES  |              | パーセンタイル       |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 42 行のデータ、720KB

---

### 17. analysis_jobs

**説明:** 分析ジョブ管理

| カラム名         | データ型    | NULL | デフォルト値 | 説明                 |
| ---------------- | ----------- | ---- | ------------ | -------------------- |
| id               | bigint      | NO   | (IDENTITY)   | プライマリキー       |
| video_id         | bigint      | NO   |              | 動画 ID（外部キー）  |
| job_type         | text        | YES  |              | ジョブタイプ         |
| status           | text        | YES  |              | ステータス           |
| started_at       | timestamptz | YES  |              | 開始日時             |
| completed_at     | timestamptz | YES  |              | 完了日時             |
| error_message    | text        | YES  |              | エラーメッセージ     |
| parameters       | text        | YES  |              | パラメータ           |
| created_at       | timestamptz | YES  | now()        | 作成日時             |
| updated_at       | timestamptz | YES  | now()        | 更新日時             |
| highlight_status | varchar     | YES  |              | ハイライトステータス |

**主キー:** id  
**外部キー:** video_id → videos.id  
**備考:** 1 行のデータ、80KB

---

### 18. channel_stamp_word_settings

**説明:** YouTube 配信者ごとのスタンプと頻出ワード管理テーブル

| カラム名       | データ型  | NULL | デフォルト値      | 説明                                                                 |
| -------------- | --------- | ---- | ----------------- | -------------------------------------------------------------------- |
| id             | int4      | NO   | nextval(...)      | プライマリキー                                                       |
| channel_id     | text      | NO   |                   | YouTube チャンネル ID（youtube_channels.channel_id と関連）          |
| target_content | text      | NO   |                   | スタンプ名（:\_name:形式）またはワード文字列                         |
| content_type   | varchar   | NO   |                   | コンテンツタイプ：stamp（スタンプ）または word（ワード）             |
| priority       | int4      | NO   | 1                 | 優先度（数値が大きいほど優先、同じ優先度の場合は created_at で判定） |
| emotion        | varchar   | YES  |                   | 感情カテゴリ（例：happy, sad, excited, funny 等）                    |
| created_at     | timestamp | YES  | CURRENT_TIMESTAMP | 作成日時                                                             |
| updated_at     | timestamp | YES  | CURRENT_TIMESTAMP | 更新日時                                                             |
| coefficient    | float4    | YES  |                   | 単語当たりの強度係数                                                 |

**主キー:** id  
**制約:** content_type IN ('stamp', 'word')  
**備考:** 30 行のデータ、112KB

---

### 19. chat_metrics_secondly

**説明:** チャット指標（秒単位）

| カラム名             | データ型    | NULL | デフォルト値 | 説明                     |
| -------------------- | ----------- | ---- | ------------ | ------------------------ |
| video_id             | bigint      | NO   |              | 動画 ID                  |
| time_seconds         | bigint      | NO   |              | 時間（秒）               |
| msgs_per_sec         | int4        | YES  |              | 秒間メッセージ数         |
| uniq_users_sec       | int4        | YES  |              | 秒間ユニークユーザー数   |
| sum_strength_sec     | float4      | YES  |              | 秒間強度合計             |
| dominant_emotion     | varchar     | YES  |              | 支配的感情               |
| emotion_strength_sec | float4      | YES  |              | 秒間感情強度             |
| norm_density         | float4      | YES  |              | 正規化密度               |
| norm_strength        | float4      | YES  |              | 正規化強度               |
| norm_users           | float4      | YES  |              | 正規化ユーザー数         |
| overall_chat1        | float4      | YES  |              | 総合チャット評価 1       |
| chat_percentile1     | float4      | YES  |              | チャットパーセンタイル 1 |
| created_at           | timestamptz | YES  | now()        | 作成日時                 |
| updated_at           | timestamptz | YES  | now()        | 更新日時                 |

**主キー:** (video_id, time_seconds)  
**備考:** 446 行のデータ、144KB

---

### 20. audio_emotion_audio_metrics_secondly

**説明:** 音声感情指標（秒単位）

| カラム名             | データ型    | NULL | デフォルト値 | 説明               |
| -------------------- | ----------- | ---- | ------------ | ------------------ |
| video_id             | bigint      | NO   |              | 動画 ID            |
| time_seconds         | bigint      | NO   |              | 時間（秒）         |
| max_norm             | float4      | YES  |              | 最大正規化値       |
| max_conf             | float4      | YES  |              | 最大信頼度         |
| dominant_emotion     | varchar     | YES  |              | 支配的感情         |
| emotion_strength_sec | float4      | YES  |              | 秒間感情強度       |
| overall_emotion      | float4      | YES  |              | 総合感情評価       |
| emotion_percentile   | float4      | YES  |              | 感情パーセンタイル |
| created_at           | timestamptz | YES  | now()        | 作成日時           |
| updated_at           | timestamptz | YES  | now()        | 更新日時           |

**主キー:** (video_id, time_seconds)  
**備考:** 52 行のデータ、40KB

---

### 21. highlight_segments

**説明:** ハイライトセグメント

| カラム名        | データ型    | NULL | デフォルト値 | 説明                                |
| --------------- | ----------- | ---- | ------------ | ----------------------------------- |
| id              | bigint      | NO   | nextval(...) | プライマリキー                      |
| video_id        | bigint      | NO   |              | 動画 ID                             |
| youtube_id      | varchar     | NO   |              | YouTube 動画 ID                     |
| start_second    | bigint      | NO   |              | 開始秒                              |
| end_second      | bigint      | NO   |              | 終了秒                              |
| peak_second     | bigint      | NO   |              | ピーク秒                            |
| peak_score      | float4      | NO   |              | ピークスコア                        |
| reason_flags    | jsonb       | NO   |              | 理由フラグ                          |
| created_at      | timestamptz | YES  | now()        | 作成日時                            |
| updated_at      | timestamptz | YES  | now()        | 更新日時                            |
| timestamp_start | text        | YES  | (computed)   | 開始タイムスタンプ（HH:MM:SS 形式） |
| timestamp_end   | text        | YES  | (computed)   | 終了タイムスタンプ（HH:MM:SS 形式） |

**主キー:** id  
**備考:** 15 行のデータ、48KB  
**計算カラム:** timestamp_start, timestamp_end は start_second, end_second から自動生成

---

## データベース統計

- **総テーブル数:** 21
- **総データサイズ:** 約 27MB
- **最大テーブル:** volume_analysis (16MB, 26,306 行)
- **リレーション数:** 15 の外部キー関係

## 主要なリレーション

1. **youtube_channels** → **videos** (1:N)
2. **videos** → **各分析テーブル** (1:N)
   - highlight_candidates
   - video_timestamps
   - analysis_results
   - volume_analysis
   - volume_analysis_secondly
   - audio_emotion_analysis
   - comment_analysis
   - keyword_analysis
   - keyword_settings
   - stamp_analysis
   - stamp_settings
   - chat_messages
   - transcriptions
   - analysis_jobs

## 注意事項

- RLS（Row Level Security）は全テーブルで無効化されています
- 大部分のテーブルで`created_at`、`updated_at`カラムがデフォルト値`now()`で設定されています
- 音量分析系テーブルは大容量のため、パフォーマンスを考慮したクエリが必要です
- JSONB カラムを含むテーブルでは、適切なインデックス設計が推奨されます
