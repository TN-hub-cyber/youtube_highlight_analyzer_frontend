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
    search_comments_multi,
    get_volume_analysis_secondly,
    get_highlight_segments
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
        # 現在の再生位置を保持
        current_position = st.session_state.get('sec', None)
        
        # 粒度設定を更新
        st.session_state['granularity'] = granularity
        
        # 再生位置を保持したまま再読み込み
        if current_position is not None:
            st.session_state['_persist_position'] = current_position
        
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

# シーク命令を処理
create_seek_command()

# 複雑なシーク状態管理 - 優先度順に処理（クリーンアップはプレイヤー初期化後に移動）

# 1. 直接シーク命令フラグがある場合の処理（優先）
if '_direct_seek_command' in st.session_state and st.session_state.get('_direct_seek_command', False):
    # 操作IDと詳細を記録
    operation_id = st.session_state.get('_active_seek_operation', '不明')
    seek_id = st.session_state.get('_seek_id', '不明')
    seek_time = st.session_state.get('_seek_sec', 0)
    seek_source = st.session_state.get('_seek_source', '不明')
    
    print(f"\n===== シーク命令実行: ID={operation_id} =====")
    print(f"➤ 詳細: 操作ID={operation_id}, シークID={seek_id}")
    print(f"➤ 時間: {seek_time}秒, 発生源: {seek_source}")
    
    # シーク命令実行済みフラグをセット
    st.session_state['_seek_command_executed'] = True
    
    # シーク命令フラグのみクリア（値は保持してプレイヤーに渡す）
    del st.session_state['_direct_seek_command']
    
    # クリーンアップをスケジュール（プレイヤー表示後にクリア）
    st.session_state['_cleanup_after_player'] = True
    
    # 即座にページをリロード
    print(f"➤ 再読み込み開始...")
    st.rerun()

# 2. フォースリロードフラグがある場合は処理し、クリア
elif '_force_reload' in st.session_state:
    print(f"\n===== フォースリロードフラグを検出 =====")
    # フラグをクリア
    del st.session_state['_force_reload']
    # 即座にページをリロード
    print(f"➤ 再読み込み開始...")
    st.rerun()

# 3. クリーンアップはプレイヤー初期化後に移動（下記に記載）

# データロード中の表示
with st.spinner("動画データを読み込み中..."):
    # 動画詳細データの取得
    video_details = get_video_details(video_id)
    
    if not video_details:
        st.error("動画データの取得に失敗しました。")
        st.stop()
    
# メトリクスデータの取得
    metrics_data = get_metrics_agg(video_id, granularity)
    
    # 詳細音量分析データの取得（metrics_graph.py内で使用）
    volume_detail_data = get_volume_analysis_secondly(video_id)

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

# レイアウト最適化: プレイヤーを全幅で表示し、コントロールパネルを削除
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

# YouTubeプレイヤーにシークポイントを渡す - 幅を広げて表示
current_time = youtube_player(
    video_id=youtube_video_id,
    width=800,
    height=450,
    start_seconds=0,
    auto_play=True,
    show_seek_buttons=True,  # シークボタンを表示
    seek_points=seek_points   # シークポイントリストを渡す
)

# プレイヤー初期化後にクリーンアップ処理を実行（重要：順序を変更）
# このタイミングでクリーンアップすることで、プレイヤーがシーク値を読み込んだ後に変数を削除できる
if '_pending_cleanup' in st.session_state and st.session_state.get('_pending_cleanup', False):
    print(f"\n===== 保留中のクリーンアップ処理を実行 =====")
    # クリーンアップフラグを削除
    del st.session_state['_pending_cleanup']
    
    # クリーンアップすべき変数リスト（すべてのシーク関連変数）
    cleanup_vars = [
        '_active_seek_operation', '_seek_sec', 'sec', '_force_reload', 
        '_direct_seek_command', '_seek_id', '_seek_command_executed',
        '_seek_source'
    ]
    
    # 存在する変数のみクリア
    for key in cleanup_vars:
        if key in st.session_state:
            print(f"  クリーンアップ: {key}={st.session_state[key]}")
            del st.session_state[key]
    
    print(f"  クリーンアップ完了")
    
    # シーク処理が完了したら変数をクリア - 優先度の高い処理として最初に配置
    if '_seek_sec' in st.session_state:
        print(f"プレイヤー初期化完了: _seek_sec={st.session_state['_seek_sec']}をクリア")
        del st.session_state['_seek_sec']
        # 他の関連変数もクリア
        for key in ['sec', '_force_reload', '_direct_seek_command', '_seek_id', '_seek_command_executed']:
            if key in st.session_state:
                print(f"  関連変数をクリア: {key}")
                del st.session_state[key]

