import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
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


def create_metrics_chart(metrics_df, selected_time=None, height=300, selected_metrics=None):
    """
    メトリクスデータのグラフを作成する
    
    Args:
        metrics_df: メトリクスデータのDataFrame
        selected_time: 現在選択されている時間（秒）
        height: グラフの高さ
        selected_metrics: 表示する指標のリスト（デフォルトではすべて表示）
        
    Returns:
        Plotlyグラフオブジェクト
    """
    if metrics_df.empty:
        # 空のグラフを返す
        return go.Figure()
    
    # 初期処理: DataFrame全体に対する正しい型変換を実施
    # 型ミスマッチ問題を解決するために最初に適切な型を強制
    numeric_cols = ['norm_mean', 'inter_mean_delta', 'dynamic_range', 'volume_score', 'is_peak', 'is_silent']

    # time_seconds型変換を強化 - BIGINT (int64)に明示的に変換し、
    # 大きな値（32ビット整数範囲を超えるもの）の問題を防止
    if 'time_seconds' in metrics_df.columns:
        # 入力の型をチェックし、float型の場合は一度floatとして読み込み
        if metrics_df['time_seconds'].dtype.kind == 'f':
            metrics_df['time_seconds'] = metrics_df['time_seconds'].fillna(0).astype('float64')
        metrics_df['time_seconds'] = metrics_df['time_seconds'].astype('int64')
        
        # 1000秒以上の時間範囲のチェック - ビジュアルだけでなくデータレベルで確認
        high_ts_count = (metrics_df['time_seconds'] >= 1000).sum()
        if high_ts_count > 0:
            print(f"1000秒以上のデータポイント：{high_ts_count}個")
            # ランダムなサンプルだけでなく最大値も確認
            print(f"最大time_seconds値：{metrics_df['time_seconds'].max()}")
    
    # 数値列を浮動小数点数に統一して型の不一致を防止
    for col in numeric_cols:
        if col in metrics_df.columns:
            # まず既存のNaN値を検出して保存
            null_mask = metrics_df[col].isna()
            # 列全体をfloat64型に変換（データタイプの種類に応じて処理）
            if metrics_df[col].dtype.kind in 'iuf':  # 整数、符号なし整数、浮動小数点
                metrics_df[col] = metrics_df[col].astype('float64')
            # そのほかのデータ型はまずオブジェクト→float変換を試みる
            else:
                try:
                    metrics_df[col] = pd.to_numeric(metrics_df[col], errors='coerce').astype('float64')
                except:
                    st.warning(f"列 {col} の型変換に失敗しました: {metrics_df[col].dtype}")
                    
            # NaN値を維持（変換で0に置き換わることを防止）
            metrics_df.loc[null_mask, col] = np.nan
    
    # 詳細なデバッグ情報：データの型と欠損値の確認 + 値分布の追加チェック
    print(f"メトリクスデータ型: {metrics_df.dtypes.to_dict()}")
    print(f"欠損値の数: {metrics_df.isna().sum().to_dict()}")
    
    # 値の分布をチェック - 特に大きな時間値の周囲で問題がないか
    if 'time_seconds' in metrics_df.columns and len(metrics_df) > 0:
        time_bins = [0, 500, 900, 1000, 1100, 1500, metrics_df['time_seconds'].max() + 1]
        time_dist = pd.cut(metrics_df['time_seconds'], bins=time_bins).value_counts().sort_index()
        print(f"時間分布: {time_dist.to_dict()}")
        
        # 1000秒付近のデータの値を具体的にチェック
        problem_range = (metrics_df['time_seconds'] >= 950) & (metrics_df['time_seconds'] <= 1050)
        if problem_range.any():
            problem_sample = metrics_df.loc[problem_range, ['time_seconds'] + [col for col in numeric_cols if col in metrics_df.columns]].head(5)
            print(f"1000秒付近のサンプル:\n{problem_sample.to_dict('records')}")
        
    # 表示用に選択された列だけをクリーニングする（効率化のため）
    for column in selected_metrics:
        if column in metrics_df.columns and column not in ['time_seconds', 'time_bucket']:
            # 浮動小数点に変換したので型チェックは不要に
                # 指標ごとに最適化したクリーニングを適用
                if column == 'norm_mean':
                    # 正規化された平均音量の処理
                    # 値が0-1の範囲にあるべきなので、クリッピングを適用
                    metrics_df[column] = metrics_df[column].clip(0, 1)
                    
                    # 欠損値の補間 - 0埋めせず、補間のみで対応（最後に細かいチェック）
                    metrics_df[column] = metrics_df[column].interpolate(method='linear')
                    metrics_df[column] = metrics_df[column].bfill()  # 先頭のNaN処理
                    metrics_df[column] = metrics_df[column].ffill()  # 末尾のNaN処理
                    
                    # 補間後もNaNが残っているか確認
                    nan_count = metrics_df[column].isna().sum()
                    if nan_count > 0:
                        print(f"{column}列に補間後も{nan_count}個のNaNが残っています")
                    
                # 大きな時間ギャップを検出して処理（平坦化を防止）
                time_diff = metrics_df['time_seconds'].diff()
                large_gaps = time_diff > 300  # 5分以上のギャップを検出
                
                if large_gaps.any():
                    print(f"大きな時間ギャップを{large_gaps.sum()}個検出しました - NaN処理適用")
                    # ギャップの前後に特別処理を適用（平坦な線を防ぐため）
                    for idx in metrics_df.index[large_gaps]:
                        if idx > 0:
                            # ギャップ後の値をNaNに設定して補間を防止
                            metrics_df.loc[idx, column] = np.nan
                
                # 問題がよく起こる1000秒付近の処理を改善
                problem_range_mask = (metrics_df['time_seconds'] >= 950) & (metrics_df['time_seconds'] <= 1200)
                if problem_range_mask.any():
                    # より広いウィンドウでのデータ平滑化
                    range_data = metrics_df.loc[problem_range_mask, column].copy()
                    
                    # 欠損値を検出
                    null_mask = range_data.isna()
                    non_null_count = (~null_mask).sum()
                    
                    # 十分なデータがある場合のみ平滑化を適用
                    if non_null_count > 3:
                        # まず欠損値を内挿補間（linear）
                        range_data = range_data.interpolate(method='linear')
                        
                        # 平滑化パラメータを調整（ウィンドウサイズを小さく）
                        smoothed_data = range_data.rolling(window=5, center=True, min_periods=1).mean()
                        
                        # 外れ値検出閾値を微調整 - より保守的な閾値に
                        std_val = range_data.std()
                        if not pd.isna(std_val) and std_val > 0:
                            # 4σを超える変化を外れ値と判定（より保守的に）
                            diff_threshold = 4 * std_val
                            diff_mask = (range_data - smoothed_data).abs() > diff_threshold
                            # 外れ値のみ平滑化値に置き換え
                            metrics_df.loc[problem_range_mask & diff_mask, column] = smoothed_data[diff_mask].astype('float64')
                        else:
                            # 標準偏差が計算できない場合は固定閾値（閾値を上げて保守的に）
                            diff_mask = (range_data - smoothed_data).abs() > 0.1
                            # 外れ値のみ平滑化値に置き換え
                            metrics_df.loc[problem_range_mask & diff_mask, column] = smoothed_data[diff_mask].astype('float64')
                    
                    # データ型の互換性を確保
                    if metrics_df[column].dtype != 'float64':
                        metrics_df[column] = metrics_df[column].astype('float64')
                    
                    # 二重平滑化を行わないよう修正 - ここが平坦化の主要原因
                    
                elif column == 'dynamic_range':
                    # 音量振れ幅の処理
                    # 異常値（極端に大きい値）を処理
                    q99 = metrics_df[column].quantile(0.99)
                    metrics_df.loc[metrics_df[column] > q99, column] = q99
                    
                    # 欠損値の補間 - 0埋めせず、補間のみで対応
                    metrics_df[column] = metrics_df[column].interpolate(method='linear')
                    metrics_df[column] = metrics_df[column].bfill()  # 先頭のNaN処理
                    metrics_df[column] = metrics_df[column].ffill()  # 末尾のNaN処理
                    
                    # 補間後もNaNが残っているか確認
                    nan_count = metrics_df[column].isna().sum()
                    if nan_count > 0:
                        print(f"{column}列に補間後も{nan_count}個のNaNが残っています")
                    
                elif column == 'inter_mean_delta':
                    # 前秒比の差分系指標の処理
                    # 平均と標準偏差を使用した外れ値処理
                    mean_val = metrics_df[column].mean()
                    std_val = metrics_df[column].std()
                    
                    if not pd.isna(mean_val) and not pd.isna(std_val) and std_val > 0:
                        # より緩やかな外れ値処理（4σ）
                        upper_limit = mean_val + 4 * std_val
                        lower_limit = mean_val - 4 * std_val
                        metrics_df.loc[metrics_df[column] > upper_limit, column] = upper_limit
                        metrics_df.loc[metrics_df[column] < lower_limit, column] = lower_limit
                    
                    # 欠損値の補間
                    metrics_df[column] = metrics_df[column].interpolate(method='linear')
                    metrics_df[column] = metrics_df[column].ffill().bfill()
                    metrics_df[column] = metrics_df[column].fillna(0)
                    
                    # 1000秒付近の特別処理 - 対象範囲を拡大
                    problem_range_mask = (metrics_df['time_seconds'] >= 950) & (metrics_df['time_seconds'] <= 1200)
                    if problem_range_mask.any():
                        # データの連続性をまず確保
                        if metrics_df.loc[problem_range_mask, column].isna().sum() > 0:
                            metrics_df.loc[problem_range_mask, column] = metrics_df.loc[problem_range_mask, column].interpolate(method='linear')
                        
                        # より強力なスムージングを適用（一貫性がとれたデータに対して）
                        # 明示的にfloat64型に変換してから代入
                        smoothed_data = metrics_df.loc[problem_range_mask, column].rolling(window=7, center=True, min_periods=1).mean()
                        metrics_df.loc[problem_range_mask, column] = smoothed_data.astype('float64')
                    
                elif column == 'is_peak':
                    # ピーク検出指標はバイナリ（0か1）であるべきなのでクリッピング
                    metrics_df[column] = metrics_df[column].clip(0, 1)
                    # 欠損値は0（ピークでない）で埋める
                    metrics_df[column] = metrics_df[column].fillna(0)
                    
                elif column == 'is_silent':
                    # 無音区間指標もバイナリ
                    metrics_df[column] = metrics_df[column].clip(0, 1)
                    metrics_df[column] = metrics_df[column].fillna(0)
                    
                else:
                    # その他の一般的な指標（volume_score, comment_countなど）
                    # 一般的な前処理
                    # 極端な外れ値（5σを超える値）を処理
                    mean_val = metrics_df[column].mean()
                    std_val = metrics_df[column].std()
                    if not pd.isna(mean_val) and not pd.isna(std_val) and std_val > 0:
                        upper_limit = mean_val + 5 * std_val
                        metrics_df.loc[metrics_df[column] > upper_limit, column] = upper_limit
                    
                    # 欠損値の補間
                    metrics_df[column] = metrics_df[column].interpolate(method='linear')
                    metrics_df[column] = metrics_df[column].ffill().bfill()
                    metrics_df[column] = metrics_df[column].fillna(0)
    
    # 2つのY軸を持つグラフを作成
    fig = go.Figure()
    
    # デフォルトでは基本指標を表示
    if selected_metrics is None:
        selected_metrics = ['comment_count', 'volume_score']
    
    # 表示色マッピング - 主要指標のみに絞る
    colors = {
        'comment_count': '#1E88E5',  # 青
        'volume_score': '#FFC107',   # 黄
        'inter_mean_delta': '#4CAF50', # 緑
        'dynamic_range': '#FF9800',  # オレンジ
        'norm_mean': '#607D8B',     # 灰
        'is_peak': '#E91E63',      # ピンク
        'is_silent': '#795548'     # 茶色
    }
    
    # グラフ表示名マッピング - 主要指標のみに絞る
    metric_names = {
        'comment_count': 'コメント数',
        'volume_score': '音量',
        'inter_mean_delta': '音量変化率',
        'dynamic_range': '音量振れ幅',
        'norm_mean': '正規化音量',
        'is_peak': 'ハイライト',
        'is_silent': '無音区間'
    }
    
    # Y軸の選択（コメント数は常に左軸、それ以外は右軸）
    y_axis_mapping = {
        'comment_count': 'y',  # 左軸
    }
    # それ以外のメトリクスは右軸
    for metric in selected_metrics:
        if metric != 'comment_count':
            y_axis_mapping[metric] = 'y2'
    
    # 指標に適した視覚的表現方法を適用
    for i, metric in enumerate(selected_metrics):
        if metric in metrics_df.columns:
            # Y軸の選択
            yaxis = y_axis_mapping.get(metric, 'y2')
            
            # カラーの選択
            color = colors.get(metric, '#000000')  # デフォルトは黒
            
            # メトリクス名
            name = metric_names.get(metric, metric)
            
            if metric == 'norm_mean':
                # 正規化平均音量は太い実線で表示（主要指標）
                fig.add_trace(go.Scatter(
                    x=metrics_df['time_seconds'],
                    y=metrics_df[metric],
                    mode='lines',
                    name=name,
                    line=dict(color=color, width=2.5, dash='solid'),
                    yaxis=yaxis,
                    hovertemplate=f'時間: %{{x}}秒<br>{name}: %{{y:.2f}}<extra></extra>'
                ))
                
            elif metric == 'is_peak':
                # ピーク検出はマーカーで表示
                peak_points = metrics_df[metrics_df[metric] > 0.5]
                
                if not peak_points.empty:
                    # ピークポイントをマーカーで表示
                    fig.add_trace(go.Scatter(
                        x=peak_points['time_seconds'],
                        y=[0.95] * len(peak_points),  # 上部に表示
                        mode='markers',
                        name=name,
                        marker=dict(
                            symbol='triangle-up',
                            size=10,
                            color=color,
                            line=dict(width=1, color='black')
                        ),
                        yaxis=yaxis,
                        hovertemplate=f'ハイライト: %{{x}}秒<extra></extra>'
                    ))
                    
                    # ピーク位置に縦線を追加
                    for _, peak in peak_points.iterrows():
                        fig.add_shape(
                            type="line",
                            x0=peak['time_seconds'],
                            x1=peak['time_seconds'],
                            y0=0,
                            y1=1,
                            yref=yaxis,
                            line=dict(
                                color=color,
                                width=1.5,
                                dash="dash",
                            ),
                            opacity=0.5,
                            layer="below"
                        )
            
            elif metric == 'dynamic_range':
                # 音量振れ幅は半透明帯として表示
                # ベースラインを取得（基準値）
                if 'norm_mean' in metrics_df.columns and 'norm_mean' in selected_metrics:
                    baseline = metrics_df['norm_mean']
                else:
                    baseline = pd.Series([0.3] * len(metrics_df), index=metrics_df.index)
                
                # 半透明の帯を表示（振れ幅を可視化）
                fig.add_trace(go.Scatter(
                    x=metrics_df['time_seconds'],
                    y=baseline + metrics_df[metric] / 2,  # 上部の境界
                    mode='lines',
                    line=dict(width=0),
                    name=name,
                    yaxis=yaxis,
                    fillcolor=f'rgba{tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (0.3,)}',  # カラーを半透明に
                    fill='tonexty',
                    showlegend=False,
                    hoverinfo='skip'
                ))
                
                fig.add_trace(go.Scatter(
                    x=metrics_df['time_seconds'],
                    y=baseline - metrics_df[metric] / 2,  # 下部の境界
                    mode='lines',
                    line=dict(width=0),
                    name=name,
                    yaxis=yaxis,
                    fillcolor=f'rgba{tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (0.3,)}',  # カラーを半透明に
                    showlegend=True,
                    hovertemplate=f'時間: %{{x}}秒<br>{name}: %{{y:.2f}}<extra></extra>'
                ))
                
            elif metric == 'inter_mean_delta':
                # 前秒比の平均音量差は点線で表示
                fig.add_trace(go.Scatter(
                    x=metrics_df['time_seconds'],
                    y=metrics_df[metric],
                    mode='lines',
                    name=name,
                    line=dict(color=color, width=1.5, dash='dot'),
                    yaxis=yaxis,
                    hovertemplate=f'時間: %{{x}}秒<br>{name}: %{{y:.2f}}<extra></extra>'
                ))
                
            elif metric == 'comment_count':
                # コメント数は青い棒グラフで表示
                fig.add_trace(go.Bar(
                    x=metrics_df['time_seconds'],
                    y=metrics_df[metric],
                    name=name,
                    marker_color=color,
                    opacity=0.7,
                    yaxis=yaxis,
                    hovertemplate=f'時間: %{{x}}秒<br>{name}: %{{y}}<extra></extra>'
                ))
                
            else:
                # その他の指標はデフォルトの線スタイルで表示
                line_width = 2 if metric == 'volume_score' else 1.5
                dash_style = 'solid' if metric == 'volume_score' else 'dash'
                
                fig.add_trace(go.Scatter(
                    x=metrics_df['time_seconds'],
                    y=metrics_df[metric],
                    mode='lines',
                    name=name,
                    line=dict(color=color, width=line_width, dash=dash_style),
                    yaxis=yaxis,
                    hovertemplate=f'時間: %{{x}}秒<br>{name}: %{{y:.2f}}<extra></extra>'
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
            rangeslider=dict(
                visible=True,
                bgcolor='#f0f0f0',
                thickness=0.05,  # より薄くシンプルに
                bordercolor='#cccccc',
                borderwidth=1
            ),  # 横スクロールバーをシークバーとして最適化
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
