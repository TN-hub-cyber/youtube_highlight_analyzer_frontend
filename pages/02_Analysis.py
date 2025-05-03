import streamlit as st
import pandas as pd
import time
from components.youtube_player import youtube_player, create_seek_command, seek_to
from components.metrics_graph import display_metrics_graph
from utils.supabase_client import (
    get_video_details, 
    get_metrics_agg, 
    get_chapters,
    get_comments,
    get_transcriptions,
    get_emotion_analysis,
    get_multi_term_comment_hist,
    search_comments_multi
)
from utils.formatting import format_time

# ページ設定
st.set_page_config(
    page_title="YouTube分析 - 動画分析",
    page_icon="📊",
    layout="wide"
)

# サイドバー
with st.sidebar:
    st.title("YouTube動画分析")
    st.markdown("---")
    
    # ホーム・動画一覧に戻るボタン
    if st.button("← 動画一覧に戻る"):
        # 動画ID情報はクリアせず、チャンネルページに戻る
        st.switch_page("pages/01_Videos.py")
    
    if st.button("← チャンネル一覧に戻る"):
        # すべての状態をクリア
        for key in ['vid', 'youtube_video_id', 'cid']:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("Home.py")
    
    st.markdown("---")
    
    # 表示設定
    st.subheader("表示設定")
    
    # データ粒度設定
    if 'granularity' not in st.session_state:
        st.session_state['granularity'] = 5
    
    granularity = st.slider(
        "データ粒度 (秒)",
        min_value=1,
        max_value=30,
        value=st.session_state['granularity'],
        step=1,
        key="sidebar_granularity",
        help="時系列データの集計粒度を設定します。数値が小さいほど詳細なデータが表示されますが、処理が重くなる場合があります。"
    )
    
    if granularity != st.session_state['granularity']:
        st.session_state['granularity'] = granularity
        st.rerun()
    
    st.markdown("---")
    st.caption("Powered by Streamlit & Supabase")

# 動画IDがセッション状態にあるか確認
if 'vid' not in st.session_state or 'youtube_video_id' not in st.session_state:
    st.warning("動画が選択されていません。動画一覧から選択してください。")
    if st.button("動画一覧に戻る"):
        st.switch_page("pages/01_Videos.py")
    st.stop()

# メインコンテンツ
video_id = st.session_state['vid']
youtube_video_id = st.session_state['youtube_video_id']
granularity = st.session_state['granularity']

# シーク命令を送信するJavaScriptを作成
create_seek_command()

# データロード中の表示
with st.spinner("動画データを読み込み中..."):
    # 動画詳細データの取得
    video_details = get_video_details(video_id)
    
    if not video_details:
        st.error("動画データの取得に失敗しました。")
        st.stop()
    
    # メトリクスデータの取得
    metrics_data = get_metrics_agg(video_id, granularity)

# ページタイトル
st.title(f"📊 {video_details['title']}")

# 動画情報エリア
col1, col2, col3, col4 = st.columns(4)

with col1:
    # published_atがNoneの場合のチェックを追加
    published_date = '不明'
    if 'published_at' in video_details and video_details['published_at'] is not None:
        try:
            published_date = pd.to_datetime(video_details['published_at']).strftime('%Y/%m/%d')
        except:
            pass
    st.markdown(f"**公開日**: {published_date}")

with col2:
    duration = format_time(video_details['duration']) if 'duration' in video_details else '不明'
    st.markdown(f"**長さ**: {duration}")

with col3:
    view_count = f"{video_details['view_count']:,}" if 'view_count' in video_details else '不明'
    st.markdown(f"**再生回数**: {view_count}")

with col4:
    comment_count = f"{video_details['comment_count']:,}" if 'comment_count' in video_details else '不明'
    st.markdown(f"**コメント数**: {comment_count}")

# YouTubeプレイヤーとコントロールパネルのレイアウト
col1, col2 = st.columns([6, 4])

