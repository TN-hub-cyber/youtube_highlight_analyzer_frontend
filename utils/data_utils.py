import pandas as pd
import streamlit as st
import numpy as np


@st.cache_data
def prepare_metrics_data(metrics_data):
    """
    メトリクスデータを可視化用に準備する
    
    Args:
        metrics_data: Supabaseから取得したメトリクスデータ
        
    Returns:
        整形されたDataFrame
    """
    if not metrics_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(metrics_data)
    
    # 必要な列が存在することを確認
    required_columns = ['time_seconds', 'comment_count', 'volume_score']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        st.warning(f"データに必要な列が不足しています: {', '.join(missing)}")
        # 不足している列を0で埋める
        for col in missing:
            df[col] = 0
    
    return df


@st.cache_data
def prepare_comment_hist_data(comment_hist_data, terms):
    """
    コメント頻度ヒストグラムデータを可視化用に準備する
    
    Args:
        comment_hist_data: Supabaseから取得したコメント頻度データ
        terms: 検索語リスト
        
    Returns:
        整形されたDataFrame
    """
    if not comment_hist_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(comment_hist_data)
    
    # 必要な列が存在することを確認
    if 'time_seconds' not in df.columns:
        st.warning("データにtime_seconds列が不足しています")
        return pd.DataFrame()
    
    # 各検索語の列が存在するか確認し、不足していれば0で埋める
    for term in terms:
        term_col = f"term_{terms.index(term)}"
        if term_col not in df.columns:
            df[term_col] = 0
    
    return df


@st.cache_data
def prepare_chapters_data(chapters_data):
    """
    チャプターデータを可視化用に準備する
    
    Args:
        chapters_data: Supabaseから取得したチャプターデータ
        
    Returns:
        整形されたDataFrame
    """
    if not chapters_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(chapters_data)
    
    # 必要な列が存在することを確認
    required_columns = ['time_seconds', 'title']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        st.warning(f"チャプターデータに必要な列が不足しています: {', '.join(missing)}")
        return pd.DataFrame()
    
    # 自動生成されたチャプターかどうかのフラグがあれば利用
    if 'is_auto' not in df.columns:
        df['is_auto'] = False
    
    return df


@st.cache_data
def prepare_emotion_data(emotion_data):
    """
    感情分析データを可視化用に準備する
    
    Args:
        emotion_data: Supabaseから取得した感情分析データ
        
    Returns:
        整形されたDataFrame
    """
    if not emotion_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(emotion_data)
    
    # 必要な列が存在することを確認
    required_columns = ['time_seconds', 'emotion_type', 'normalized_score']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        st.warning(f"感情分析データに必要な列が不足しています: {', '.join(missing)}")
        return pd.DataFrame()
    
    # ピボットテーブルで各感情タイプを列に変換
    pivot_df = df.pivot_table(
        index='time_seconds', 
        columns='emotion_type', 
        values='normalized_score', 
        aggfunc='max'
    ).reset_index()
    
    # 欠損値を0で埋める
    pivot_df = pivot_df.fillna(0)
    
    return pivot_df


@st.cache_data
def find_highlights(metrics_df, threshold_percentile=90):
    """
    メトリクスデータからハイライトポイントを検出する
    
    Args:
        metrics_df: メトリクスDataFrame
        threshold_percentile: ハイライト検出の閾値パーセンタイル
        
    Returns:
        ハイライトポイントのリスト（時間と重要度スコア）
    """
    if metrics_df.empty:
        return []
    
    # コメント数と音量スコアを合成してハイライトスコアを計算
    if 'comment_count' in metrics_df.columns and 'volume_score' in metrics_df.columns:
        # 各指標を正規化
        metrics_df['norm_comments'] = metrics_df['comment_count'] / metrics_df['comment_count'].max() if metrics_df['comment_count'].max() > 0 else 0
        metrics_df['norm_volume'] = metrics_df['volume_score'] / metrics_df['volume_score'].max() if metrics_df['volume_score'].max() > 0 else 0
        
        # 複合スコアの計算（コメント数: 0.7, 音量: 0.3 の重み）
        metrics_df['highlight_score'] = metrics_df['norm_comments'] * 0.7 + metrics_df['norm_volume'] * 0.3
    else:
        # 不足している場合はコメント数のみ、または音量のみで代用
        if 'comment_count' in metrics_df.columns:
            metrics_df['highlight_score'] = metrics_df['comment_count'] / metrics_df['comment_count'].max() if metrics_df['comment_count'].max() > 0 else 0
        elif 'volume_score' in metrics_df.columns:
            metrics_df['highlight_score'] = metrics_df['volume_score'] / metrics_df['volume_score'].max() if metrics_df['volume_score'].max() > 0 else 0
        else:
            return []
    
    # 閾値を設定
    threshold = np.percentile(metrics_df['highlight_score'], threshold_percentile)
    
    # 閾値を超えるポイントを抽出
    highlights = metrics_df[metrics_df['highlight_score'] >= threshold]
    
    # ハイライトポイントのリストを作成（時間とスコア）
    highlight_points = [
        {
            'time_seconds': row['time_seconds'],
            'score': row['highlight_score'],
            'comment_count': row.get('comment_count', 0),
            'volume_score': row.get('volume_score', 0)
        }
        for _, row in highlights.iterrows()
    ]
    
    # スコアの降順で並べ替え
    highlight_points.sort(key=lambda x: x['score'], reverse=True)
    
    return highlight_points


@st.cache_data
def search_transcriptions(transcriptions_data, search_term):
    """
    文字起こしデータから指定された検索語を検索する
    
    Args:
        transcriptions_data: 文字起こしデータ
        search_term: 検索語
        
    Returns:
        検索結果のリスト（時間と該当テキスト）
    """
    if not transcriptions_data or not search_term:
        return []
    
    df = pd.DataFrame(transcriptions_data)
    
    # 必要な列が存在することを確認
    required_columns = ['time_seconds', 'transcription']
    if not all(col in df.columns for col in required_columns):
        return []
    
    # 検索語を含む行を抽出
    results = df[df['transcription'].str.contains(search_term, case=False, na=False)]
    
    # 検索結果のリストを作成
    search_results = [
        {
            'time_seconds': row['time_seconds'],
            'text': row['transcription'],
            'timestamp': row.get('timestamp', '')
        }
        for _, row in results.iterrows()
    ]
    
    return search_results
