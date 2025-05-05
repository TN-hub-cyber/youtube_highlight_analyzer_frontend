import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go

# データ処理ライブラリをインポート
from utils.supabase_client import (
    get_volume_analysis_secondly,
    get_volume_analysis,
    get_video_details,
    get_metrics_agg,
    get_supabase_client,
    init_supabase
)

def display_json(data, title="データ表示"):
    """JSONデータを整形して表示する"""
    st.subheader(title)
    try:
        # 表示用にJSONを整形
        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
        st.code(formatted_json, language="json")
    except:
        # DataFrameに変換して表示
        st.write(pd.DataFrame(data))

def analyze_volume_data(df):
    """
    詳細音量データの分析を行う関数
    
    Args:
        df: 音量データのDataFrame
    """
    st.subheader("📊 詳細音量データ分析")
    
    # データの基本統計量を表示
    st.write("### 基本統計量")
    numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
    st.dataframe(df[numeric_columns].describe())
    
    # 時間連続性の分析
    st.write("### 時間連続性の分析")
    time_diffs = df['time_seconds'].diff().dropna()
    
    # 時間の連続性をグラフで表示
    fig_time_diff = px.histogram(
        time_diffs, 
        nbins=50,
        title="時間間隔の分布",
        labels={"value": "時間間隔（秒）", "count": "頻度"}
    )
    st.plotly_chart(fig_time_diff)
    
    irregular_intervals = time_diffs[time_diffs > 1.5].index.tolist()
    if irregular_intervals:
        st.warning(f"不規則な時間間隔が{len(irregular_intervals)}箇所見つかりました")
        st.write("不規則な間隔が発生している時間位置:")
        irregular_times = df.iloc[irregular_intervals]['time_seconds'].tolist()
        for i, t in enumerate(irregular_times[:10]):
            st.write(f"{i+1}. {t}秒付近 (間隔: {time_diffs.iloc[irregular_intervals[i]]:.2f}秒)")
        if len(irregular_times) > 10:
            st.write(f"...他{len(irregular_times)-10}箇所")
    else:
        st.success("時間間隔は均一です")
    
    # 欠損値の分析
    st.write("### 欠損値の分析")
    missing_values = df.isnull().sum()
    if missing_values.sum() > 0:
        st.warning("欠損値があります")
        st.dataframe(missing_values[missing_values > 0])
    else:
        st.success("欠損値はありません")
    
    # 主要な音量関連指標をグラフ表示
    st.write("### 音量指標の推移")
    volume_metrics = ['norm_mean', 'inter_mean_delta', 'dynamic_range']
    available_metrics = [col for col in volume_metrics if col in df.columns]
    
    if available_metrics:
        # まずすべての指標を一つのグラフに表示
        fig_combined = go.Figure()
        
        for metric in available_metrics:
            fig_combined.add_trace(go.Scatter(
                x=df['time_seconds'],
                y=df[metric],
                mode='lines',
                name=metric
            ))
            
        fig_combined.update_layout(
            title="音量指標の推移",
            xaxis_title="時間（秒）",
            yaxis_title="値",
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_combined)
        
        # 個別の指標を詳細に表示するオプション
        selected_metric = st.selectbox(
            "詳細表示する指標を選択", 
            available_metrics,
            index=0 if available_metrics else None
        )
        
        if selected_metric:
            fig_detail = px.line(
                df, 
                x='time_seconds', 
                y=selected_metric,
                title=f"{selected_metric}の詳細推移"
            )
            st.plotly_chart(fig_detail)
    else:
        st.warning("音量関連指標が見つかりません")