with col1:
    # YouTubeプレイヤー
    st.subheader("YouTube動画")
    
    # チャプターデータを取得（先に読み込んでプレイヤーに渡す）
    with st.spinner("チャプターデータを読み込み中..."):
        chapters_data = get_chapters(video_id)
    
    # シークポイントリストを生成（チャプターから）
    seek_points = []
    if chapters_data:
        chapters_df = pd.DataFrame(chapters_data)
        if not chapters_df.empty:
            for _, chapter in chapters_df.iterrows():
                # (秒数, ラベル) の形式でシークポイントを追加
                seek_points.append((
                    chapter['time_seconds'], 
                    f"{format_time(chapter['time_seconds'])} - {chapter['title'][:20]}..."
                ))
    
    # YouTubeプレイヤーにシークポイントを渡す
    current_time = youtube_player(
        video_id=youtube_video_id,
        width=650,
        height=450,  # 少し高くして、ボタンの表示スペースを確保
        start_seconds=0,
        auto_play=True,
        show_seek_buttons=True,  # シークボタンを表示
        seek_points=seek_points   # シークポイントリストを渡す
    )

with col2:
    # コントロールパネル
    st.subheader("コントロールパネル")
    
    # 粒度設定
    control_granularity = st.slider(
        "データ粒度 (秒)",
        min_value=1,
        max_value=30,
        value=granularity,
        step=1,
        key="control_panel_granularity",
        help="時系列データの集計粒度を設定します。数値が小さいほど詳細なデータが表示されますが、処理が重くなる場合があります。"
    )
    
    # 粒度が変更された場合はセッション状態を更新
    if control_granularity != granularity:
        st.session_state['granularity'] = control_granularity
        st.rerun()
    
    # 区切り線
    st.markdown("---")
    
    # コメント検索（複数指定可）
    st.markdown("### コメント検索（複数指定可）")
    search_terms_input = st.text_input(
        "検索語を入力（複数語はカンマで区切る）", 
        key="control_search_terms",
        placeholder="例: かわいい, すごい, 面白い"
    )
    
    # 検索語の処理
    if search_terms_input:
        search_terms = [term.strip() for term in search_terms_input.split(',') if term.strip()]
        if search_terms:
            # 検索条件
            match_type = st.radio(
                "検索条件",
                ["いずれかを含む", "すべてを含む"],
                horizontal=True,
                key="control_match_type"
            )
            
            # 検索ボタン
            if st.button("検索", type="primary"):
                # タブをコメントタブに切り替え
                st.session_state['active_tab'] = 1  # コメントタブのインデックス
                st.session_state['search_terms'] = search_terms
                st.session_state['match_type'] = match_type
                st.rerun()
    
    # 区切り線
    st.markdown("---")
    
    # 現在位置
    st.markdown(f"**現在位置**: {format_time(current_time) if current_time is not None else '00:00'}")
    
    # 詳細設定ボタン
    if st.button("詳細設定", key="settings_button"):
        st.session_state['show_settings'] = True
        st.rerun()

# メトリクスグラフ
st.subheader("メトリクス")
clicked_time = display_metrics_graph(metrics_data, current_time)

# グラフがクリックされた場合はシーク
if clicked_time is not None:
    st.session_state['sec'] = clicked_time
    st.rerun()

# タブコンテンツ - アクティブタブの管理
if 'active_tab' not in st.session_state:
    st.session_state['active_tab'] = 0  # デフォルトはチャプタータブ(0)

# タブ切り替え機能
tab_names = ["📑 チャプター", "💬 コメント", "📝 文字起こし", "😊 感情分析"]
tabs = st.tabs(tab_names)

# コントロールパネルからの検索をハンドリング
if 'search_terms' in st.session_state and st.session_state.get('active_tab') == 1:
    # コメントタブアクティブ時に検索語があれば検索フォームに設定
    search_terms = st.session_state['search_terms']
    del st.session_state['search_terms']

