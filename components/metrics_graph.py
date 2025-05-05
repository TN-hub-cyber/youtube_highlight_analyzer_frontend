import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from streamlit_plotly_events import plotly_events
from utils.formatting import format_time # create_metrics_chart は削除
# prepare_metrics_data は削除し、新しい関数をインポート
from utils.data_utils import find_highlights, load_and_prepare_secondly_metrics


def display_metrics_graph(metrics_data, current_time=None, height=300, click_enabled=True, show_highlights=True):
    """
    メトリクスグラフ（音量とコメント頻度）を表示する
    
    Args:
        metrics_data: Supabaseから取得したメトリクスデータ
        current_time: 現在の再生位置（秒）
        height: グラフの高さ
        click_enabled: クリックイベントを有効にするかどうか
        show_highlights: ハイライトを表示するかどうか
        
    Returns:
        クリックされた位置（秒）または None
    """
    # セッション状態から動画IDを取得
    video_id = st.session_state.get('vid', None)
    if not video_id:
        st.warning("動画IDが選択されていません。")
        return None

    # --- データ取得と準備 ---
    # データ粒度選択 (固定リストに変更)
    granularity_options = [10, 30, 60] # 1秒はデータ量が多すぎる可能性があるため除外、10秒をデフォルトに
    granularity_labels = {g: f"{g}秒" for g in granularity_options}
    selected_granularity_label = st.selectbox(
        "データ粒度",
        options=list(granularity_labels.values()),
        index=granularity_options.index(st.session_state.get('metrics_granularity', 10)), # デフォルト10秒
        key='metrics_granularity_selectbox',
        help="グラフデータを集計する時間間隔を選択します。短いほど詳細ですが、表示が重くなる場合があります。"
    )
    # ラベルから実際の粒度（秒数）を取得
    granularity = [g for g, label in granularity_labels.items() if label == selected_granularity_label][0]

    # セッション状態に保存
    if granularity != st.session_state.get('metrics_granularity', 10):
        st.session_state['metrics_granularity'] = granularity
        # 粒度変更時はキャッシュをクリアするために再実行
        st.rerun()

    # 新しい関数でデータを取得・準備
    metrics_df = load_and_prepare_secondly_metrics(video_id, granularity)

    if metrics_df.empty:
        st.warning("メトリクスデータの取得または処理に失敗しました。")
        return None

    # --- メトリクス選択UI ---
    default_metrics = ['comment_cnt', 'norm_mean'] # コメント数と正規化音量をデフォルトに
    if 'selected_metrics' not in st.session_state:
        st.session_state['selected_metrics'] = default_metrics

    with st.expander("メトリクス表示設定", expanded=False):
        st.write("表示するメトリクスを選択")
        selected_metrics_ui = []

        # 利用可能なメトリクス（新しいRPCに基づく）
        available_metrics = {
            'comment_cnt': "コメント数",
            'norm_mean': "正規化音量 ⭐",
            'inter_mean_delta': "音量変化率（前秒比）",
            'dynamic_range': "音量振れ幅",
            'is_peak': "盛り上がりポイント",
            'is_silent': "無音区間"
        }
        help_text = {
            'comment_cnt': "指定した粒度でのコメント総数",
            'norm_mean': "0-1に正規化された平均音量（**推奨**） - 動画中の盛り上がりを検出するのに最適",
            'inter_mean_delta': "前秒比の平均音量変化率 - 音量の急激な変化を検出",
            'dynamic_range': "同一秒内の音量振れ幅 - 音声の強弱やダイナミクスを検出",
            'is_peak': "アルゴリズムが検出した重要な瞬間 (1=Peak)",
            'is_silent': "無音または非常に静かな部分 (1=Silent)"
        }

        # チェックボックス生成
        cols = st.columns(3)
        col_idx = 0
        for key, label in available_metrics.items():
            with cols[col_idx % 3]:
                is_checked = st.checkbox(
                    label,
                    value=(key in st.session_state['selected_metrics']),
                    key=f"cb_{key}",
                    help=help_text.get(key, ""),
                    disabled=(key == 'comment_cnt') # コメント数は常に表示
                )
                if is_checked:
                    selected_metrics_ui.append(key)
            col_idx += 1

        # 選択が変更されたか確認
        if set(selected_metrics_ui) != set(st.session_state['selected_metrics']):
            current_position = st.session_state.get('sec', None)
            st.session_state['selected_metrics'] = selected_metrics_ui
            if current_position is not None:
                st.session_state['_persist_position'] = current_position
            st.rerun()

    # --- グラフ作成 ---
    selected_metrics_display = st.session_state['selected_metrics']
    numeric_metrics = [m for m in selected_metrics_display if m in ['norm_mean', 'inter_mean_delta', 'dynamic_range']]
    flag_metrics = [m for m in selected_metrics_display if m in ['is_peak', 'is_silent']]

    # 2軸グラフを作成
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. 数値メトリクスを左Y軸に線グラフで追加
    colors = px.colors.qualitative.Plotly
    for i, metric in enumerate(numeric_metrics):
        if metric in metrics_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=metrics_df['time_seconds'],
                    y=metrics_df[metric],
                    mode='lines',
                    name=available_metrics.get(metric, metric),
                    line=dict(color=colors[i % len(colors)], width=(3 if metric == 'norm_mean' else 1.5)), # norm_meanを太く
                    yaxis='y1'
                ),
                secondary_y=False,
            )

    # 2. コメント数を右Y軸に棒グラフで追加 (常に表示)
    if 'comment_cnt' in metrics_df.columns:
         fig.add_trace(
             go.Bar(
                 x=metrics_df['time_seconds'],
                 y=metrics_df['comment_cnt'],
                 name=available_metrics['comment_cnt'],
                 marker_color='rgba(150, 150, 150, 0.6)',
                 yaxis='y2'
             ),
             secondary_y=True,
         )

    # 3. フラグメトリクスを右Y軸に散布図で追加
    flag_symbols = {'is_peak': 'star', 'is_silent': 'circle-open'}
    flag_colors = {'is_peak': 'red', 'is_silent': 'blue'}
    flag_y_offset = {'is_peak': 0.95, 'is_silent': 0.05} # Y軸の上端/下端にプロット

    max_comment_cnt = metrics_df['comment_cnt'].max() if 'comment_cnt' in metrics_df.columns and not metrics_df['comment_cnt'].empty else 1
    y2_range_max = max(1, max_comment_cnt * 1.1) # コメント数の最大値に基づいて右Y軸の範囲を設定

    for metric in flag_metrics:
        if metric in metrics_df.columns:
            points = metrics_df[metrics_df[metric] == 1]
            if not points.empty:
                 # Y座標をコメント数軸の上端/下端に設定
                 y_values = [y2_range_max * flag_y_offset[metric]] * len(points)
                 fig.add_trace(
                     go.Scatter(
                         x=points['time_seconds'],
                         y=y_values,
                         mode='markers',
                         name=available_metrics.get(metric, metric),
                         marker=dict(
                             symbol=flag_symbols.get(metric, 'circle'),
                             color=flag_colors.get(metric, 'black'),
                             size=8
                         ),
                         yaxis='y2' # 右Y軸を使用
                     ),
                     secondary_y=True,
                 )

    # 4. 現在時間の垂直線を追加
    if current_time is not None:
        fig.add_vline(
            x=current_time,
            line_width=1,
            line_dash="solid",
            line_color="red",
            annotation_text="Current",
            annotation_position="top right"
        )

    # グラフのレイアウト設定
    fig.update_layout(
        height=height,
        xaxis_title="Time (seconds)",
        yaxis_title="Metric Value",
        yaxis2_title="Comment Count / Flags",
        legend_title="Metrics",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(range=[0, 1.05]), # 左Y軸の範囲を0-1に固定（正規化指標のため）
        yaxis2=dict(range=[0, y2_range_max]), # 右Y軸の範囲を設定
        # legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1) # 凡例を上部に
    )
    # X軸の範囲をデータの最小・最大に合わせる
    if not metrics_df.empty:
        fig.update_xaxes(range=[metrics_df['time_seconds'].min(), metrics_df['time_seconds'].max()])


    # --- ハイライト表示 ---
    if show_highlights:
        # find_highlightsがvolume_scoreではなくnorm_meanを使うように修正が必要
        # 一旦、norm_meanとcomment_cntで計算するように仮定して呼び出す
        highlights = find_highlights(metrics_df) # find_highlightsの修正が必要
        if highlights:
            top_highlights = highlights[:5]
            for highlight in top_highlights:
                fig.add_vline(
                    x=highlight['time_seconds'],
                    line_width=1.5,
                    line_dash="dash",
                    line_color="rgba(255, 165, 0, 0.7)", # オレンジ色に変更
                    annotation_text=f"Highlight ({int(highlight['score'] * 100)}%)",
                    annotation_position="top left",
                    annotation_font_size=10
                )

            with st.expander("🔍 ハイライトポイント", expanded=False):
                st.markdown("#### 動画内の重要ポイント (上位5件)")
                for i, highlight in enumerate(top_highlights):
                    col1, col2, col3 = st.columns([2, 7, 1])
                    with col1:
                        st.markdown(f"**{format_time(highlight['time_seconds'])}**")
                    with col2:
                        score_perc = int(highlight['score'] * 100)
                        comment_count = int(highlight.get('comment_cnt', 0)) # 'comment_cnt' を使用
                        norm_mean_val = highlight.get('norm_mean', 0) # 'norm_mean' を使用
                        st.markdown(f"重要度: {score_perc}% (コメント: {comment_count}, 音量: {norm_mean_val:.2f})")
                    with col3:
                        btn_key = f"highlight_btn_{i}_{hash(str(highlight['time_seconds']))}"
                        if st.button(f"▶️ #{i+1}", key=btn_key):
                            from components.youtube_player import seek_to
                            seek_to(highlight['time_seconds'], source_id=f"highlight_btn_{i}")
                            st.rerun()

    # --- クリックイベント処理 ---
    clicked_sec = None
    plot_key = "metrics_graph_events" 
    if click_enabled:
        # plotly_events には use_container_width は不要
        selected_points = plotly_events(fig, click_event=True, key=plot_key) 
        if selected_points:
            clicked_sec = selected_points[0].get('x')
            if clicked_sec is not None:
                # 連続クリック防止
                if 'last_clicked_sec' not in st.session_state or st.session_state['last_clicked_sec'] != clicked_sec:
                    try:
                        st.session_state['last_clicked_sec'] = clicked_sec
                        from components.youtube_player import seek_to
                        seek_to(clicked_sec, source_id="metrics_graph")
                        st.rerun()
                    except Exception as e:
                        st.error(f"シーク処理中にエラーが発生しました: {e}")
                # else:
                #     print(f"同じ位置の連続クリック検出: {clicked_sec}秒 - 処理をスキップ") # デバッグ用
    else:
        # クリック無効の場合も use_container_width=True を設定
        st.plotly_chart(fig, use_container_width=True) 

    return clicked_sec


