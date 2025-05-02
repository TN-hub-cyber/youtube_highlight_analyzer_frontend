# YouTube データ分析可視化サービス - UI/UX実装ガイド (最新版)

このドキュメントは、YouTubeデータ分析可視化サービスのUI/UX実装のための包括的なガイドです。画面設計、ユーザーフロー、コンポーネント仕様を詳細に解説しています。

## 目次
1. [アプリケーション全体構成](#アプリケーション全体構成)
2. [ホーム画面 (Home.py)](#ホーム画面-homepy)
3. [動画一覧画面 (01_Videos.py)](#動画一覧画面-01_videospy)
4. [動画分析画面 (02_Analysis.py)](#動画分析画面-02_analysispy)
5. [タブコンテンツ詳細](#タブコンテンツ詳細)
   - [チャプタータブ](#チャプタータブ)
   - [コメントタブ](#コメントタブ)
   - [文字起こしタブ](#文字起こしタブ)
   - [感情分析タブ](#感情分析タブ)
6. [技術的実装のポイント](#技術的実装のポイント)
7. [レスポンシブデザイン対応](#レスポンシブデザイン対応)

---

## アプリケーション全体構成

### 画面遷移フロー
```
ホーム画面（チャンネル一覧）→ 動画一覧画面 → 動画分析画面
```

### 状態管理キー
- `cid`: Channel ID - チャンネル識別子
- `vid`: Video ID - 動画識別子
- `granularity`: データの粒度（秒単位）- 1, 5, 10, 30, 60
- `search_terms`: 検索語句の配列（複数コメント検索用）
- `sec`: 現在の再生位置（秒）
- `active_tab`: 現在選択中のタブ（0-3）

### データフロー概要
1. ユーザーアクション（クリック、選択変更など）がトリガー
2. `st.session_state`に状態を保存
3. 必要に応じてSupabase RPC（Edge Function）を呼び出し
4. 結果をStreamlit UI要素に反映

---

## ホーム画面 (Home.py)

### 設計: チャンネル一覧表示
- **目的**: ユーザーが分析したいチャンネルを直感的に選択できる
- **操作フロー**: チャンネルカードをクリック → 動画一覧画面に直接遷移

### 主要コンポーネント
1. **ヘッダー**: アプリケーションタイトルと簡単な説明
2. **検索バー**: チャンネル名によるフィルタリング
   ```python
   search_term = st.text_input("チャンネル名で検索", key="channel_search")
   if search_term:
       channels = [c for c in channels if search_term.lower() in c['title'].lower()]
   ```

3. **チャンネル一覧**: クリック可能なカード形式
   ```python
   for channel in channels:
       with st.container():
           col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
           with col1:
               st.write(f"### {channel['title']}")
               st.write(f"@{channel['username']}")
           # 他の列にデータ表示
           
           # クリック処理
           if st.button(f"選択", key=f"btn_{channel['id']}"):
               st.session_state['cid'] = channel['id']
               st.switch_page("pages/01_Videos.py")
   ```

### データ要件
- **APIエンドポイント**: `youtube_channels` テーブル
- **取得データ**: チャンネルID、タイトル、ユーザー名、統計情報
- **キャッシュ戦略**: `@st.cache_data(ttl=600)`で10分間キャッシュ

---

## 動画一覧画面 (01_Videos.py)

### 設計ポイント
- **目的**: 選択したチャンネルの動画一覧表示と分析対象の選択
- **操作フロー**: 動画を選択（ラジオボタン）→ 「分析画面へ」ボタンクリック

### 主要コンポーネント
1. **チャンネルヘッダー**: 選択中チャンネルの情報表示
   ```python
   # チャンネル情報取得
   channel = supabase.table('youtube_channels').select('*').eq('id', st.session_state['cid']).single().execute()
   st.header(channel['title'])
   st.subheader(f"@{channel['username']}")
   
   # 統計情報
   col1, col2, col3 = st.columns(3)
   with col1:
       st.metric("登録者数", f"{channel['subscriber_count']:,}")
   # 他の列にメトリクス表示
   ```

2. **動画リスト**: ラジオボタンによる選択
   ```python
   # 動画一覧取得
   videos = supabase.table('videos').select('*').eq('channel_id', st.session_state['cid']).order('published_at', desc=True).execute()
   
   # ラジオボタンで表示
   selected_video = st.radio(
       "分析する動画を選択",
       videos['data'],
       format_func=lambda x: f"{x['title']} ({x['published_at']})"
   )
   
   # 選択状態の保存
   if selected_video:
       st.session_state['vid'] = selected_video['id']
   ```

3. **ページネーション**: 大量の動画を複数ページに分割
   ```python
   # 簡易ページネーション
   page = st.session_state.get('page', 1)
   page_size = 10
   total_pages = (len(videos['data']) + page_size - 1) // page_size
   
   col1, col2, col3 = st.columns([1, 3, 1])
   with col1:
       if st.button("前へ") and page > 1:
           st.session_state['page'] = page - 1
           st.rerun()
   
   with col2:
       st.write(f"ページ {page}/{total_pages}")
   
   with col3:
       if st.button("次へ") and page < total_pages:
           st.session_state['page'] = page + 1
           st.rerun()
   ```

4. **分析ボタン**: 画面遷移トリガー
   ```python
   if st.button("分析画面へ", use_container_width=True):
       if 'vid' in st.session_state:
           st.switch_page("pages/02_Analysis.py")
       else:
           st.error("動画を選択してください")
   ```

### データ要件
- **APIエンドポイント**: `videos` テーブル
- **取得データ**: 動画ID、タイトル、サムネイル、公開日、再生回数、コメント数
- **フィルター条件**: channel_id = st.session_state['cid']

---

## 動画分析画面 (02_Analysis.py)

### 設計ポイント
- **目的**: YouTubeプレイヤーと分析UIの統合表示
- **操作体験**: 時系列グラフとビデオの双方向連携（クリック→シーク、再生→グラフ更新）
- **一貫したレイアウト**: どのタブでもコントロールパネルとメトリクスグラフは同じ構成

### 主要コンポーネント
1. **YouTubeプレイヤー**: IFrame埋め込みとJSブリッジ
   ```python
   # YouTubeプレイヤーIFrame生成
   video_id = "..." # API から取得
   iframe_code = f"""
   <div id="player-container">
       <iframe id="ytplayer" src="https://www.youtube.com/embed/{video_id}?enablejsapi=1" frameborder="0"></iframe>
   </div>
   <script>
       // YouTube IFrame API
       var tag = document.createElement('script');
       tag.src = "https://www.youtube.com/iframe_api";
       var firstScriptTag = document.getElementsByTagName('script')[0];
       firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
       
       var player;
       function onYouTubeIframeAPIReady() {{
           player = new YT.Player('ytplayer', {{
               events: {{
                   'onReady': onPlayerReady
               }}
           }});
       }}
       
       function onPlayerReady(event) {{
           // メッセージ監視とtickの送信設定
           window.addEventListener('message', e => {{
               if(e.data.type === 'seek'){{ 
                   player.seekTo(e.data.sec, true); 
               }}
           }});
           
           // 定期的に現在時刻を親に通知
           setInterval(() => {{
               parent.postMessage({{
                   type: 'tick',
                   sec: player.getCurrentTime()
               }}, '*');
           }}, 500);
       }}
   </script>
   """
   
   st.components.v1.html(iframe_code, height=350)
   ```

2. **コントロールパネル**: 一貫したレイアウトで全タブ共通
   ```python
   with st.sidebar:
       st.subheader("コントロールパネル")
       
       # 粒度設定
       granularity = st.selectbox(
           "データ粒度",
           [1, 5, 10, 30, 60],
           format_func=lambda x: f"{x}秒",
           index=2  # デフォルト10秒
       )
       if st.session_state.get('granularity') != granularity:
           st.session_state['granularity'] = granularity
           st.cache_data.clear()
       
       st.markdown("---")
       
       # コメント検索 (常に表示)
       st.subheader("コメント検索")
       
       # 検索ワード入力
       search_input = st.text_input(
           "検索ワード（複数指定する場合はカンマ区切り）",
           value=",".join(st.session_state.get('search_terms', [])),
           key="search_input"
       )
       
       # 検索タグ表示
       if 'search_terms' in st.session_state and st.session_state['search_terms']:
           term_colors = get_term_colors(st.session_state['search_terms'])
           
           for i, term in enumerate(st.session_state['search_terms']):
               col1, col2 = st.columns([4, 1])
               with col1:
                   color = term_colors[term]
                   st.markdown(
                       f"<span style='background-color:{color};color:white;padding:3px 8px;border-radius:12px;'>{term}</span>",
                       unsafe_allow_html=True
                   )
               with col2:
                   if st.button("×", key=f"remove_{i}"):
                       st.session_state['search_terms'].pop(i)
                       st.cache_data.clear()
                       st.rerun()
       
       # 検索ボタン
       if st.button("検索", key="search_button"):
           terms = [term.strip() for term in search_input.split(",") if term.strip()]
           terms = list(dict.fromkeys(terms))[:5]  # 重複除去、最大5個
           st.session_state['search_terms'] = terms
           st.cache_data.clear()
           st.rerun()
       
       st.markdown("---")
       
       # 現在位置表示
       if 'sec' in st.session_state:
           st.write(f"**現在位置**: {format_time(st.session_state['sec'])}")
       
       # 詳細設定ボタン
       if st.button("詳細設定", key="settings_button"):
           st.session_state['show_settings'] = not st.session_state.get('show_settings', False)
   
   # 詳細設定パネル（トグル表示）
   if st.session_state.get('show_settings', False):
       with st.expander("詳細設定", expanded=True):
           # 表示設定オプション
           st.selectbox("表示期間", ["全期間", "1分間", "5分間", "10分間", "カスタム"])
           st.multiselect("表示メトリクス", ["音量", "コメント頻度"], default=["音量", "コメント頻度"])
   ```

3. **メトリクスグラフ**: 音量と検索コメント頻度を表示（全タブ共通）
   ```python
   def display_metrics_graph():
       """メトリクスグラフ（音量とコメント頻度）を表示する関数"""
       
       # 音量データ取得
       @st.cache_data(ttl=30)
       def get_metrics(vid, g):
           result = supabase.rpc(
               'metrics_agg', 
               {'_vid': vid, '_g': g}
           ).execute()
           return result['data']
       
       # 複数検索ワードのコメント頻度データ取得
       @st.cache_data(ttl=30)
       def get_multi_term_hist(vid, terms, g):
           if not terms or len(terms) == 0:
               return None
           
           result = supabase.rpc(
               'multi_term_comment_hist', 
               {'_vid': vid, '_terms': terms, '_g': g}
           ).execute()
           
           # 各ワードごとにデータを整理
           term_data = {}
           for row in result['data']:
               term = row['term']
               if term not in term_data:
                   term_data[term] = []
               
               term_data[term].append({
                   'sec': row['sec'],
                   'hits': row['hits']
               })
           
           return term_data
       
       # データ取得
       metrics = get_metrics(st.session_state['vid'], st.session_state['granularity'])
       
       # 検索ワードのヒストグラムデータ取得
       terms = st.session_state.get('search_terms', [])
       term_hist = None
       if terms:
           term_hist = get_multi_term_hist(st.session_state['vid'], terms, st.session_state['granularity'])
       
       # 検索ワードの色定義
       term_colors = get_term_colors(terms)
       
       # Plotlyグラフ作成
       import plotly.graph_objects as go
       from streamlit_plotly_events import plotly_events
       
       fig = go.Figure()
       
       # 音量グラフ
       fig.add_trace(go.Scatter(
           x=[m['sec'] for m in metrics],
           y=[m['volume'] for m in metrics],
           name="音量",
           line=dict(color='#f44336', width=2)  # 赤色
       ))
       
       # コメント検索ヒストグラム (検索ワードがある場合のみ)
       if term_hist:
           # 右側のY軸を追加
           fig.update_layout(
               yaxis2=dict(
                   title="コメント出現回数",
                   titlefont=dict(color='#673AB7'),
                   tickfont=dict(color='#673AB7'),
                   overlaying='y',
                   side='right'
               )
           )
           
           # 各検索ワードごとにバーチャートを追加
           for term, data in term_hist.items():
               color = term_colors.get(term, '#673AB7')
               
               fig.add_trace(go.Bar(
                   x=[d['sec'] for d in data],
                   y=[d['hits'] for d in data],
                   name=f"「{term}」",
                   marker_color=color,
                   opacity=0.6,
                   yaxis='y2',
                   width=st.session_state['granularity'] * 0.5  # バーの幅を調整
               ))
       
       # 現在位置マーカー
       if 'sec' in st.session_state:
           fig.add_vline(
               x=st.session_state['sec'], 
               line_dash="dash", 
               line_color="gray"
           )
       
       # レイアウト設定
       fig.update_layout(
           height=200,
           margin=dict(l=0, r=10, t=10, b=0),
           legend=dict(orientation="h", y=1.1),
           hovermode="x unified",
           yaxis_title="音量",
           xaxis_title="時間（秒）",
           barmode='group'  # バーを重ねず並べて表示
       )
       
       # グラフ表示
       st.markdown("**メトリクスグラフ** (クリックでシーク)")
       
       # クリックイベント処理用
       selected_points = plotly_events(fig, click_event=True, hover_event=False)
       if selected_points:
           point = selected_points[0]
           st.session_state['sec'] = point['x']
   
   # メトリクスグラフ表示（すべてのタブで共通）
   display_metrics_graph()
   ```

4. **タブコンテンツ**: チャプター/コメント/文字起こし/感情分析表示
   ```python
   tab1, tab2, tab3, tab4 = st.tabs(["チャプター", "コメント", "文字起こし", "感情分析"])
   
   with tab1:
       display_chapters_tab()
   
   with tab2:
       display_comments_tab()
       
   with tab3:
       display_transcription_tab()
       
   with tab4:
       display_emotion_tab()
   ```

### データ要件
- **APIエンドポイント**: 
  - RPC `metrics_agg`: 音量データ取得
  - RPC `multi_term_comment_hist`: 複数検索ワードのヒストグラム取得
  - テーブル: `video_timestamps`, `chat_messages`, `transcriptions`, `audio_emotion_analysis`

---

## タブコンテンツ詳細

### チャプタータブ

**主要コンポーネント**:
- **チャプターリスト**: 時間、タイトル、長さ、コメント数などの情報を表示
- **再生ボタン**: クリックで対応する時間にジャンプ
- **現在位置ハイライト**: 現在視聴中のチャプターを背景色で強調

**実装例**:
```python
def display_chapters_tab():
    """チャプタータブの内容を表示する関数"""
    
    # チャプターデータ取得
    @st.cache_data(ttl=60)
    def get_chapters(vid):
        result = supabase.table('video_timestamps').select('*').eq('video_id', vid).order('time_seconds').execute()
        return result['data']
    
    chapters = get_chapters(st.session_state['vid'])
    
    if not chapters:
        st.info("この動画にはチャプターデータがありません。")
        return
    
    # ヘッダー行
    col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 1, 1])
    with col1:
        st.write("**時間**")
    with col2:
        st.write("**チャプタータイトル**")
    with col3:
        st.write("**長さ**")
    with col4:
        st.write("**コメント数**")
    with col5:
        st.write("**操作**")
    
    # チャプターリスト
    current_sec = st.session_state.get('sec', 0)
    
    for i, chapter in enumerate(chapters):
        # 次のチャプターの開始時間（または動画終了時間）を計算
        next_start = chapters[i+1]['time_seconds'] if i < len(chapters)-1 else None
        duration = (next_start - chapter['time_seconds']) if next_start else None
        
        # 現在のチャプター内にいるかをチェック
        is_current = (current_sec >= chapter['time_seconds'] and 
                     (next_start is None or current_sec < next_start))
        
        # 行のスタイル（現在のチャプターはハイライト）
        row_style = "background-color: rgba(33, 150, 243, 0.1);" if is_current else ""
        
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 1, 1])
            
            with col1:
                st.write(format_time(chapter['time_seconds']))
            
            with col2:
                st.write(chapter['title'])
            
            with col3:
                st.write(format_duration(duration) if duration else "")
            
            with col4:
                # チャプター内のコメント数を取得
                comment_count = get_chapter_comment_count(st.session_state['vid'], 
                                                         chapter['time_seconds'], 
                                                         next_start)
                st.write(str(comment_count))
            
            with col5:
                if st.button("再生", key=f"play_{chapter['time_seconds']}"):
                    st.session_state['sec'] = chapter['time_seconds']
```

### コメントタブ

**主要コンポーネント**:
- **コメントフィルター**: 表示件数、並び替え、検索語一致条件の設定
- **コメントリスト**: 時間、ユーザー、コメント内容、検索一致、いいね数を表示
- **検索ワードのハイライト**: コメント内の検索ワードを色別にハイライト
- **ページネーション**: 大量のコメントを複数ページに分割

**実装例**:
```python
def display_comments_tab():
    """コメントタブの内容を表示する関数"""
    
    # 検索ワードの取得
    terms = st.session_state.get('search_terms', [])
    term_colors = get_term_colors(terms)
    
    # フィルター・ソートコントロール
    col1, col2, col3, col4 = st.columns([1, 1.5, 1.5, 1])
    
    with col1:
        display_count = st.selectbox(
            "表示件数",
            [10, 20, 50, 100],
            index=1,
            key="comment_display_count"
        )
    
    with col2:
        sort_by = st.selectbox(
            "並び替え",
            ["時間（昇順）", "時間（降順）", "いいね数", "一致数"],
            key="comment_sort_by"
        )
    
    with col3:
        # 検索ワードが複数ある場合のみ表示
        if len(terms) > 1:
            match_type = st.selectbox(
                "検索語一致",
                ["いずれか一致", "すべて一致"],
                key="match_type"
            )
        else:
            match_type = "いずれか一致"
    
    with col4:
        if st.button("絞り込み", key="comment_filter_button"):
            st.session_state['comment_filter_applied'] = True
    
    # コメント取得
    if len(terms) > 0:
        # match_typeの変換
        sql_match_type = "all" if match_type == "すべて一致" else "any"
        
        # 複数検索ワードでコメントを取得
        comments = get_comments_multi(
            st.session_state['vid'], 
            terms, 
            match_type=sql_match_type
        )
        
        # ソート
        if sort_by == "時間（降順）":
            comments = sorted(comments, key=lambda c: c['time_seconds'], reverse=True)
        elif sort_by == "いいね数":
            comments = sorted(comments, key=lambda c: c['likes'], reverse=True)
        elif sort_by == "一致数":
            comments = sorted(comments, key=lambda c: len(c['matching_terms']), reverse=True)
    else:
        # 検索ワードなしの場合は通常のコメント取得
        comments = get_comments(st.session_state['vid'])
    
    # コメント一覧表示
    if not comments or len(comments) == 0:
        st.info(f"該当するコメントはありません。{' 検索ワードを変更してみてください。' if terms else ''}")
    else:
        # ページング処理
        page = st.session_state.get('comment_page', 1)
        total_pages = (len(comments) + display_count - 1) // display_count
        
        # コメント表示
        for comment in comments[(page-1)*display_count:page*display_count]:
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 1, 4, 1])
                
                with col1:
                    # 時間とシークボタン
                    time_str = format_time(comment['time_seconds'])
                    if st.button(time_str, key=f"comment_time_{comment['id']}"):
                        st.session_state['sec'] = comment['time_seconds']
                
                with col2:
                    # ユーザー名
                    st.write(f"**{comment['name']}**")
                
                with col3:
                    # 検索ワードをハイライトしたコメント内容
                    comment_text = comment['message']
                    highlighted_text = comment_text
                    
                    # 一致した検索ワードをハイライト
                    if 'matching_terms' in comment and comment['matching_terms']:
                        for term in comment['matching_terms']:
                            color = term_colors.get(term, '#673AB7')
                            highlighted_text = highlighted_text.replace(
                                term, 
                                f"<span style='background-color: {color}; opacity: 0.3;'>{term}</span>"
                            )
                    
                    st.markdown(highlighted_text, unsafe_allow_html=True)
                
                with col4:
                    # 一致した検索ワードのタグ表示
                    if 'matching_terms' in comment and comment['matching_terms']:
                        for term in comment['matching_terms']:
                            color = term_colors.get(term, '#673AB7')
                            st.markdown(
                                f"<span style='background-color: {color}; color: white; padding: 1px 5px; border-radius: 10px; font-size: 0.7rem;'>{term}</span>",
                                unsafe_allow_html=True
                            )
                    
                    # いいね数
                    st.write(f"👍 {comment['likes']}")
            
            st.markdown("---")
        
        # ページネーション
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀ 前へ", disabled=page <= 1):
                st.session_state['comment_page'] = page - 1
                st.rerun()
        
        with col2:
            st.write(f"ページ {page}/{total_pages}")
        
        with col3:
            if st.button("次へ ▶", disabled=page >= total_pages):
                st.session_state['comment_page'] = page + 1
                st.rerun()
```

### 文字起こしタブ

**主要コンポーネント**:
- **検索機能**: 文字起こしテキスト内のキーワード検索
- **表示単位設定**: 文字起こしの表示粒度調整
- **文字起こしリスト**: 時間範囲、話者、テキスト内容、信頼度を表示
- **ダウンロード機能**: 文字起こし全文のエクスポート

**実装例**:
```python
def display_transcription_tab():
    """文字起こしタブの内容を表示する関数"""
    
    # 検索・フィルターコントロール
    col1, col2, col3, col4 = st.columns([2, 1, 1.5, 1.5])
    
    with col1:
        search_keyword = st.text_input(
            "文字起こし検索",
            key="transcription_search"
        )
    
    with col2:
        if st.button("検索", key="transcription_search_button"):
            st.session_state['transcription_keyword'] = search_keyword
            st.cache_data.clear()
            st.rerun()
    
    with col3:
        display_unit = st.selectbox(
            "表示単位",
            ["分ごと", "チャプターごと", "文ごと"],
            key="transcription_display_unit"
        )
    
    with col4:
        st.download_button(
            "全文ダウンロード",
            get_full_transcription(st.session_state['vid']),
            file_name=f"transcription_{st.session_state['vid']}.txt",
            mime="text/plain"
        )
    
    # 文字起こしデータ取得
    keyword = st.session_state.get('transcription_keyword', '')
    transcriptions = get_transcriptions(st.session_state['vid'], keyword)
    
    if not transcriptions:
        st.info(f"文字起こしデータが見つかりません。{' キーワードを変更して検索してください。' if keyword else ''}")
        return
    
    # 現在の再生位置
    current_sec = st.session_state.get('sec', 0)
    
    # ヘッダー行
    col1, col2, col3, col4 = st.columns([1, 1, 4, 1])
    with col1:
        st.write("**時間**")
    with col2:
        st.write("**話者**")
    with col3:
        st.write("**文字起こしテキスト**")
    with col4:
        st.write("**信頼度**")
    
    # 文字起こしリスト
    for transcript in transcriptions:
        # 現在の位置かどうかをチェック
        is_current = (current_sec >= transcript['time_seconds'] and 
                     (transcript['end_time'] is None or current_sec < transcript['end_time']))
        
        # 行のスタイル（現在位置はハイライト）
        row_style = "background-color: #e3f2fd;" if is_current else ""
        
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 1, 4, 1])
            
            with col1:
                # 時間とシークボタン
                time_str = format_time(transcript['time_seconds'])
                if st.button(time_str, key=f"transcript_{transcript['id']}"):
                    st.session_state['sec'] = transcript['time_seconds']
            
            with col2:
                st.write(transcript['speaker'] if 'speaker' in transcript else "")
            
            with col3:
                # キーワードをハイライト
                text = transcript['transcription']
                if keyword and keyword in text:
                    text = text.replace(
                        keyword,
                        f"<span style='background-color: #FFEB3B;'>{keyword}</span>"
                    )
                st.markdown(text, unsafe_allow_html=True)
            
            with col4:
                confidence = transcript.get('confidence', None)
                if confidence is not None:
                    st.write(f"{confidence:.2f}")
        
        st.markdown("---")
    
    # ページネーション
    if len(transcriptions) > 10:
        page = st.session_state.get('transcription_page', 1)
        total_pages = (len(transcriptions) + 10 - 1) // 10
        
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀ 前へ", key="transcription_prev", disabled=page <= 1):
                st.session_state['transcription_page'] = page - 1
                st.rerun()
        
        with col2:
            st.write(f"ページ {page}/{total_pages}")
        
        with col3:
            if st.button("次へ ▶", key="transcription_next", disabled=page >= total_pages):
                st.session_state['transcription_page'] = page + 1
                st.rerun()
```

### 感情分析タブ

**主要コンポーネント**:
- **感情フィルター**: 表示する感情タイプの選択
- **強度閾値設定**: 検出感情の強度によるフィルタリング
- **感情リスト**: 時間範囲、感情タイプ、強度、信頼度を色分け表示
- **色分け表示**: 感情タイプごとに異なる色を使用

**実装例**:
```python
def display_emotion_tab():
    """感情分析タブの内容を表示する関数"""
    
    # 感情タイプと色の定義
    emotion_types = ["笑い", "悲鳴", "興奮", "落ち着き", "苛立ち"]
    emotion_colors = {
        "笑い": "#4CAF50",
        "悲鳴": "#F44336", 
        "興奮": "#FFC107",
        "落ち着き": "#2196F3",
        "苛立ち": "#9C27B0",
    }
    
    # 英語名とのマッピング
    emotion_mapping = {
        "笑い": "laughter",
        "悲鳴": "scream",
        "興奮": "excited",
        "落ち着き": "calm",
        "苛立ち": "frustrated"
    }
    
    # フィルターコントロール
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_emotions = st.multiselect(
            "感情タイプ",
            emotion_types,
            default=emotion_types,
            key="emotion_types"
        )
    
    with col2:
        min_intensity = st.slider(
            "最小強度",
            min_value=0.0,
            max_value=1.0,
            value=0.6,
            step=0.05,
            key="emotion_min_intensity"
        )
    
    with col3:
        if st.button("絞り込み", key="emotion_filter"):
            st.session_state['emotion_filter_applied'] = True
    
    # 感情データ凡例
    st.write("##### 感情タイプ")
    legend_cols = st.columns(len(emotion_types))
    
    for i, (emotion, col) in enumerate(zip(emotion_types, legend_cols)):
        with col:
            if emotion in selected_emotions:
                color = emotion_colors[emotion]
                st.markdown(
                    f"<div style='display:flex;align-items:center'>"
                    f"<div style='width:12px;height:12px;background-color:{color};margin-right:5px'></div>"
                    f"<span>{emotion}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    
    # 感情データ取得
    emotion_params = {
        'emotion_types': [emotion_mapping[e] for e in selected_emotions],
        'min_intensity': min_intensity
    }
    
    emotions = get_emotion_data(st.session_state['vid'], **emotion_params)
    
    if not emotions:
        st.info("条件に一致する感情データが見つかりませんでした。フィルター設定を変更してみてください。")
        return
    
    # ヘッダー行
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        st.write("**時間範囲**")
    with col2:
        st.write("**感情タイプ**")
    with col3:
        st.write("**強度**")
    with col4:
        st.write("**信頼度**")
    
    # 感情リスト
    for emotion in emotions:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                # 時間範囲をクリック可能に
                time_range = f"{format_time_with_seconds(emotion['start_time'])} - {format_time_with_seconds(emotion['end_time'])}"
                if st.button(time_range, key=f"emotion_{emotion['id']}"):
                    st.session_state['sec'] = emotion['start_time']
            
            with col2:
                # 感情タイプを色付きで表示
                e_type_jp = next(k for k, v in emotion_mapping.items() if v == emotion['emotion_type'])
                color = emotion_colors.get(e_type_jp, '#999999')
                st.markdown(
                    f"<span style='background-color: {color}; color: white; padding: 2px 8px; border-radius: 12px;'>{e_type_jp}</span>",
                    unsafe_allow_html=True
                )
            
            with col3:
                # 強度のプログレスバー
                st.progress(emotion['normalized_score'])
            
            with col4:
                # 信頼度
                st.write(f"{emotion['confidence_score']:.2f}")
        
        st.markdown("---")
    
    # ページネーション
    if len(emotions) > 10:
        page = st.session_state.get('emotion_page', 1)
        total_pages = (len(emotions) + 10 - 1) // 10
        
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀ 前へ", key="emotion_prev", disabled=page <= 1):
                st.session_state['emotion_page'] = page - 1
                st.rerun()
        
        with col2:
            st.write(f"ページ {page}/{total_pages}")
        
        with col3:
            if st.button("次へ ▶", key="emotion_next", disabled=page >= total_pages):
                st.session_state['emotion_page'] = page + 1
                st.rerun()
```

---

## 技術的実装のポイント

### 1. JavaScript-Python連携
- IFrameとStreamlitの連携はpostMessageで実現
- クリックイベントからシーク動作までの流れ:
  ```
  Plotlyクリック → session_state['sec']更新 → postMessage送信 → YouTubeプレイヤーがseekTo()実行
  ```
- プレイヤーからの現在位置通知:
  ```
  setInterval() → postMessage({type:'tick'}) → Streamlitが受信 → グラフの縦線位置更新
  ```

### 2. 複数検索ワードの処理
- カンマ区切りの入力から配列に変換
- 各検索ワードに固有の色を割り当て
- 検索ワードごとのコメント出現頻度を同時表示

```python
def get_term_colors(terms):
    """検索ワードごとに固有の色を割り当てる"""
    # 定義済みの色のリスト（最大5色）
    colors = [
        "#673AB7",  # 紫色
        "#2196F3",  # 青色
        "#4CAF50",  # 緑色
        "#FF9800",  # オレンジ色
        "#E91E63",  # ピンク色
    ]
    
    # 各ワードに色を割り当て
    return {term: colors[i % len(colors)] for i, term in enumerate(terms)}
```

### 3. キャッシュ戦略
- RPCクエリ結果は`@st.cache_data(ttl=30)`でキャッシュ
- 粒度変更、検索ワード変更時にキャッシュをクリア
- 頻繁に変わらないデータ（チャプター情報など）は長めのTTLを設定

### 4. 効率的なデータ取得
- サーバーサイドでの集計・フィルタリング処理
- 複数ワード検索のためのカスタムRPC

```sql
-- 複数検索ワードのヒストグラム取得関数
CREATE OR REPLACE FUNCTION public.multi_term_comment_hist(
    _vid UUID,
    _terms TEXT[],
    _g INT
)
RETURNS TABLE(
    term TEXT,
    sec INT,
    hits INT
) AS $$
DECLARE
    _term TEXT;
BEGIN
    -- 各検索ワードに対して処理
    FOREACH _term IN ARRAY _terms
    LOOP
        RETURN QUERY
        SELECT 
            _term AS term,
            FLOOR(time_seconds / _g) * _g AS sec,
            COUNT(*) AS hits
        FROM 
            chat_messages
        WHERE 
            video_id = _vid
            AND message ILIKE '%' || _term || '%'
        GROUP BY 
            sec
        ORDER BY 
            sec;
    END LOOP;
END;
$$ LANGUAGE plpgsql STABLE;
```
- 粒度単位でデータを集計してRPCで取得（サーバー側集計）
- SQLの集計クエリ例:
  ```sql
  SELECT floor(second/_g)*_g as sec, avg(rel_volume), avg(emotion), sum(comment_cnt)
  FROM volume_analysis_secondly
  WHERE video_id = _vid
  GROUP BY sec
  ORDER BY sec
  ```

### 5. ヘルパー関数の充実
- 時間フォーマット（秒→MM:SS形式）
- 色定義（感情タイプや検索ワードごと）
- 改行を含むテキストのHTML表示

### 6. イベント処理とコールバック
- 選択イベント → 状態更新 → データ再取得 → UI更新のサイクル
- コールバックチェーン:
  - 粒度変更 → キャッシュクリア → データ再取得 → グラフ更新
  - グラフクリック → 位置更新 → JS連携 → シーク

### 7. HTML直接操作による最適化
- 複雑なテーブルとインタラクションはHTMLで実装
- JavaScriptによるクリックイベント処理でPython側の再読み込みを回避

---

## レスポンシブデザイン対応

### モバイル対応のポイント
1. **ページ全体設定**
   ```python
   st.set_page_config(layout="wide", page_title="YouTube分析", page_icon="🎬")
   ```

2. **画面サイズに応じたレイアウト調整**
   ```python
   # レスポンシブなカラム構成
   if is_mobile():
       # モバイル向けシングルカラムレイアウト
       youtube_player_container = st.container()
       controls_container = st.container()
   else:
       # デスクトップ向け2カラムレイアウト
       col1, col2 = st.columns([2, 1])
       youtube_player_container = col1.container()
       controls_container = col2.container()
   ```

3. **Plotlyグラフのレスポンシブ設定**
   ```python
   fig.update_layout(
       autosize=True,
       margin=dict(l=10, r=10, t=10, b=10),
       legend=dict(orientation="h"),
       hovermode="x unified"
   )
   ```

4. **モバイル向け表示調整**
   - モバイルではカラム数を減らす
   - 重要な情報を優先表示
   - タッチフレンドリーなUIサイズ調整

### 画面サイズ判定ロジック
```python
def is_mobile():
    # ビューポート幅の取得はクライアントサイドで行う必要がある
    # Streamlitではブラウザ情報にアクセスできないため、代替策を使用
    
    # カスタムCSSを使用して情報を取得
    custom_css = """
    <style>
    .mobile-detector { display: none; }
    @media (max-width: 768px) { 
        .mobile-detector { display: block; } 
    }
    </style>
    <div class="mobile-detector" id="mobile-detector"></div>
    <script>
    if(document.getElementById('mobile-detector').offsetParent !== null) {
        window.parent.postMessage({type: 'is_mobile', value: true}, '*');
    } else {
        window.parent.postMessage({type: 'is_mobile', value: false}, '*');
    }
    </script>
    """
    st.components.v1.html(custom_css, height=0)
    
    # この値はセッションに格納し、JS からのメッセージで更新する
    return st.session_state.get('is_mobile', False)
```

---

このガイドと添付されたワイヤーフレームを組み合わせることで、YouTubeデータ分析可視化サービスの実装作業をスムーズに進めることができます。開発中の質問や詳細な実装上の課題については、追加情報が必要な場合はお気軽にお問い合わせください。