# 各タブの内容
# タブ1: チャプター
with tabs[0]:
    # このタブが選択されたら状態を更新
    st.session_state['active_tab'] = 0
    st.header("チャプター")
    
    # チャプターデータは既にプレイヤー表示時に取得済み
    if chapters_data:
        chapters_df = pd.DataFrame(chapters_data)
        
        if not chapters_df.empty:
            st.markdown(f"#### 全 {len(chapters_df)} チャプター")
            
            # チャプターテーブルとして表示
            chapter_table_data = []
            for _, chapter in chapters_df.iterrows():
                time_seconds = chapter['time_seconds']
                time_str = format_time(time_seconds)
                title = chapter['title']
                description = chapter.get('description', '')
                
                # テーブル用のデータを準備
                chapter_table_data.append({
                    "時間": time_str, 
                    "タイトル": title, 
                    "説明": description,
                    "時間（秒）": time_seconds
                })
                
            # DataFrameをテーブルとして表示
            table_df = pd.DataFrame(chapter_table_data)
            
            # 時間をクリックできるボタンに変換
            def make_clickable_time(time_str, seconds):
                # シークボタン付きの時間文字列を返す
                return f"<div style='display:flex; align-items:center; justify-content:space-between;'><span>{time_str}</span><button onclick=\"parent.postMessage({{type:'seek',sec:{seconds}}}, '*');\" style='background:#f0f0f0; border:1px solid #ccc; border-radius:4px; padding:2px 6px;'>▶️</button></div>"
            
            # 時間列をクリッカブルにする
            table_df["時間"] = table_df.apply(lambda row: make_clickable_time(row["時間"], row["時間（秒）"]), axis=1)
            
            # 使わない列を削除
            table_df = table_df.drop("時間（秒）", axis=1)
            
            # テーブルとして表示
            st.markdown("""
            <style>
            .chapter-table {
                width: 100%;
                border-collapse: collapse;
            }
            .chapter-table th {
                background-color: #f8f9fa;
                text-align: left;
                padding: 8px;
                border-bottom: 2px solid #dee2e6;
            }
            .chapter-table td {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # テーブルの下に簡単なシークボタングリッドを表示
            st.write("### チャプターにジャンプ")
            
            # ボタンを3列グリッドで表示
            cols_per_row = 3
            row_count = (len(chapters_df) + cols_per_row - 1) // cols_per_row  # 切り上げ割り算
            
            for row in range(row_count):
                cols = st.columns(cols_per_row)
                for col_idx in range(cols_per_row):
                    chapter_idx = row * cols_per_row + col_idx
                    if chapter_idx < len(chapters_df):
                        chapter = chapters_df.iloc[chapter_idx]
                        with cols[col_idx]:
                            # 時間とタイトル（短縮形）の両方を表示するボタン
                            time_str = format_time(chapter['time_seconds'])
                            short_title = chapter['title'][:15] + "..." if len(chapter['title']) > 15 else chapter['title']
                            button_label = f"{time_str} {short_title}"
                            
                            if st.button(button_label, key=f"chapter_btn_{chapter['id']}"):
                                # シーク関数を直接呼び出す
                                seek_to(chapter['time_seconds'])
                                st.rerun()
            # ユーザーへの注意表示
            st.markdown("""
            <div style="font-size: 12px; color: #666; margin-top: 10px;">
            チャプターボタンはクリックしてジャンプできます。プレイヤー下部にも同様のボタンがあります。
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("この動画にはチャプターデータがありません。")
    else:
        st.info("この動画にはチャプターデータがありません。")

# タブ2: コメント
with tabs[1]:
    # このタブが選択されたら状態を更新
    st.session_state['active_tab'] = 1
    st.header("コメント分析")
    
    # 検索語入力
    search_terms_input = st.text_input(
        "検索語を入力（複数語はカンマで区切る）",
        placeholder="例: かわいい, すごい, 面白い"
    )
    
    search_terms = [term.strip() for term in search_terms_input.split(',')] if search_terms_input else []
    
    if search_terms:
        # 検索語が入力された場合
        col1, col2 = st.columns([1, 1])
        
        with col1:
            match_type = st.radio(
                "検索条件",
                ["いずれかを含む", "すべてを含む"],
                horizontal=True
            )
        
        with col2:
            sort_method = st.radio(
                "並び順",
                ["関連度", "時間順"],
                horizontal=True
            )
        
        # 検索処理
        with st.spinner("コメントを検索中..."):
            # コメント頻度データの取得
            comment_hist_data = get_multi_term_comment_hist(video_id, search_terms, granularity)
            
            # コメント検索
            match_type_param = "all" if match_type == "すべてを含む" else "any"
            search_results = search_comments_multi(video_id, search_terms, match_type_param)
        
        # 検索結果の表示
        if search_results:
            # コメント頻度グラフの表示
            from components.metrics_graph import display_search_graph
            
            st.subheader("検索語の出現頻度")
            clicked_time_search = display_search_graph(comment_hist_data, search_terms, current_time)
            
            # グラフがクリックされた場合はシーク
            if clicked_time_search is not None:
                st.session_state['sec'] = clicked_time_search
                st.rerun()
            
            # ソート
            results_df = pd.DataFrame(search_results)
            if not results_df.empty:
                if sort_method == "時間順":
                    results_df = results_df.sort_values('time_seconds')
                else:  # 関連度順
                    if 'score' in results_df.columns:
                        results_df = results_df.sort_values('score', ascending=False)
                
                # 検索結果一覧の表示
                st.subheader(f"検索結果 ({len(results_df)}件)")
                
                for _, comment in results_df.iterrows():
                    col1, col2, col3 = st.columns([2, 9, 1])
                    
                    with col1:
                        time_str = format_time(comment['time_seconds'])
                        st.markdown(f"**{time_str}**")
                        if 'author' in comment:
                            st.caption(comment['author'])
                    
                    with col2:
                        message = comment['message']
                        # 検索語をハイライト
                        for term in search_terms:
                            if term in message:
                                message = message.replace(term, f"**{term}**")
                        st.markdown(message)
                    
                    with col3:
                        if st.button("▶️", key=f"comment_{comment['id']}"):
                            # セッション変数で設定
                            time_to_seek = comment['time_seconds']
                            st.session_state['sec'] = time_to_seek
                            
                            # スクリプトを直接実行して即座にシーク
                            st.markdown(f"""
                            <script>
                            console.log("コメントジャンプ: {time_to_seek}秒");
                            
                            // 直接グローバル関数を呼び出す
                            if (typeof seekToYouTubeTime === 'function') {{
                                seekToYouTubeTime({time_to_seek});
                            }} else if (typeof player !== 'undefined' && player) {{
                                player.seekTo({time_to_seek});
                                player.playVideo();
                            }}
                            </script>
                            """, unsafe_allow_html=True)
                            
                            # すぐに再実行して変更を反映
                            st.rerun()
                    
                    st.markdown("---")
            else:
                st.info("検索条件に一致するコメントがありませんでした。")
        else:
            st.info("検索条件に一致するコメントがありませんでした。")
    
    else:
        # 検索語が入力されていない場合
        with st.spinner("コメントデータを読み込み中..."):
            comments_data = get_comments(video_id)
        
        if comments_data:
            comments_df = pd.DataFrame(comments_data)
            
            if not comments_df.empty:
                # 時間順にソート
                comments_df = comments_df.sort_values('time_seconds')
                
                # コメント一覧の表示（最大100件）
                max_comments = min(100, len(comments_df))
                st.subheader(f"最新コメント (全{len(comments_df)}件中 {max_comments}件表示)")
                
                for _, comment in comments_df.head(max_comments).iterrows():
                    col1, col2, col3 = st.columns([2, 9, 1])
                    
                    with col1:
                        time_str = format_time(comment['time_seconds'])
                        st.markdown(f"**{time_str}**")
                        if 'name' in comment:
                            st.caption(comment['name'])
                    
                    with col2:
                        st.markdown(comment['message'])
                    
                    with col3:
                        if st.button("▶️", key=f"comment_{comment['id']}"):
                            # セッション変数で設定
                            time_to_seek = comment['time_seconds']
                            st.session_state['sec'] = time_to_seek
                            
                            # スクリプトを直接実行して即座にシーク
                            st.markdown(f"""
                            <script>
                            console.log("通常コメントジャンプ: {time_to_seek}秒");
                            
                            // 直接グローバル関数を呼び出す
                            if (typeof seekToYouTubeTime === 'function') {{
                                seekToYouTubeTime({time_to_seek});
                            }} else if (typeof player !== 'undefined' && player) {{
                                player.seekTo({time_to_seek});
                                player.playVideo();
                            }}
                            </script>
                            """, unsafe_allow_html=True)
                            
                            # すぐに再実行して変更を反映
                            st.rerun()
                    
                    st.markdown("---")
                
                if len(comments_df) > max_comments:
                    st.info(f"表示件数を制限しています。検索機能を使用してコメントを絞り込んでください。")
            else:
                st.info("この動画にはコメントがありません。")
        else:
            st.info("この動画にはコメントがありません。")

# タブ3: 文字起こし
with tabs[2]:
    # このタブが選択されたら状態を更新
    st.session_state['active_tab'] = 2
    st.header("文字起こし")
    
    # 検索フィルター
    transcript_search = st.text_input("🔍 文字起こしを検索", "")
    
    with st.spinner("文字起こしデータを読み込み中..."):
        transcriptions_data = get_transcriptions(video_id)
    
    if transcriptions_data:
        transcriptions_df = pd.DataFrame(transcriptions_data)
        
        if not transcriptions_df.empty:
            # 検索フィルタリング
            if transcript_search:
                filtered_transcripts = transcriptions_df[
                    transcriptions_df['transcription'].str.contains(transcript_search, case=False, na=False)
                ]
                st.markdown(f"検索結果: {len(filtered_transcripts)}件")
            else:
                filtered_transcripts = transcriptions_df
            
            # 時間順にソート
            filtered_transcripts = filtered_transcripts.sort_values('time_seconds')
            
            # 文字起こし一覧の表示
            for _, transcript in filtered_transcripts.iterrows():
                col1, col2, col3 = st.columns([2, 9, 1])
                
                with col1:
                    time_str = format_time(transcript['time_seconds'])
                    st.markdown(f"**{time_str}**")
                
                with col2:
                    text = transcript['transcription']
                    
                    # 検索語をハイライト
                    if transcript_search and transcript_search in text:
                        text = text.replace(transcript_search, f"**{transcript_search}**")
                    
                    st.markdown(text)
                
                with col3:
                    if st.button("▶️", key=f"transcript_{transcript['id']}"):
                        # セッション変数で設定
                        time_to_seek = transcript['time_seconds']
                        st.session_state['sec'] = time_to_seek
                        
                        # スクリプトを直接実行して即座にシーク
                        st.markdown(f"""
                        <script>
                        console.log("文字起こしジャンプ: {time_to_seek}秒");
                        
                        // 直接グローバル関数を呼び出す
                        if (typeof seekToYouTubeTime === 'function') {{
                            seekToYouTubeTime({time_to_seek});
                        }} else if (typeof player !== 'undefined' && player) {{
                            player.seekTo({time_to_seek});
                            player.playVideo();
                        }}
                        </script>
                        """, unsafe_allow_html=True)
                        
                        # すぐに再実行して変更を反映
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info("この動画には文字起こしデータがありません。")
    else:
        st.info("この動画には文字起こしデータがありません。")

# タブ4: 感情分析
with tabs[3]:
    # このタブが選択されたら状態を更新
    st.session_state['active_tab'] = 3
    st.header("感情分析")
    
    with st.spinner("感情分析データを読み込み中..."):
        emotion_data = get_emotion_analysis(video_id)
    
    if emotion_data:
        # データフレームに変換
        from utils.data_utils import prepare_emotion_data
        emotion_df = prepare_emotion_data(emotion_data)
        
        if not emotion_df.empty:
            # 時間範囲選択
            st.subheader("感情分析データ")
            
            # 表形式での表示（ワイヤーフレームに準拠）
            emotion_cols = [col for col in emotion_df.columns if col != 'time_seconds']
            
            # 一部のデータを表示（最大100件）
            max_rows = min(100, len(emotion_df))
            display_df = emotion_df.head(max_rows).copy()
            
            # データ整形
            display_df['time'] = display_df['time_seconds'].apply(format_time)
            
            # 表示する列の順序と名前を設定
            emotion_types = ['happy', 'sad', 'angry', 'surprise', 'fear', 'disgust', 'neutral']
            
            # 存在する感情タイプだけを表示
            available_types = [t for t in emotion_types if t in display_df.columns]
            
            # 表示するデータフレームを作成
            view_df = pd.DataFrame()
            view_df['時間'] = display_df['time']
            
            # 感情タイプごとに列を追加（日本語名に変換）
            emotion_names = {
                'happy': '喜び',
                'sad': '悲しみ',
                'angry': '怒り',
                'surprise': '驚き',
                'fear': '恐怖',
                'disgust': '嫌悪',
                'neutral': '中立'
            }
            
            for emotion in available_types:
                if emotion in display_df.columns:
                    view_df[emotion_names.get(emotion, emotion)] = display_df[emotion].round(2)
            
            # 最大感情を強調表示するスタイル関数
            def highlight_max(row):
                emotion_cols = [col for col in row.index if col != '時間']
                if not emotion_cols:
                    return [''] * len(row)
                    
                max_col = max(emotion_cols, key=lambda x: row[x])
                return ['font-weight: bold; background-color: #e6f2ff' if col == max_col else '' for col in row.index]
            
            # スタイル適用
            st.dataframe(
                view_df.style.apply(highlight_max, axis=1),
                use_container_width=True,
                height=400
            )
            
            # シーク機能
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_time = st.slider(
                    "時間を選択してジャンプ", 
                    min_value=0, 
                    max_value=int(emotion_df['time_seconds'].max()),
                    value=int(current_time) if current_time is not None else 0,
                    key="emotion_tab_time_slider"
                )
            
            with col2:
                if st.button("▶️ ジャンプ", key="emotion_seek"):
                    # セッション変数で設定
                    time_to_seek = selected_time
                    st.session_state['sec'] = time_to_seek
                    
                    # スクリプトを直接実行して即座にシーク
                    st.markdown(f"""
                    <script>
                    console.log("感情分析ジャンプ: {time_to_seek}秒");
                    
                    // 直接グローバル関数を呼び出す
                    if (typeof seekToYouTubeTime === 'function') {{
                        seekToYouTubeTime({time_to_seek});
                    }} else if (typeof player !== 'undefined' && player) {{
                        player.seekTo({time_to_seek});
                        player.playVideo();
                    }}
                    </script>
                    """, unsafe_allow_html=True)
                    
                    # すぐに再実行して変更を反映
                    st.rerun()
            
            if len(emotion_df) > max_rows:
                st.info(f"表示件数を制限しています（{max_rows}/{len(emotion_df)}件表示）")
        
        # 感情の説明
        with st.expander("感情スコアについて"):
            st.markdown("""
            **感情分析について**
            
            このテーブルは動画の音声から検出された感情を時系列で表示しています。
            各感情スコアは0〜1の範囲で正規化されており、値が大きいほどその感情が強く表れています。
            
            主な感情タイプ:
            - **喜び (happy)**: 喜び、楽しさ、ポジティブな感情
            - **悲しみ (sad)**: 悲しみ、落ち込み、ネガティブな感情
            - **怒り (angry)**: 苛立ち、怒り、攻撃的な感情
            - **驚き (surprise)**: 驚き、意外性に対する反応
            - **恐怖 (fear)**: 不安、心配、恐れ
            - **嫌悪 (disgust)**: 不快感、拒絶反応
            - **中立 (neutral)**: 特定の感情がない平常状態
            
            各時間で最も強い感情が強調表示されています。
            """)
    else:
        st.info("この動画には感情分析データがありません。")