# seek_to_position 関数は不要なので削除
# def seek_to_position(position_seconds):
#     """
#     指定位置にシークするためのセッション状態をセット
#     
#     Args:
#         position_seconds: シーク先の位置（秒）
#     """
#     if position_seconds is not None:
#         st.session_state['sec'] = position_seconds


def display_search_graph(comment_hist_data, terms, current_time=None, height=250):
    """
    検索語のコメント頻度グラフを表示する
    
    Args:
        comment_hist_data: コメント頻度集計データ
        terms: 検索語リスト
        current_time: 現在の再生位置（秒）
        height: グラフの高さ
        
    Returns:
        クリックされた位置（秒）または None
    """
    from utils.data_utils import prepare_comment_hist_data
    from utils.formatting import create_multi_term_chart # これはまだ使う

    # データが空の場合やtermsが空の場合は何も表示しない
    if not comment_hist_data or not terms:
        # st.write("コメント頻度データがありません") # デバッグ用
        return None

    # データをDataFrameに変換
    hist_df = prepare_comment_hist_data(comment_hist_data, terms)

    if hist_df.empty:
        # st.write("コメント頻度データの準備に失敗しました") # デバッグ用
        return None

    # グラフの作成
    try:
        fig = create_multi_term_chart(hist_df, terms, current_time, height)
    except Exception as e:
        st.error(f"コメント頻度グラフの作成中にエラー: {e}")
        return None

    # クリックイベントを使用してプロットを表示 (plotly_events から use_container_width を削除)
    selected_points = plotly_events(fig, click_event=True, key="search_graph_events") # 一意のキーを追加
    
    # クリックされた場合は位置を返す
    if selected_points:
        clicked_sec = selected_points[0].get('x')
        if clicked_sec is not None:
            # 直前のクリックと同じなら処理しない（ループ防止）
            search_last_click_key = 'last_clicked_sec_search'
            if search_last_click_key in st.session_state and st.session_state[search_last_click_key] == clicked_sec:
                # 同じ位置の連続クリックを検出 - 何もしない
                print(f"検索グラフ: 同じ位置の連続クリック検出: {clicked_sec}秒 - 処理をスキップ")
            else:
                try:
                    # 直前のクリック位置を記録
                    st.session_state[search_last_click_key] = clicked_sec
                    
                    # 現在の再生位置を保持
                    current_position = st.session_state.get('sec', None)
                    
                    # youtube_player.pyのseek_to関数を使用、発生源情報を明示的に渡す
                    from components.youtube_player import seek_to
                    seek_to(clicked_sec, source_id="search_graph")
                    
                    # 再生位置を保持したまま再読み込み
                    if current_position is not None:
                        st.session_state['_persist_position'] = current_position
                    
                    # シーク命令送信のために再読み込み
                    st.rerun()
                except Exception as e:
                    st.error(f"検索グラフのシーク処理中にエラーが発生しました: {e}")
        return clicked_sec
    
    return None


