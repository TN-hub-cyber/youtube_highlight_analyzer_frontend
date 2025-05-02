import streamlit as st
import pandas as pd
import time
from components.youtube_player import youtube_player, create_seek_command
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

# YouTubeプレイヤーとメトリクスグラフのレイアウト
col1, col2 = st.columns([6, 4])

with col1:
    # YouTubeプレイヤー
    st.subheader("YouTube動画")
    current_time = youtube_player(
        video_id=youtube_video_id,
        width=650,
        height=365,
        start_seconds=0,
        auto_play=True
    )

with col2:
    # メトリクスグラフ
    st.subheader("メトリクス")
    clicked_time = display_metrics_graph(metrics_data, current_time)
    
    # グラフがクリックされた場合はシーク
    if clicked_time is not None:
        st.session_state['sec'] = clicked_time
        st.rerun()

# タブコンテンツ
tab1, tab2, tab3, tab4 = st.tabs(["📑 チャプター", "💬 コメント", "📝 文字起こし", "😊 感情分析"])

# タブ1: チャプター
with tab1:
    st.header("チャプター")
    
    with st.spinner("チャプターデータを読み込み中..."):
        chapters_data = get_chapters(video_id)
    
    if chapters_data:
        chapters_df = pd.DataFrame(chapters_data)
        
        if not chapters_df.empty:
            st.markdown(f"#### 全 {len(chapters_df)} チャプター")
            
            for _, chapter in chapters_df.iterrows():
                col1, col2, col3 = st.columns([2, 9, 1])
                
                with col1:
                    time_str = format_time(chapter['time_seconds'])
                    st.markdown(f"**{time_str}**")
                
                with col2:
                    st.markdown(f"**{chapter['title']}**")
                    if 'description' in chapter and chapter['description']:
                        st.markdown(chapter['description'])
                
                with col3:
                    if st.button("▶️", key=f"chapter_{chapter['id']}"):
                        st.session_state['sec'] = chapter['time_seconds']
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info("この動画にはチャプターデータがありません。")
    else:
        st.info("この動画にはチャプターデータがありません。")

# タブ2: コメント
with tab2:
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
                            st.session_state['sec'] = comment['time_seconds']
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
                            st.session_state['sec'] = comment['time_seconds']
                            st.rerun()
                    
                    st.markdown("---")
                
                if len(comments_df) > max_comments:
                    st.info(f"表示件数を制限しています。検索機能を使用してコメントを絞り込んでください。")
            else:
                st.info("この動画にはコメントがありません。")
        else:
            st.info("この動画にはコメントがありません。")

# タブ3: 文字起こし
with tab3:
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
                        st.session_state['sec'] = transcript['time_seconds']
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info("この動画には文字起こしデータがありません。")
    else:
        st.info("この動画には文字起こしデータがありません。")

# タブ4: 感情分析
with tab4:
    st.header("感情分析")
    
    with st.spinner("感情分析データを読み込み中..."):
        emotion_data = get_emotion_analysis(video_id)
    
    if emotion_data:
        from components.metrics_graph import display_emotion_graph
        
        # 感情グラフの表示
        clicked_time_emotion = display_emotion_graph(emotion_data, current_time)
        
        # グラフがクリックされた場合はシーク
        if clicked_time_emotion is not None:
            st.session_state['sec'] = clicked_time_emotion
            st.rerun()
        
        # 感情の説明
        with st.expander("感情スコアについて"):
            st.markdown("""
            **感情分析について**
            
            このグラフは動画の音声から検出された感情を時系列で表示しています。
            各感情スコアは0〜1の範囲で正規化されており、値が大きいほどその感情が強く表れています。
            
            主な感情タイプ:
            - **happy (幸せ)**: 喜び、楽しさ、ポジティブな感情
            - **sad (悲しみ)**: 悲しみ、落ち込み、ネガティブな感情
            - **angry (怒り)**: 苛立ち、怒り、攻撃的な感情
            - **surprise (驚き)**: 驚き、意外性に対する反応
            - **fear (恐怖)**: 不安、心配、恐れ
            - **disgust (嫌悪)**: 不快感、拒絶反応
            - **neutral (中立)**: 特定の感情がない平常状態
            """)
    else:
        st.info("この動画には感情分析データがありません。")
