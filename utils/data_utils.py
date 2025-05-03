import pandas as pd
import streamlit as st
import numpy as np
# 循環インポートを解消するために、関数内で動的インポートを行う
# from utils.supabase_client import get_volume_analysis, get_comments


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


# クライアントサイドフォールバック実装関数
@st.cache_data(ttl=60)
def client_side_metrics_agg(video_id, granularity=5):
    """metrics_aggのクライアントサイド実装"""
    try:
        # 循環インポートを避けるために、関数内でインポート
        from utils.supabase_client import get_volume_analysis, get_comments
        
        # Supabaseから直接データ取得
        volume_data = get_volume_analysis(video_id)
        comments_data = get_comments(video_id)
        
        # データフレームに変換
        volume_df = pd.DataFrame(volume_data) if volume_data else pd.DataFrame()
        comments_df = pd.DataFrame(comments_data) if comments_data else pd.DataFrame()
        
        # データが空の場合はダミーデータを生成
        if volume_df.empty and comments_df.empty:
            # 500秒分のダミーデータを作成
            dummy_data = []
            for i in range(0, 500, granularity):
                dummy_data.append({
                    'time_bucket': i,
                    'time_seconds': i,
                    'volume_normalized_avg': 0.1 + 0.2 * (i % 100) / 100,  # 0.1～0.3の間で変動
                    'volume_score': 0.1 + 0.2 * (i % 100) / 100,
                    'comment_count': i % 3  # 0, 1, 2の値をとる
                })
            return dummy_data
        
        # 粒度ごとの時間バケットを作成
        result = []
        
        # 最大時間を計算
        max_time = 0
        if not volume_df.empty and 'time_seconds' in volume_df:
            max_time = max(max_time, volume_df['time_seconds'].max())
        if not comments_df.empty and 'time_seconds' in comments_df:
            max_time = max(max_time, comments_df['time_seconds'].max())
        
        # バケットごとにデータを集計
        for bucket_start in range(0, int(max_time) + granularity, granularity):
            bucket_end = bucket_start + granularity
            
            # 音量データの集計
            volume_normalized_avg = 0
            if not volume_df.empty and 'time_seconds' in volume_df and 'normalized_score' in volume_df:
                bucket_volume = volume_df[
                    (volume_df['time_seconds'] >= bucket_start) & 
                    (volume_df['time_seconds'] < bucket_end)
                ]
                if not bucket_volume.empty:
                    volume_normalized_avg = bucket_volume['normalized_score'].mean()
            
            # コメントデータの集計
            comment_count = 0
            if not comments_df.empty and 'time_seconds' in comments_df:
                bucket_comments = comments_df[
                    (comments_df['time_seconds'] >= bucket_start) & 
                    (comments_df['time_seconds'] < bucket_end)
                ]
                comment_count = len(bucket_comments)
            
            # 結果に追加
            result.append({
                'time_bucket': bucket_start,
                'time_seconds': bucket_start,  # 後方互換性のため追加
                'volume_normalized_avg': float(volume_normalized_avg),
                'volume_score': float(volume_normalized_avg),  # 後方互換性のため追加
                'comment_count': int(comment_count)
            })
        
        return result
        
    except Exception as e:
        st.error(f"メトリクス集計エラー: {e}")
        return []


@st.cache_data(ttl=60)
def client_side_multi_term_comment_hist(video_id, terms, granularity=5):
    """multi_term_comment_histのクライアントサイド実装"""
    try:
        # 循環インポートを避けるために、関数内でインポート
        from utils.supabase_client import get_comments
        
        # コメントデータを取得
        comments_data = get_comments(video_id)
        
        if not comments_data:
            return []
        
        # DataFrameに変換
        comments_df = pd.DataFrame(comments_data)
        
        if 'time_seconds' not in comments_df.columns or 'message' not in comments_df.columns:
            st.warning("コメントデータに必要なカラムがありません")
            return []
        
        # 最大時間を計算
        max_time = comments_df['time_seconds'].max() if not comments_df.empty else 0
        
        # 結果の初期化
        result = []
        
        # バケットごとにデータを集計
        for bucket_start in range(0, int(max_time) + granularity, granularity):
            bucket_end = bucket_start + granularity
            
            # バケット内のコメントを抽出
            bucket_comments = comments_df[
                (comments_df['time_seconds'] >= bucket_start) & 
                (comments_df['time_seconds'] < bucket_end)
            ]
            
            # 各検索語の出現回数をカウント
            term_counts = {}
            for i, term in enumerate(terms):
                if not bucket_comments.empty:
                    count = bucket_comments['message'].str.contains(term, case=False, na=False).sum()
                    term_counts[f"term_{i}"] = int(count)
                else:
                    term_counts[f"term_{i}"] = 0
            
            # 結果に追加
            bucket_result = {
                'time_bucket': bucket_start,
                'time_seconds': bucket_start,  # 後方互換性のため追加
            }
            bucket_result.update(term_counts)
            
            result.append(bucket_result)
        
        return result
        
    except Exception as e:
        st.error(f"コメント頻度集計エラー: {e}")
        return []


@st.cache_data(ttl=60)
def client_side_search_comments_multi(video_id, terms, match_type="any"):
    """search_comments_multiのクライアントサイド実装"""
    try:
        # 循環インポートを避けるために、関数内でインポート
        from utils.supabase_client import get_comments
        
        # コメントデータを取得
        comments_data = get_comments(video_id)
        
        if not comments_data:
            return []
        
        # DataFrameに変換
        comments_df = pd.DataFrame(comments_data)
        
        if 'time_seconds' not in comments_df.columns or 'message' not in comments_df.columns:
            st.warning("コメントデータに必要なカラムがありません")
            return []
        
        # 検索条件に基づいてフィルタリング
        if match_type == "all":
            # すべての検索語を含むコメントをフィルタリング
            filtered_df = comments_df.copy()
            for term in terms:
                filtered_df = filtered_df[filtered_df['message'].str.contains(term, case=False, na=False)]
        else:  # "any"
            # いずれかの検索語を含むコメントをフィルタリング
            mask = pd.Series(False, index=comments_df.index)
            for term in terms:
                mask = mask | comments_df['message'].str.contains(term, case=False, na=False)
            filtered_df = comments_df[mask]
        
        # 検索スコアの計算
        results = []
        for _, comment in filtered_df.iterrows():
            score = 0
            matched_terms = []
            
            for term in terms:
                if term.lower() in comment['message'].lower():
                    score += 1
                    matched_terms.append(term)
            
            # 結果の作成
            results.append({
                'id': comment.get('id', 0),
                'time_seconds': comment['time_seconds'],
                'message': comment['message'],
                'name': comment.get('name', ''),
                'author': comment.get('name', ''),  # 後方互換性のため
                'score': score / len(terms),
                'matched_terms': matched_terms
            })
        
        # スコア順にソート
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        return results
        
    except Exception as e:
        st.error(f"コメント検索エラー: {e}")
        return []
