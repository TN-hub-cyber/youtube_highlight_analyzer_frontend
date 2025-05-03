import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events
from utils.formatting import format_time, create_metrics_chart
from utils.data_utils import prepare_metrics_data, find_highlights


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
    # データが空の場合は空のグラフを表示
    if not metrics_data:
        st.warning("メトリクスデータがありません")
        return None
    
    # データをDataFrameに変換
    metrics_df = prepare_metrics_data(metrics_data)
    
    if metrics_df.empty:
        st.warning("メトリクスデータの変換に失敗しました")
        return None
    
    # メトリクスグラフの作成
    fig = create_metrics_chart(metrics_df, current_time, height)
    
    # ハイライトポイントを表示
    if show_highlights:
        highlights = find_highlights(metrics_df)
        if highlights:
            # ハイライトポイントを上位5件に制限
            top_highlights = highlights[:5]
            
            # ハイライトポイントをグラフに追加
            for highlight in top_highlights:
                fig.add_vline(
                    x=highlight['time_seconds'],
                    line_width=1.5,
                    line_dash="dash",
                    line_color="rgba(255, 0, 0, 0.5)",
                )
            
            # ハイライトポイントを表示
            with st.expander("🔍 ハイライトポイント", expanded=False):
                st.markdown("#### 動画内の重要ポイント")
                
                for i, highlight in enumerate(top_highlights):
                    col1, col2, col3 = st.columns([2, 7, 1])
                    
                    with col1:
                        st.markdown(f"**{format_time(highlight['time_seconds'])}**")
                    
                    with col2:
                        score_perc = int(highlight['score'] * 100)
                        comment_count = int(highlight.get('comment_count', 0))
                        st.markdown(f"重要度: {score_perc}% (コメント: {comment_count}件)")
                    
                    with col3:
                        # ユニークなキーを使用してボタン重複を避ける
                        btn_key = f"highlight_btn_{i}_{hash(str(highlight['time_seconds']))}"
                        if st.button(f"▶️ #{i+1}", key=btn_key): 
                            st.session_state['sec'] = highlight['time_seconds']
                            # 即時シーク実行のためJavaScript呼び出しも追加
                            st.markdown(f"""
                            <script>
                            if(typeof player !== 'undefined') {{
                                player.seekTo({highlight['time_seconds']});
                                player.playVideo();
                            }}
                            </script>
                            """, unsafe_allow_html=True)
                            st.rerun()
    
    # クリックイベントの有効・無効を設定
    clicked_sec = None
    if click_enabled:
        # クリックイベントを使用してプロットを表示
        selected_points = plotly_events(fig, click_event=True)
        
        # クリックされた場合は位置を返す
        if selected_points:
            clicked_sec = selected_points[0].get('x')
            
            # シーク命令のためにセッション状態を設定 & JavaScript直接実行
            if clicked_sec is not None:
                # エラーハンドリングを強化
                try:
                    # セッション状態を設定
                    st.session_state['sec'] = clicked_sec
                    
                    # 即時シーク実行のためJavaScript呼び出しも追加
                    st.markdown(f"""
                    <script>
                    console.log("グラフクリック - {clicked_sec}秒にシーク");
                    // グローバルプレイヤーがある場合は直接呼び出し
                    if(typeof player !== 'undefined' && player && typeof player.seekTo === 'function') {{
                        player.seekTo({clicked_sec});
                        player.playVideo();
                    }}
                    // グローバル関数がある場合はそれを呼び出し
                    else if(typeof seekYouTubePlayerTo === 'function') {{
                        seekYouTubePlayerTo({clicked_sec});
                    }}
                    </script>
                    """, unsafe_allow_html=True)
                    
                    # シーク命令送信のために再読み込み
                    st.rerun()
                except Exception as e:
                    st.error(f"シーク処理中にエラーが発生しました: {e}")
    else:
        # 通常のプロットとして表示
        st.plotly_chart(fig, use_container_width=True)
    
    return clicked_sec


# この関数は不要なので削除（上記の修正で直接セッション状態を設定するため）
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
    from utils.formatting import create_multi_term_chart
    
    # データが空の場合やtermsが空の場合は何も表示しない
    if not comment_hist_data or not terms:
        return None
    
    # データをDataFrameに変換
    hist_df = prepare_comment_hist_data(comment_hist_data, terms)
    
    if hist_df.empty:
        return None
    
    # グラフの作成
    fig = create_multi_term_chart(hist_df, terms, current_time, height)
    
    # クリックイベントを使用してプロットを表示
    selected_points = plotly_events(fig, click_event=True)
    
    # クリックされた場合は位置を返す
    if selected_points:
        clicked_sec = selected_points[0].get('x')
        if clicked_sec is not None:
            # 直接セッション状態を設定してリランする
            st.session_state['sec'] = clicked_sec
            st.rerun()
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
    from utils.formatting import create_emotion_chart
    
    # データが空の場合は何も表示しない
    if not emotion_data:
        return None
    
    # データをDataFrameに変換
    emotion_df = prepare_emotion_data(emotion_data)
    
    if emotion_df.empty:
        return None
    
    # グラフの作成
    fig = create_emotion_chart(emotion_df, current_time, height)
    
    # クリックイベントを使用してプロットを表示
    selected_points = plotly_events(fig, click_event=True)
    
    # クリックされた場合は位置を返す
    if selected_points:
        clicked_sec = selected_points[0].get('x')
        if clicked_sec is not None:
            # 直接セッション状態を設定してリランする
            st.session_state['sec'] = clicked_sec
            st.rerun()
        return clicked_sec
    
    return None