def analyze_problem_area(df):
    """
    問題のある時間帯（1000秒付近）を詳細に分析する
    
    Args:
        df: 音量データのDataFrame
    """
    st.subheader("🔍 1000秒付近の問題分析")
    
    # 問題の時間範囲を定義（デフォルトは950〜1100秒）
    col1, col2 = st.columns(2)
    with col1:
        min_time = st.number_input("開始時間（秒）", value=950, min_value=0)
    with col2:
        max_time = st.number_input("終了時間（秒）", value=1100, min_value=0)
    
    # 指定された時間範囲のデータを抽出
    problem_df = df[(df['time_seconds'] >= min_time) & (df['time_seconds'] <= max_time)].copy()
    
    if problem_df.empty:
        st.warning(f"指定された時間範囲（{min_time}〜{max_time}秒）にデータがありません")
        return
    
    st.write(f"### {min_time}〜{max_time}秒のデータ分析")
    st.write(f"対象データ数: {len(problem_df)}件")
    
    # データの連続性チェック
    time_diffs = problem_df['time_seconds'].diff().dropna()
    avg_interval = time_diffs.mean()
    max_interval = time_diffs.max()
    
    st.write(f"時間間隔: 平均={avg_interval:.3f}秒, 最大={max_interval:.3f}秒")
    
    # 大きな間隔がある場合は警告
    if max_interval > 1.5:
        st.warning(f"この時間範囲には最大{max_interval:.3f}秒の間隔があります")
        large_gaps = time_diffs[time_diffs > 1.5]
        if not large_gaps.empty:
            st.write("大きな間隔がある時間位置:")
            for idx in large_gaps.index:
                time_pos = problem_df.loc[idx, 'time_seconds']
                gap = time_diffs.loc[idx]
                st.write(f"- {time_pos:.2f}秒 (間隔: {gap:.2f}秒)")
    
    # データテーブル表示
    with st.expander("データテーブル表示", expanded=False):
        st.dataframe(problem_df)
    
    # 値の変化を詳細に分析
    volume_metrics = ['norm_mean', 'inter_mean_delta', 'dynamic_range']
    available_metrics = [col for col in volume_metrics if col in problem_df.columns]
    
    if available_metrics:
        # 問題時間帯のデータをグラフ表示
        fig = go.Figure()
        
        for metric in available_metrics:
            fig.add_trace(go.Scatter(
                x=problem_df['time_seconds'],
                y=problem_df[metric],
                mode='lines+markers',
                name=metric
            ))
            
        fig.update_layout(
            title=f"{min_time}〜{max_time}秒の音量指標推移",
            xaxis_title="時間（秒）",
            yaxis_title="値",
            hovermode="x unified"
        )
        
        st.plotly_chart(fig)
        
        # 値の停滞（平坦化）を検出
        for metric in available_metrics:
            st.write(f"### {metric}の変化分析")
            
            # 前の値との差分を計算
            problem_df[f'{metric}_diff'] = problem_df[metric].diff()
            zero_diffs = problem_df[problem_df[f'{metric}_diff'] == 0]
            
            if not zero_diffs.empty:
                consecutive_count = 0
                flat_regions = []
                prev_idx = None
                
                for idx in zero_diffs.index:
                    if prev_idx is not None and idx == prev_idx + 1:
                        consecutive_count += 1
                    else:
                        if consecutive_count >= 2:  # 3つ以上連続で同じ値
                            flat_regions.append((prev_idx - consecutive_count, prev_idx, consecutive_count + 1))
                        consecutive_count = 0
                    prev_idx = idx
                
                # 最後のフラット領域をチェック
                if consecutive_count >= 2:
                    flat_regions.append((prev_idx - consecutive_count, prev_idx, consecutive_count + 1))
                
                if flat_regions:
                    st.warning(f"{len(flat_regions)}箇所で値が平坦になっています")
                    st.write("平坦な領域:")
                    for start_idx, end_idx, count in flat_regions:
                        start_time = problem_df.iloc[start_idx]['time_seconds']
                        end_time = problem_df.iloc[end_idx]['time_seconds']
                        value = problem_df.iloc[start_idx][metric]
                        st.write(f"- {start_time:.2f}〜{end_time:.2f}秒: {count}ポイント連続で値={value}")
                else:
                    st.success("連続して同じ値が続く領域はありません")
            else:
                st.success("すべての値が変化しています（平坦な領域はありません）")


