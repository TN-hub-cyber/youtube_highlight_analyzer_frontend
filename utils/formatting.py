import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta


def format_time(seconds):
    """
    秒数を時:分:秒または分:秒形式に変換する
    
    Args:
        seconds: 秒数（整数または浮動小数点）
        
    Returns:
        フォーマットされた時間文字列
    """
    if seconds is None:
        return "00:00"
    
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


def format_time_delta(seconds):
    """
    秒数をtimedelta形式に変換する
    
    Args:
        seconds: 秒数（整数または浮動小数点）
        
    Returns:
        timedelta型のオブジェクト
    """
    if seconds is None:
        return timedelta(seconds=0)
    
    return timedelta(seconds=int(seconds))


def create_metrics_chart(metrics_df, selected_time=None, height=300):
    """
    メトリクスデータのグラフを作成する
    
    Args:
        metrics_df: メトリクスデータのDataFrame
        selected_time: 現在選択されている時間（秒）
        height: グラフの高さ
        
    Returns:
        Plotlyグラフオブジェクト
    """
    if metrics_df.empty:
        # 空のグラフを返す
        return go.Figure()
    
    # 2つのY軸を持つグラフを作成
    fig = go.Figure()
    
    # コメント数の追加
    if 'comment_count' in metrics_df.columns:
        fig.add_trace(go.Scatter(
            x=metrics_df['time_seconds'],
            y=metrics_df['comment_count'],
            mode='lines',
            name='コメント数',
            line=dict(color='#1E88E5', width=2),
            hovertemplate='時間: %{x}秒<br>コメント数: %{y}<extra></extra>'
        ))
    
    # 音量スコアの追加（セカンダリY軸）
    if 'volume_score' in metrics_df.columns:
        fig.add_trace(go.Scatter(
            x=metrics_df['time_seconds'],
            y=metrics_df['volume_score'],
            mode='lines',
            name='音量',
            line=dict(color='#FFC107', width=2, dash='dot'),
            yaxis='y2',
            hovertemplate='時間: %{x}秒<br>音量スコア: %{y:.2f}<extra></extra>'
        ))
    
    # 現在の再生位置マーカーを追加
    if selected_time is not None:
        try:
            # 数値型かどうか確認
            x_value = float(selected_time) if selected_time is not None else None
            if x_value is not None:
                fig.add_vline(
                    x=x_value,
                    line_width=2,
                    line_dash="solid",
                    line_color="red",
                    annotation_text="現在位置",
                    annotation_position="top"
                )
        except (TypeError, ValueError):
            # 型変換できない場合は垂直線を追加しない
            print(f"警告: 再生位置の型が不正です: {type(selected_time)}")
    
    # レイアウト設定
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        xaxis=dict(
            title="時間（秒）",
            gridcolor='lightgray',
            zeroline=False,
            tickformat=',d',
            tickmode='auto',
            dtick=300,  # 5分ごとのティック
        ),
        yaxis=dict(
            title="コメント数",
            gridcolor='lightgray',
            zeroline=False,
            side='left'
        ),
        yaxis2=dict(
            title="音量スコア",
            gridcolor='lightgray',
            zeroline=False,
            overlaying='y',
            side='right'
        ),
    )
    
    # X軸のラベルを時:分:秒形式に変換（表示数を制限して見やすく）
    # 動画の長さに応じて適切な間隔でティックを生成
    max_time = metrics_df['time_seconds'].max()
    time_span = max_time - metrics_df['time_seconds'].min()
    
    # 動画の長さに応じてティックの間隔を調整
    if time_span > 3600:  # 1時間以上
        tick_interval = 600  # 10分間隔
    elif time_span > 1800:  # 30分以上
        tick_interval = 300  # 5分間隔
    elif time_span > 600:  # 10分以上
        tick_interval = 120  # 2分間隔
    else:
        tick_interval = 60   # 1分間隔
    
    # 均等な間隔でティック位置を生成
    tick_positions = list(range(0, int(max_time) + tick_interval, tick_interval))
    
    fig.update_xaxes(
        tickvals=tick_positions,
        ticktext=[format_time(t) for t in tick_positions],
        tickangle=0,  # ラベルを水平に保つ
        tickfont=dict(size=10)  # フォントサイズを小さくして重なりを防ぐ
    )
    
    return fig