# 現在位置を表示 (コントロールパネルから移動)
st.markdown(f"**現在位置**: {format_time(current_time) if current_time is not None else '00:00'}")

# メトリクスグラフ - 現在時間をトラッキング
st.subheader("メトリクス")

# 再生位置を常に最新の状態に保つ
if '_seek_sec' in st.session_state:
    # シーク命令がある場合はその位置を使う
    track_position = st.session_state['_seek_sec']
elif 'sec' in st.session_state:
    # 古いセッション変数も確認
    track_position = st.session_state['sec']
else:
    # YouTubeプレイヤーから返された現在位置を使用
    track_position = current_time
    
clicked_time = display_metrics_graph(metrics_data, track_position)

# グラフがクリックされた場合はシークは既にseek_to関数内で処理されているので
# ここでは特に何もする必要はない（修正済み）
# if clicked_time is not None:
#     # 修正済み - metrics_graph.py内でseek_to関数を使用している
#     pass

# タブコンテンツ - アクティブタブの管理
if 'active_tab' not in st.session_state:
    st.session_state['active_tab'] = 0  # デフォルトはチャプタータブ(0)

# タブ切り替え機能
tab_names = ["📑 チャプター", "💬 コメント", "📝 文字起こし", "😊 感情分析", "✨ ハイライト"]
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
            
            # テーブル表示
            table_data = []
            for i, chapter in enumerate(chapters_data):
                # 基本データフォーマット
                time_seconds = chapter['time_seconds']
                time_str = format_time(time_seconds)
                title = chapter['title']
                description = chapter.get('description', '')
                
                # テーブル表示用データを収集
                table_data.append({
                    "番号": i+1,
                    "時間": time_str,
                    "タイトル": title,
                    "説明": description,
                    "秒数": time_seconds  # 内部計算用
                })
            
            # データフレームとしてテーブル表示
            df = pd.DataFrame(table_data)
            
            # 改良版チャプター表示 - 視認性向上のためにレイアウトを改善
            for i, row in df.iterrows():
                # 情報とボタンを統合した大きめのボタン形式 UI
                col1, col2 = st.columns([11, 1])
                
                with col1:
                    # 左側に時間とタイトルを表示
                    st.markdown(f"### {row['番号']}. {row['時間']} - {row['タイトル']}")
                    if row['説明']:
                        st.markdown(f"<div style='margin-left: 20px; margin-top: -15px; font-size: 0.9em; color: #666;'>{row['説明']}</div>", unsafe_allow_html=True)
                
                with col2:
                    # 右側にボタンを配置
                    if st.button("▶", key=f"chapter_{i}", help=f"{row['時間']}にジャンプ"):
                        chapter_time = float(row['秒数'])
                        print(f"チャプターボタン{i}がクリックされました: {chapter_time}秒")
                        # 関数呼び出し前にシーク関連セッション変数をクリア
                        for key in ['_seek_sec', 'sec', '_force_reload']:
                            if key in st.session_state:
                                del st.session_state[key]
                        # seek_to関数を直接呼び出し
                        seek_to(chapter_time)
                        # 即座に再読み込み
                        st.rerun()
                
                # 視覚的な区切り - より細いセパレーター
                st.markdown("<hr style='margin: 5px 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
            
            # プレイヤー下部のボタンに関する注意表示
            st.markdown("""
            <div style="font-size: 14px; color: #666; margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
            <b>ヒント:</b> 動画プレイヤー下部にもチャプターボタンがあり、再生中にクリックして移動できます。
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
    
    # 検索状態の保持
    if 'comment_search_terms_input' not in st.session_state:
        st.session_state['comment_search_terms_input'] = ""
    if 'comment_match_type' not in st.session_state:
        st.session_state['comment_match_type'] = "いずれかを含む"
    if 'comment_sort_method' not in st.session_state:
        st.session_state['comment_sort_method'] = "関連度"
    
    # 検索語入力と「クリア」ボタンを横に配置
    col1, col2 = st.columns([5, 1])
    
    with col1:
        # 検索語入力（セッション状態から初期値を取得）
        search_terms_input = st.text_input(
            "検索語を入力（複数語はカンマで区切る）",
            value=st.session_state['comment_search_terms_input'],
            placeholder="例: かわいい, すごい, 面白い"
        )
        
        # 検索入力が変更されたらセッション状態を更新
        if search_terms_input != st.session_state['comment_search_terms_input']:
            st.session_state['comment_search_terms_input'] = search_terms_input
            
    with col2:
        # クリアボタン
        if st.button("クリア", key="clear_comment_search"):
            # 検索語をクリア
            st.session_state['comment_search_terms_input'] = ""
            # ページをリロード
            st.rerun()
    
    search_terms = [term.strip() for term in search_terms_input.split(',')] if search_terms_input else []
    
    if search_terms:
        # 検索語が入力された場合
        col1, col2 = st.columns([1, 1])
        
        with col1:
            match_type = st.radio(
                "検索条件",
                ["いずれかを含む", "すべてを含む"],
                horizontal=True,
                index=0 if st.session_state['comment_match_type'] == "いずれかを含む" else 1
            )
            # 値が変更されたらセッション状態を更新
            if match_type != st.session_state['comment_match_type']:
                st.session_state['comment_match_type'] = match_type
        
        with col2:
            sort_method = st.radio(
                "並び順",
                ["関連度", "時間順"],
                horizontal=True,
                index=0 if st.session_state['comment_sort_method'] == "関連度" else 1
            )
            # 値が変更されたらセッション状態を更新
            if sort_method != st.session_state['comment_sort_method']:
                st.session_state['comment_sort_method'] = sort_method
        
        # 検索処理
        with st.spinner("コメントを検索中..."):
            # コメント頻度データの取得
            comment_hist_data = get_multi_term_comment_hist(video_id, search_terms, granularity)
            
            # コメント検索
            match_type_param = "all" if match_type == "すべてを含む" else "any"
            search_results = search_comments_multi(video_id, search_terms, match_type_param)
        
        # 検索結果の表示
        if search_results:
            # コメント頻度グラフをメトリクスに統合（オプション）
            with st.expander("検索語の出現頻度グラフ", expanded=True):
                from components.metrics_graph import display_search_graph
                
                st.subheader("検索語の出現頻度")
                clicked_time_search = display_search_graph(comment_hist_data, search_terms, current_time)
                
                # 説明を追加
                st.markdown("""
                <div style="font-size: 12px; color: #666; margin-top: 5px;">
                グラフはメトリクスグラフと同期しています。クリックで動画の該当位置に移動できます。
                </div>
                """, unsafe_allow_html=True)
            
            # ソート
            results_df = pd.DataFrame(search_results)
            if not results_df.empty:
                if sort_method == "時間順":
                    results_df = results_df.sort_values('time_seconds')
                else:  # 関連度順
                    if 'score' in results_df.columns:
                        results_df = results_df.sort_values('score', ascending=False)
                
                # 検索結果一覧の表示 - 改善されたUIで表示
                st.subheader(f"検索結果 ({len(results_df)}件)")
                
                # ページネーションを追加して表示を制限
                items_per_page = 20
                total_pages = (len(results_df) + items_per_page - 1) // items_per_page
                
                # セッション状態の初期化
                if 'comment_search_page' not in st.session_state:
                    st.session_state['comment_search_page'] = 0
                
                # 現在のページ
                current_page = st.session_state['comment_search_page']
                
                # 表示するデータの範囲
                start_idx = current_page * items_per_page
                end_idx = min(start_idx + items_per_page, len(results_df))
                
                # 検索結果を表示
                for i, (_, comment) in enumerate(results_df.iloc[start_idx:end_idx].iterrows(), start=start_idx):
                    # 情報とボタンを統合した改良版レイアウト
                    col1, col2 = st.columns([11, 1])
                    
                    with col1:
                        time_str = format_time(comment['time_seconds'])
                        
                        # 投稿者情報と時間をヘッダーに
                        author = comment.get('author', comment.get('name', ''))
                        header = f"**{time_str}**" + (f" - {author}" if author else "")
                        st.markdown(header)
                        
                        # メッセージ内容（検索語をハイライト）
                        message = comment['message']
                        for term in search_terms:
                            if term.lower() in message.lower():
                                # 大文字小文字を区別しないハイライト
                                import re
                                pattern = re.compile(re.escape(term), re.IGNORECASE)
                                matches = list(pattern.finditer(message))
                                # 後ろから処理して位置がずれないように
                                for match in reversed(matches):
                                    start, end = match.span()
                                    match_text = message[start:end]
                                    message = message[:start] + f"**{match_text}**" + message[end:]
                                    
                        # 検索語をハイライトしたメッセージを表示
                        st.markdown(f"<div style='margin-left: 20px;'>{message}</div>", unsafe_allow_html=True)
                        
                        # 一致した検索語の情報を追加
                        if 'matched_terms' in comment and comment['matched_terms']:
                            matched_terms = ", ".join(comment['matched_terms'])
                            st.markdown(f"<div style='margin-left: 20px; font-size: 0.8em; color: #666;'>一致: {matched_terms}</div>", unsafe_allow_html=True)
                    
                    with col2:
                        # ジャンプボタン
                        if st.button("▶️", key=f"comment_{i}_{comment.get('id', i)}", help=f"{time_str}にジャンプ"):
                            comment_time = float(comment['time_seconds'])
                            print(f"コメント再生ボタンがクリックされました: {comment_time}秒")
                            for key in ['_seek_sec', 'sec', '_force_reload']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            seek_to(comment_time)
                            st.rerun()
                    
                    # 細いセパレーター
                    st.markdown("<hr style='margin: 10px 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
                
                # ページネーションコントロール
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 3, 1])
                    
                    with col1:
                        if st.button("◀ 前のページ", key="prev_comment_page", disabled=current_page == 0):
                            st.session_state['comment_search_page'] = max(0, current_page - 1)
                            st.rerun()
                    
                    with col2:
                        st.markdown(f"<div style='text-align: center;'>ページ {current_page + 1}/{total_pages}</div>", unsafe_allow_html=True)
                    
                    with col3:
                        if st.button("次のページ ▶", key="next_comment_page", disabled=current_page >= total_pages - 1):
                            st.session_state['comment_search_page'] = min(total_pages - 1, current_page + 1)
                            st.rerun()
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
                # comments_df = comments_df.sort_values('time_seconds')
                
                # 時間の昇順にソート(データ取得時に昇順でとってきてるが念のため)
                comments_df = comments_df.sort_values('time_seconds', ascending=True)
                
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
                            # 一時変数に保存してから、seek_to関数を呼び出す
                            comment_time = float(comment['time_seconds'])
                            print(f"コメント再生ボタンがクリックされました: {comment_time}秒")
                            # 関数呼び出し前にすべてのシーク関連セッション変数をクリア
                            for key in ['_seek_sec', 'sec', '_force_reload']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            # seek_to関数を直接呼び出し
                            seek_to(comment_time)
                            # 即座に再読み込み
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
    
    # 検索フィルターとクリアボタンを横に配置
    if 'transcript_search' not in st.session_state:
        st.session_state['transcript_search'] = ""
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        transcript_search = st.text_input("🔍 文字起こしを検索", value=st.session_state['transcript_search'])
        
        # 検索語が変更されたらセッション状態を更新
        if transcript_search != st.session_state['transcript_search']:
            st.session_state['transcript_search'] = transcript_search
            
    with col2:
        # クリアボタン
        if st.button("クリア", key="clear_transcript_search"):
            # 検索語をクリア
            st.session_state['transcript_search'] = ""
            # ページをリロード
            st.rerun()
    
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
            for i, (_, transcript) in enumerate(filtered_transcripts.iterrows()):
                # データの検証
                if 'time_seconds' not in transcript or 'transcription' not in transcript:
                    continue  # 必要なデータがない行はスキップ
                
                col1, col2, col3 = st.columns([2, 9, 1])
                
                with col1:
                    time_str = format_time(transcript['time_seconds'])
                    st.markdown(f"**{time_str}**")
                
                with col2:
                    # テキストの確認と整形
                    if not isinstance(transcript['transcription'], str):
                        text = str(transcript['transcription'])
                    else:
                        text = transcript['transcription']
                    
                    # 検索語をハイライト（大文字小文字を区別しない）
                    if transcript_search:
                        import re
                        pattern = re.compile(re.escape(transcript_search), re.IGNORECASE)
                        matches = list(pattern.finditer(text))
                        if matches:
                            # マッチした部分を強調表示
                            for match in reversed(matches):  # 後ろから処理して位置がずれないようにする
                                start, end = match.span()
                                match_text = text[start:end]
                                text = text[:start] + f"**{match_text}**" + text[end:]
                    
                    st.markdown(text)
                
                with col3:
                    # ユニークなボタンキー（インデックスと時間を組み合わせて一意性を確保）
                    unique_key = f"transcript_{i}_{hash(str(transcript.get('id', '')))}"
                    if st.button("▶️", key=unique_key):
                        # 一時変数に保存してから、seek_to関数を呼び出す
                        trans_time = float(transcript['time_seconds'])
                        print(f"文字起こし再生ボタンがクリックされました: {trans_time}秒")
                        # 関数呼び出し前にすべてのシーク関連セッション変数をクリア
                        for key in ['_seek_sec', 'sec', '_force_reload']:
                            if key in st.session_state:
                                del st.session_state[key]
                        # seek_to関数を直接呼び出し
                        seek_to(trans_time)
                        # 即座に再読み込み
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
    
    # セッション状態の初期化
    if 'emotion_filter_type' not in st.session_state:
        st.session_state['emotion_filter_type'] = []
    
    if 'emotion_filter_confidence' not in st.session_state:
        st.session_state['emotion_filter_confidence'] = 0.0
    
    if 'emotion_page' not in st.session_state:
        st.session_state['emotion_page'] = 0
    
    if 'emotion_page_size' not in st.session_state:
        st.session_state['emotion_page_size'] = 10  # デフォルトの1ページ表示件数
    
    with st.spinner("感情分析データを読み込み中..."):
        emotion_data = get_emotion_analysis(video_id)
    
    if emotion_data:
        # データフレームに変換
        from utils.data_utils import prepare_emotion_data
        emotion_df = prepare_emotion_data(emotion_data)
        
        if not emotion_df.empty:
            # 時間範囲選択
            st.subheader("感情分析データ")
            
            # 感情タイプの表示名マッピング
            emotion_names = {
                'Scream': 'スクリーム',
                'Screaming': '叫び声',
                'Crying': '泣き声',
                'Gasp': '息を呑む',
                'Yell': '怒鳴り声',
                'Shriek': '悲鳴',
                'Wail': '泣き叫び',
                'HowlRoar': '遠吠え/咆哮',
                'Howl': '遠吠え',
                'Roar': '咆哮',
                'Growl': 'うなり声',
                'Groan': '呻き声',
                'Bellow': '大声'
            }
            
            # データ前処理
            # 時間を人間が読みやすい形式に変換
            emotion_df['time_formatted'] = emotion_df['time_seconds'].apply(format_time)
            
            # 感情タイプを日本語に変換
            emotion_df['emotion_type_ja'] = emotion_df['emotion_type'].apply(lambda x: emotion_names.get(x, x))
            
            # 信頼度スコアを小数点以下2桁に丸める
            emotion_df['confidence_score'] = emotion_df['confidence_score'].apply(lambda x: round(float(x), 2) if pd.notnull(x) else 0)
            
            # フィルター用UI
            st.subheader("フィルター設定")
            
            # 3列レイアウトでフィルターを作成
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # 感情タイプフィルター
                # 利用可能な感情タイプをデータから取得
                available_emotions = sorted(emotion_df['emotion_type'].unique())
                available_emotions_ja = [emotion_names.get(e, e) for e in available_emotions]
                
                # 日本語表示名と内部値のマッピングを作成
                emotion_options = dict(zip(available_emotions_ja, available_emotions))
                
                # マルチセレクトによる感情タイプ選択
                selected_emotions_ja = st.multiselect(
                    "感情タイプ",
                    options=available_emotions_ja,
                    default=[],
                    key="emotion_type_filter"
                )
                
                # 日本語表示名から内部値に変換
                selected_emotions = [emotion_options[e_ja] for e_ja in selected_emotions_ja]
                
                # 選択が変更された場合はセッション状態を更新し、ページをリセット
                if selected_emotions != st.session_state['emotion_filter_type']:
                    st.session_state['emotion_filter_type'] = selected_emotions
                    st.session_state['emotion_page'] = 0
            
            with col2:
                # 信頼度フィルター
                confidence_threshold = st.slider(
                    "最小信頼度",
                    min_value=0.0,
                    max_value=1.0,
                    value=st.session_state['emotion_filter_confidence'],
                    step=0.05,
                    format="%.2f",
                    key="confidence_threshold"
                )
                
                # 値が変更された場合はセッション状態を更新し、ページをリセット
                if confidence_threshold != st.session_state['emotion_filter_confidence']:
                    st.session_state['emotion_filter_confidence'] = confidence_threshold
                    st.session_state['emotion_page'] = 0
                
                # 1ページあたりの表示件数
                page_size = st.selectbox(
                    "表示件数",
                    options=[5, 10, 20, 50, 100],
                    index=1,  # デフォルトは10
                    key="page_size"
                )
                
                # 値が変更された場合はセッション状態を更新し、ページをリセット
                if page_size != st.session_state['emotion_page_size']:
                    st.session_state['emotion_page_size'] = page_size
                    st.session_state['emotion_page'] = 0
            
            # フィルタークリアボタンを削除（ユーザーフィードバックに基づく修正）
            
            # フィルタリング処理
            filtered_df = emotion_df.copy()
            
            # 感情タイプでフィルタリング
            if st.session_state['emotion_filter_type']:
                filtered_df = filtered_df[filtered_df['emotion_type'].isin(st.session_state['emotion_filter_type'])]
            
            # 信頼度でフィルタリング
            if st.session_state['emotion_filter_confidence'] > 0:
                filtered_df = filtered_df[filtered_df['confidence_score'] >= st.session_state['emotion_filter_confidence']]
            
            # ページネーション処理
            total_items = len(filtered_df)
            page_size = st.session_state['emotion_page_size']
            current_page = st.session_state['emotion_page']
            total_pages = max(1, (total_items + page_size - 1) // page_size)  # 切り上げ除算
            
            # ページが範囲外にならないように調整
            if current_page >= total_pages:
                st.session_state['emotion_page'] = total_pages - 1
                current_page = total_pages - 1
            
            # 現在のページのデータを取得
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, total_items)
            
            if not filtered_df.empty:
                display_df = filtered_df.iloc[start_idx:end_idx]
                
                # 結果情報を表示
                st.subheader(f"感情分析リスト ({total_items}件中 {start_idx + 1}～{end_idx}件を表示)")
                
                # データ表示
                for i, row in display_df.iterrows():
                    cols = st.columns([2, 3, 3, 1])
                    
                    with cols[0]:
                        st.markdown(f"**{row['time_formatted']}**")
                    
                    with cols[1]:
                        st.markdown(f"**{row['emotion_type_ja']}**")
                    
                    with cols[2]:
                        # 信頼度スコアをプログレスバーとして表示
                        score = row['confidence_score']
                        st.progress(score)
                        st.caption(f"信頼度: {score:.2f}")
                    
                    with cols[3]:
                        # ジャンプボタン
                        if st.button("▶️", key=f"emotion_{i}"):
                            # 一時変数に保存してから、seek_to関数を呼び出す
                            emotion_time = float(row['time_seconds'])
                            print(f"感情分析ボタン{i}がクリックされました: {emotion_time}秒")
                            # 関数呼び出し前にすべてのシーク関連セッション変数をクリア
                            for key in ['_seek_sec', 'sec', '_force_reload']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            # seek_to関数を直接呼び出し
                            seek_to(emotion_time)
                            # 即座に再読み込み
                            st.rerun()
                    
                    # 区切り線
                    st.divider()
                
                # ページネーションコントロール
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col1:
                    if st.button("前へ", key="prev_page", disabled=current_page == 0):
                        st.session_state['emotion_page'] = max(0, current_page - 1)
                        st.rerun()
                
                with col2:
                    st.write(f"ページ: {current_page + 1} / {total_pages}")
                    
                    # ページ番号入力
                    page_input = st.number_input(
                        "ページ番号を入力",
                        min_value=1,
                        max_value=total_pages,
                        value=current_page + 1,
                        step=1,
                        key="page_number"
                    )
                    
                    if st.button("移動", key="goto_page"):
                        st.session_state['emotion_page'] = page_input - 1
                        st.rerun()
                
                with col3:
                    if st.button("次へ", key="next_page", disabled=current_page >= total_pages - 1):
                        st.session_state['emotion_page'] = min(total_pages - 1, current_page + 1)
                        st.rerun()
            else:
                st.info("条件に一致するデータがありません。フィルターを調整してください。")
        
        # 感情の説明
        with st.expander("感情分析データについて"):
            st.markdown("""
            **感情分析について**
            
            このテーブルは動画の音声から検出された感情を時系列で表示しています。
            各感情スコアは0〜1の範囲で正規化されており、値が大きいほどその感情が強く表れています。
            
            **感情タイプ一覧**:
            - **スクリーム (Scream)**: 叫び声や悲鳴
            - **叫び声 (Screaming)**: 大声での叫び
            - **泣き声 (Crying)**: 涙を伴う感情表現
            - **息を呑む (Gasp)**: 驚きや衝撃による息の詰まり
            - **怒鳴り声 (Yell)**: 怒りや興奮を表す大声
            - **悲鳴 (Shriek)**: 恐怖や驚きの鋭い声
            - **泣き叫び (Wail)**: 悲しみを伴う大きな泣き声
            - **遠吠え/咆哮 (HowlRoar)**: 力強い感情表現の声
            - **遠吠え (Howl)**: 長く引き伸ばした声
            - **咆哮 (Roar)**: 力強い怒りや興奮の表現
            - **うなり声 (Growl)**: 低い音域での威嚇や不満
            - **呻き声 (Groan)**: 痛みや不快感の表現
            - **大声 (Bellow)**: 非常に大きな叫び声
            
            **信頼度スコア**は、その感情が検出された確実性を示しています。値が高いほど、その感情が明確に表れていると判断されています。
            """)
    else:
        st.info("この動画には感情分析データがありません。")

# タブ5: ハイライト
with tabs[4]:
    # このタブが選択されたら状態を更新
    st.session_state['active_tab'] = 4
    st.header("ハイライト")
    
    with st.spinner("ハイライトデータを読み込み中..."):
        highlight_data = get_highlight_segments(video_id)
    
    if highlight_data:
        # ハイライトデータを表示
        st.subheader(f"ハイライトセグメント ({len(highlight_data)}件)")
        
        # ページネーション状態の初期化
        if 'highlight_page' not in st.session_state:
            st.session_state['highlight_page'] = 0
        
        # 1ページあたりの表示件数
        items_per_page = 10
        
        # 総ページ数の計算
        total_items = len(highlight_data)
        total_pages = (total_items + items_per_page - 1) // items_per_page  # 切り上げ除算
        
        # 現在のページ
        current_page = st.session_state['highlight_page']
        
        # ページが範囲外にならないように調整
        if current_page >= total_pages:
            st.session_state['highlight_page'] = total_pages - 1
            current_page = total_pages - 1
        
        # 現在のページのデータを取得
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = highlight_data[start_idx:end_idx]
        
        # 各ハイライトセグメントを表示
        for i, highlight in enumerate(page_data):
            # 左右のレイアウト
            col1, col2 = st.columns([10, 2])
            
            with col1:
                # 時間情報
                timestamp_start = highlight.get('timestamp_start', format_time(highlight['start_second']))
                timestamp_end = highlight.get('timestamp_end', format_time(highlight['end_second']))
                timestamp_peak = format_time(highlight['peak_second']) if 'peak_second' in highlight else ""
                
                # 時間表示
                st.markdown(f"**時間**: {timestamp_start} → {timestamp_end} " + 
                           (f"(ピーク: {timestamp_peak})" if timestamp_peak else ""))
                
                # 秒数情報
                st.markdown(f"**秒数**: {highlight['start_second']} → {highlight['end_second']} " +
                           (f"(ピーク: {highlight['peak_second']})" if 'peak_second' in highlight else ""))
                
                # スコア情報（プログレスバーで表示）
                if 'peak_score' in highlight:
                    score = highlight['peak_score']
                    st.markdown(f"**スコア**: {score:.2f}")
                    st.progress(min(score, 1.0))  # スコアが1.0を超える場合に対応
                
                # 理由フラグの表示（JSONBフィールド）
                if 'reason_flags' in highlight and highlight['reason_flags']:
                    try:
                        import json
                        if isinstance(highlight['reason_flags'], str):
                            reason_flags = json.loads(highlight['reason_flags'])
                        else:
                            reason_flags = highlight['reason_flags']
                            
                        # 理由の表示
                        reasons = []
                        for key, value in reason_flags.items():
                            if value:
                                # キー名を読みやすく変換
                                key_display = {
                                    'volume': '音量上昇',
                                    'comment': 'コメント急増',
                                    'emotion': '感情検出',
                                    'keyword': 'キーワード検出',
                                    'manual': '手動設定'
                                }.get(key, key)
                                reasons.append(key_display)
                        
                        if reasons:
                            st.markdown(f"**理由**: {', '.join(reasons)}")
                    except Exception as e:
                        st.markdown(f"**理由**: {str(highlight['reason_flags'])}")
            
            with col2:
                # ジャンプボタン
                st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
                if st.button("▶️", key=f"highlight_{i}_{highlight.get('id', i)}", help=f"{timestamp_start}にジャンプ"):
                    highlight_time = float(highlight['start_second'])
                    print(f"ハイライトボタン{i}がクリックされました: {highlight_time}秒")
                    # 関数呼び出し前にすべてのシーク関連セッション変数をクリア
                    for key in ['_seek_sec', 'sec', '_force_reload']:
                        if key in st.session_state:
                            del st.session_state[key]
                    # seek_to関数を直接呼び出し
                    seek_to(highlight_time)
                    # 即座に再読み込み
                    st.rerun()
            
            # 区切り線
            st.markdown("<hr style='margin: 10px 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
        
        # ページネーションコントロール（ページ数が2以上の場合のみ表示）
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col1:
                if st.button("◀ 前へ", key="prev_highlight_page", disabled=current_page == 0):
                    st.session_state['highlight_page'] = max(0, current_page - 1)
                    st.rerun()
            
            with col2:
                st.markdown(f"<div style='text-align: center;'>ページ {current_page + 1}/{total_pages}</div>", unsafe_allow_html=True)
            
            with col3:
                if st.button("次へ ▶", key="next_highlight_page", disabled=current_page >= total_pages - 1):
                    st.session_state['highlight_page'] = min(total_pages - 1, current_page + 1)
                    st.rerun()
    else:
        st.info("この動画にはハイライトデータがありません。")