def display_emotion_graph(emotion_data, current_time=None, height=250):
    """
    感情分析グラフを表示する
    
    Args:
        emotion_data: 感情分析データ
        current_time: 現在の再生位置（秒）
        height: グラフの高さ
        
    Returns:
        クリックされた位置（秒）または None
    """
    from utils.data_utils import prepare_emotion_data
    from utils.formatting import create_emotion_chart # これはまだ使う

    # データが空の場合は何も表示しない
    if not emotion_data:
        # st.write("感情分析データがありません") # デバッグ用
        return None

    # データをDataFrameに変換
    emotion_df = prepare_emotion_data(emotion_data)

    if emotion_df.empty:
        # st.write("感情分析データの準備に失敗しました") # デバッグ用
        return None

    # グラフの作成
    try:
        fig = create_emotion_chart(emotion_df, current_time, height)
    except Exception as e:
        st.error(f"感情分析グラフの作成中にエラー: {e}")
        return None

    # クリックイベントを使用してプロットを表示 (plotly_events から use_container_width を削除)
    selected_points = plotly_events(fig, click_event=True, key="emotion_graph_events") # 一意のキーを追加
    
    # クリックされた場合は位置を返す
    if selected_points:
        clicked_sec = selected_points[0].get('x')
        if clicked_sec is not None:
            # 直前のクリックと同じなら処理しない（ループ防止）
            emotion_last_click_key = 'last_clicked_sec_emotion'
            if emotion_last_click_key in st.session_state and st.session_state[emotion_last_click_key] == clicked_sec:
                # 同じ位置の連続クリックを検出 - 何もしない
                print(f"感情グラフ: 同じ位置の連続クリック検出: {clicked_sec}秒 - 処理をスキップ")
            else:
                try:
                    # 直前のクリック位置を記録
                    st.session_state[emotion_last_click_key] = clicked_sec
                    
                    # 現在の再生位置を保持
                    current_position = st.session_state.get('sec', None)
                    
                    # youtube_player.pyのseek_to関数を使用、発生源情報を明示的に渡す
                    from components.youtube_player import seek_to
                    seek_to(clicked_sec, source_id="emotion_graph")
                    
                    # 再生位置を保持したまま再読み込み
                    if current_position is not None:
                        st.session_state['_persist_position'] = current_position
                    
                    # シーク命令送信のために再読み込み
                    st.rerun()
                except Exception as e:
                    st.error(f"感情グラフのシーク処理中にエラーが発生しました: {e}")
        return clicked_sec
    
    return None