def create_multi_term_chart(comment_hist_df, terms, selected_time=None, height=300):
    """
    複数検索語のコメント頻度グラフを作成する
    
    Args:
        comment_hist_df: コメント頻度データのDataFrame
        terms: 検索語リスト
        selected_time: 現在選択されている時間（秒）
        height: グラフの高さ
        
    Returns:
        Plotlyグラフオブジェクト
    """
    if comment_hist_df.empty or not terms:
        # 空のグラフを返す
        return go.Figure()
    
    # グラフを作成
    fig = go.Figure()
    
    # 各検索語のトレースを追加
    colors = ['#1E88E5', '#FFC107', '#4CAF50', '#F44336', '#9C27B0', '#FF9800', '#607D8B', '#00BCD4']
    
    for i, term in enumerate(terms):
        term_col = f"term_{i}"
        if term_col in comment_hist_df.columns:
            color = colors[i % len(colors)]  # 色を循環使用
            
            fig.add_trace(go.Scatter(
                x=comment_hist_df['time_seconds'],
                y=comment_hist_df[term_col],
                mode='lines',
                name=term,
                line=dict(color=color, width=2),
                hovertemplate=f'時間: %{{x}}秒<br>{term}: %{{y}}<extra></extra>'
            ))
    
    # 現在の再生位置マーカーを追加
    if selected_time is not None:
        try:
            # 数値型かどうか確認
            x_value = float(selected_time) if selected_time is not None else None
            if x_value is not None:
                fig.add_vline(
                    x=x_value,
                    line_width=2,
                    line_dash="solid",
                    line_color="red",
                    annotation_text="現在位置",
                    annotation_position="top"
                )
        except (TypeError, ValueError):
            # 型変換できない場合は垂直線を追加しない
            print(f"警告: 再生位置の型が不正です: {type(selected_time)}")
    
    # レイアウト設定
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        xaxis=dict(
            title="時間（秒）",
            gridcolor='lightgray',
            zeroline=False,
            tickformat=',d',
            tickmode='auto',
            dtick=300,  # 5分ごとのティック
        ),
        yaxis=dict(
            title="出現回数",
            gridcolor='lightgray',
            zeroline=False,
        ),
    )
    
    # X軸のラベルを時:分:秒形式に変換（表示数を制限して見やすく）
    # 動画の長さに応じて適切な間隔でティックを生成
    max_time = comment_hist_df['time_seconds'].max()
    time_span = max_time - comment_hist_df['time_seconds'].min()
    
    # 動画の長さに応じてティックの間隔を調整
    if time_span > 3600:  # 1時間以上
        tick_interval = 600  # 10分間隔
    elif time_span > 1800:  # 30分以上
        tick_interval = 300  # 5分間隔
    elif time_span > 600:  # 10分以上
        tick_interval = 120  # 2分間隔
    else:
        tick_interval = 60   # 1分間隔
    
    # 均等な間隔でティック位置を生成
    tick_positions = list(range(0, int(max_time) + tick_interval, tick_interval))
    
    fig.update_xaxes(
        tickvals=tick_positions,
        ticktext=[format_time(t) for t in tick_positions],
        tickangle=0,  # ラベルを水平に保つ
        tickfont=dict(size=10)  # フォントサイズを小さくして重なりを防ぐ
    )
    
    return fig


def create_emotion_chart(emotion_df, selected_time=None, height=300):
    """
    感情分析データのグラフを作成する
    
    Args:
        emotion_df: 感情分析データのDataFrame
        selected_time: 現在選択されている時間（秒）
        height: グラフの高さ
        
    Returns:
        Plotlyグラフオブジェクト
    """
    if emotion_df.empty:
        # 空のグラフを返す
        return go.Figure()
    
    # 感情の種類を取得
    emotion_types = [col for col in emotion_df.columns if col != 'time_seconds']
    
    # 感情の色マッピング
    emotion_colors = {
        'happy': '#4CAF50',      # 緑
        'sad': '#2196F3',        # 青
        'angry': '#F44336',      # 赤
        'surprise': '#FFC107',   # 黄
        'fear': '#9C27B0',       # 紫
        'disgust': '#795548',    # 茶
        'neutral': '#607D8B',    # グレー
    }
    
    # デフォルトの色
    default_colors = ['#1E88E5', '#FFC107', '#4CAF50', '#F44336', '#9C27B0', '#FF9800', '#607D8B', '#00BCD4']
    
    # グラフを作成
    fig = go.Figure()
    
    # 各感情タイプのトレースを追加
    for i, emotion_type in enumerate(emotion_types):
        # 感情タイプに対応する色を取得（マッピングになければデフォルト色を使用）
        color = emotion_colors.get(emotion_type.lower(), default_colors[i % len(default_colors)])
        
        fig.add_trace(go.Scatter(
            x=emotion_df['time_seconds'],
            y=emotion_df[emotion_type],
            mode='lines',
            name=emotion_type,
            line=dict(color=color, width=2),
            hovertemplate=f'時間: %{{x}}秒<br>{emotion_type}: %{{y:.2f}}<extra></extra>'
        ))
    
    # 現在の再生位置マーカーを追加
    if selected_time is not None:
        try:
            # 数値型かどうか確認
            x_value = float(selected_time) if selected_time is not None else None
            if x_value is not None:
                fig.add_vline(
                    x=x_value,
                    line_width=2,
                    line_dash="solid",
                    line_color="red",
                    annotation_text="現在位置",
                    annotation_position="top"
                )
        except (TypeError, ValueError):
            # 型変換できない場合は垂直線を追加しない
            print(f"警告: 再生位置の型が不正です: {type(selected_time)}")
    
    # レイアウト設定
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        xaxis=dict(
            title="時間（秒）",
            gridcolor='lightgray',
            zeroline=False,
            tickformat=',d',
            tickmode='auto',
            dtick=300,  # 5分ごとのティック
        ),
        yaxis=dict(
            title="感情スコア",
            gridcolor='lightgray',
            zeroline=False,
            range=[0, 1],  # 正規化されたスコアの範囲
        ),
    )
    
    # X軸のラベルを時:分:秒形式に変換（表示数を制限して見やすく）
    # 動画の長さに応じて適切な間隔でティックを生成
    max_time = emotion_df['time_seconds'].max()
    time_span = max_time - emotion_df['time_seconds'].min()
    
    # 動画の長さに応じてティックの間隔を調整
    if time_span > 3600:  # 1時間以上
        tick_interval = 600  # 10分間隔
    elif time_span > 1800:  # 30分以上
        tick_interval = 300  # 5分間隔
    elif time_span > 600:  # 10分以上
        tick_interval = 120  # 2分間隔
    else:
        tick_interval = 60   # 1分間隔
    
    # 均等な間隔でティック位置を生成
    tick_positions = list(range(0, int(max_time) + tick_interval, tick_interval))
    
    fig.update_xaxes(
        tickvals=tick_positions,
        ticktext=[format_time(t) for t in tick_positions],
        tickangle=0,  # ラベルを水平に保つ
        tickfont=dict(size=10)  # フォントサイズを小さくして重なりを防ぐ
    )
    
    return fig