def main():
    st.title("詳細音量データ・デバッグツール")
    st.write("音量関連データの取得と詳細分析を行います")
    
    # Supabaseの初期化を明示的に行う
    supabase_client = get_supabase_client(st)
    if not supabase_client:
        st.error("Supabaseクライアントの初期化に失敗しました")
        st.write("別途初期化を試みます...")
        supabase_client = init_supabase()
        
    if not supabase_client:
        st.error("Supabaseに接続できません。設定を確認してください。")
        st.stop()
    else:
        st.success("Supabaseに接続しました")
    
    # ビデオIDの入力（セッション状態から取得するか、入力フィールドで受け取る）
    if 'vid' in st.session_state:
        video_id = st.session_state['vid']
        st.write(f"セッション状態から読み込まれたビデオID: {video_id}")
    else:
        video_id = st.text_input("ビデオIDを入力", value="", help="内部ID（数値）またはYouTube ID（文字列）を入力")
        
    if not video_id:
        st.warning("ビデオIDを入力するか、メインアプリから動画を選択してください")
        # テスト用デフォルト値を設定することもできます
        # video_id = "12345" # テスト用ID
        st.stop()
    
    # ビデオ詳細を取得
    try:
        video_details = get_video_details(video_id)
        if video_details:
            st.write(f"## 動画タイトル: {video_details.get('title', '不明')}")
        else:
            st.warning("動画詳細情報が取得できませんでした")
    except Exception as e:
        st.error(f"動画詳細取得エラー: {e}")
        video_details = {"title": "不明"}
    
    # データ取得タイプの選択
    data_type = st.radio(
        "取得するデータの種類を選択",
        ["詳細音量データ (volume_analysis_secondly)", 
         "基本音量データ (volume_analysis)",
         "メトリクス集計データ (metrics_agg)"],
        index=0
    )
    
    # データ表示件数の設定
    display_limit = st.slider("表示件数", min_value=10, max_value=500, value=50, step=10)
    
    # データ取得と表示
    if st.button("データを取得"):
        with st.spinner("データを取得中..."):
            try:
                if data_type == "詳細音量データ (volume_analysis_secondly)":
                    st.write(f"詳細音量データを取得中... (video_id: {video_id})")
                    data = get_volume_analysis_secondly(video_id)
                    st.write(f"取得結果: {type(data)}, 空かどうか: {not data}")
                    
                    if data:
                        # 表示件数を制限して不要な負荷を減らす
                        display_data = data[:display_limit]
                        
                        # 行数と時間範囲を表示
                        if data:
                            min_time = min(item['time_seconds'] for item in data)
                            max_time = max(item['time_seconds'] for item in data)
                            st.write(f"総データ件数: {len(data)}件 (時間範囲: {min_time}秒 ～ {max_time}秒)")
                        
                        # 時間間隔の分析
                        if len(data) >= 2:
                            df = pd.DataFrame(data)
                            df = df.sort_values('time_seconds')
                            time_diffs = df['time_seconds'].diff().dropna()
                            avg_interval = time_diffs.mean()
                            min_interval = time_diffs.min()
                            max_interval = time_diffs.max()
                            st.write(f"時間間隔: 平均={avg_interval:.2f}秒, 最小={min_interval:.2f}秒, 最大={max_interval:.2f}秒")
                        
                        # テーブル表示
                        df = pd.DataFrame(display_data)
                        st.write(f"最初の{len(display_data)}件を表示:")
                        st.dataframe(df)
                        
                        # JSONとして表示
                        display_json(display_data, "詳細音量データ（JSON形式）")
                        
                        # 列名（キー）の一覧表示
                        if data:
                            keys = data[0].keys()
                            st.write("### 利用可能なデータキー（列名）")
                            st.write(", ".join(keys))
                            
                            # DataFrameに変換して詳細分析
                            df_full = pd.DataFrame(data).sort_values('time_seconds')
                            
                            # 詳細分析タブ
                            tabs = st.tabs(["基本データ", "詳細分析", "1000秒付近の問題"])
                            
                            with tabs[1]:
                                # 詳細音量データの分析
                                analyze_volume_data(df_full)
                            
                            with tabs[2]:
                                # 1000秒付近の問題分析
                                analyze_problem_area(df_full)
                    else:
                        st.error("詳細音量データが取得できませんでした")
                
                elif data_type == "基本音量データ (volume_analysis)":
                    st.write(f"基本音量データを取得中... (video_id: {video_id})")
                    data = get_volume_analysis(video_id)
                    st.write(f"取得結果: {type(data)}, 空かどうか: {not data}")
                    
                    if data:
                        # 表示件数を制限
                        display_data = data[:display_limit]
                        
                        # 行数と時間範囲を表示
                        if data:
                            min_time = min(item['time_seconds'] for item in data)
                            max_time = max(item['time_seconds'] for item in data)
                            st.write(f"総データ件数: {len(data)}件 (時間範囲: {min_time}秒 ～ {max_time}秒)")
                        
                        # テーブル表示
                        df = pd.DataFrame(display_data)
                        st.write(f"最初の{len(display_data)}件を表示:")
                        st.dataframe(df)
                        
                        # JSONとして表示
                        display_json(display_data, "基本音量データ（JSON形式）")
                        
                        # 列名（キー）の一覧表示
                        if data:
                            keys = data[0].keys()
                            st.write("### 利用可能なデータキー（列名）")
                            st.write(", ".join(keys))
                    else:
                        st.error("基本音量データが取得できませんでした")
                
                elif data_type == "メトリクス集計データ (metrics_agg)":
                    granularity = st.slider("集計粒度（秒）", min_value=1, max_value=30, value=5, step=1)
                    st.write(f"メトリクス集計データを取得中... (video_id: {video_id}, 粒度: {granularity}秒)")
                    data = get_metrics_agg(video_id, granularity)
                    st.write(f"取得結果: {type(data)}, 空かどうか: {not data}")
                    
                    if data:
                        # 表示件数を制限
                        display_data = data[:display_limit]
                        
                        # 行数と時間範囲を表示
                        if data:
                            min_time = min(item['time_seconds'] for item in data)
                            max_time = max(item['time_seconds'] for item in data)
                            st.write(f"総データ件数: {len(data)}件 (時間範囲: {min_time}秒 ～ {max_time}秒)")
                        
                        # テーブル表示
                        df = pd.DataFrame(display_data)
                        st.write(f"最初の{len(display_data)}件を表示:")
                        st.dataframe(df)
                        
                        # JSONとして表示
                        display_json(display_data, "メトリクス集計データ（JSON形式）")
                        
                        # 列名（キー）の一覧表示
                        if data:
                            keys = data[0].keys()
                            st.write("### 利用可能なデータキー（列名）")
                            st.write(", ".join(keys))
                    else:
                        st.error("メトリクス集計データが取得できませんでした")
            except Exception as e:
                st.error(f"データ取得中にエラーが発生しました: {e}")
                st.exception(e)

if __name__ == "__main__":
    main()
