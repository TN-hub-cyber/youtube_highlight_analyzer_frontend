import pandas as pd
import streamlit as st
import numpy as np
# 循環インポートを解消するために、関数内で動的インポートを行う
# from utils.supabase_client import get_volume_analysis, get_comments
from utils.supabase_client import get_supabase_client # Supabaseクライアントを取得する関数をインポート


@st.cache_data
def prepare_metrics_data(metrics_data, detailed_volume_data=None):
    """
    メトリクスデータを可視化用に準備する
    
    Args:
        metrics_data: Supabaseから取得したメトリクスデータ
        detailed_volume_data: 詳細音量分析データ（オプション）
        
    Returns:
        整形されたDataFrame
    """
    if not metrics_data:
        return pd.DataFrame()
    
    # 最初から適切な型を設定してデータフレームを作成
    # データが空でない場合に型変換を確実に行う
    df = pd.DataFrame(metrics_data)
    
    if not df.empty:
        # まずconvert_dtypesでPandasに推測させる
        df = df.convert_dtypes()
        
        # 時間軸を明示的にBIGINT（int64）型に確保 - 1000秒以上の問題を防ぐため
        if 'time_seconds' in df.columns:
            # NaN値があれば0で一時的に埋める（型変換のため）
            df['time_seconds'] = df['time_seconds'].fillna(0)
            
            # まず全ての値がfloatであるかを確認してから変換
            if df['time_seconds'].dtype.kind == 'f':
                # floatからint64に変換（32ビット整数の範囲を超える可能性がある）
                df['time_seconds'] = df['time_seconds'].astype('float64').astype('int64')
            else:
                # 直接int64に変換
                df['time_seconds'] = df['time_seconds'].astype('int64')
                
            # time_bucketも同様に扱う（存在する場合）
            if 'time_bucket' in df.columns:
                df['time_bucket'] = df['time_bucket'].fillna(0).astype('int64')
        
        # 数値データ列の型を明示的に設定
        numeric_cols = ['volume_score', 'volume_normalized_avg', 'comment_count']
        for col in numeric_cols:
            if col in df.columns:
                # まずfloat64に変換してから、適切な型に変換
                if col == 'comment_count':
                    df[col] = df[col].fillna(0).astype('int64')
                else:
                    df[col] = df[col].fillna(0).astype('float64')
    
    # 必要な列が存在することを確認
    required_columns = ['time_seconds', 'comment_count', 'volume_score']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        st.warning(f"データに必要な列が不足しています: {', '.join(missing)}")
        # 不足している列を0で埋める
        for col in missing:
            df[col] = 0
    
    # 詳細音量分析データがある場合は統合
    if detailed_volume_data:
        # DataFrameに変換
        vol_df = pd.DataFrame(detailed_volume_data)
        
        if not vol_df.empty and 'time_seconds' in vol_df.columns:
            # 統合したいカラムのリスト
            detail_columns = [
                'inter_mean_delta', 'inter_max_delta', 'inter_min_delta', 
                'dynamic_range', 'norm_mean', 'smooth_mean'
            ]
            
            # 存在するカラムのみ抽出
            existing_columns = [col for col in detail_columns if col in vol_df.columns]
            if existing_columns:
                # 詳細音量データの前処理を強化
                # 型変換とNaNやNullの事前処理
                for col in existing_columns:
                    if col in vol_df.columns:
                        # 欠損値の検出
                        nan_count_before = vol_df[col].isna().sum()
                        
                        # まず明示的に浮動小数点型に変換 - float4の問題を回避
                        vol_df[col] = pd.to_numeric(vol_df[col], errors='coerce').astype('float64')
                        
                        # 欠損値を補間（線形補間、前方/後方補間）- 0埋めをせず断言を追加
                        vol_df[col] = vol_df[col].interpolate(method='linear')
                        vol_df[col] = vol_df[col].bfill() # 先頭のNaN処理
                        vol_df[col] = vol_df[col].ffill() # 末尾のNaN処理
                        
                        # 補間後も残るNaNがあるか確認し警告
                        nan_count = vol_df[col].isna().sum()
                        if nan_count > 0:
                            st.warning(f"{col}列に補間前に{nan_count_before}個、補間後も{nan_count}個のNaNが残っています - データ品質問題の可能性")
                            
                        # 特に1000秒付近のデータを確認
                        problem_area = vol_df[(vol_df['time_seconds'] >= 950) & (vol_df['time_seconds'] <= 1100)]
                        if not problem_area.empty:
                            prob_nan = problem_area[col].isna().sum()
                            if prob_nan > 0:
                                print(f"{col}列の1000秒付近に{prob_nan}個のNaNが残っています")
            
            # データ統合方法を改善: mergeを使った効率的な統合
            # 重複を防ぐために一度クレンジング
            vol_df = vol_df.drop_duplicates(subset=['time_seconds']).sort_values('time_seconds')
            
            # 時間バケットの情報を取得
            if 'time_bucket' in df.columns:
                # バケットサイズを推定（隣接するバケット間の差）
                bucket_sizes = df['time_bucket'].diff().dropna()
                bucket_size = bucket_sizes.mode()[0] if not bucket_sizes.empty else 5  # デフォルトは5秒
            else:
                # バケットサイズのデフォルト値
                bucket_size = 5
                
            # データフレームに時間バケット列がなければ追加 - 必ずint64型に
            if 'time_bucket' not in df.columns:
                df['time_bucket'] = df['time_seconds'].astype('int64')
            
            # 詳細音量データを時間バケットごとに集計
            vol_df['time_bucket'] = (vol_df['time_seconds'] // bucket_size) * bucket_size
            vol_agg = vol_df.groupby('time_bucket')[existing_columns].agg({
                col: 'mean' for col in existing_columns
            }).reset_index()
            
            # mergeを使って効率的にデータを統合
            # left joinで元のデータフレームはすべて保持
            df = df.merge(vol_agg, on='time_bucket', how='left', suffixes=('', '_detail'))
            
            # 後処理: 長い欠損区間の検出と処理
            for col in existing_columns:
                if col in df.columns:
                    # 元の列がすでに存在する場合は詳細データで上書き
                    if f"{col}_detail" in df.columns:
                        # NaN値を保存
                        mask = ~df[f"{col}_detail"].isna()
                        df.loc[mask, col] = df.loc[mask, f"{col}_detail"]
                        # 詳細列は削除
                        df = df.drop(columns=[f"{col}_detail"])
                    
                    # 大きな時間ギャップを検出し、そこでは補間しない
                    # （平坦な線を発生させないため）
                    time_diff = df['time_seconds'].diff()
                    large_gaps = time_diff > 300  # 5分以上の間隔
                    if large_gaps.any():
                        for idx in df.index[large_gaps]:
                            if idx > 0:
                                df.loc[idx, col] = np.nan
    
    return df

@st.cache_data
def prepare_volume_detail_data(volume_detail_data):
    """
    詳細音量分析データを可視化用に準備する
    
    Args:
        volume_detail_data: Supabaseから取得した詳細音量分析データ
        
    Returns:
        整形されたDataFrame
    """
    if not volume_detail_data:
        return pd.DataFrame()
    
    # データフレーム変換と初期型設定を統合
    df = pd.DataFrame(volume_detail_data)
    
    # 元のデータがあるときだけ型変換を行う
    if not df.empty:
        # データ型変換（一括）
        df = df.convert_dtypes()
        
        # time_secondsを明示的にint64に
        if 'time_seconds' in df.columns:
            # まずfloat型として扱い、それからint64に安全に変換
            df['time_seconds'] = pd.to_numeric(df['time_seconds'], errors='coerce').fillna(0).astype('int64')
    
    # 必要な列が存在することを確認
    required_columns = ['time_seconds']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        st.warning(f"詳細音量データに必要な列が不足しています: {', '.join(missing)}")
        return pd.DataFrame()
    
    # 必要に応じて追加のデータ処理
    metric_columns = [
        'inter_mean_delta', 'inter_max_delta', 'inter_min_delta', 
        'dynamic_range', 'norm_mean', 'smooth_mean', 
        'rel_net_change', 'rel_max_positive_diff', 'rel_sum_of_abs_diff',
        'abs_db_mean', 'abs_db_max', 'abs_db_min'
    ]
    
    for col in metric_columns:
        if col in df.columns:
            # まず明示的にfloat64型に変換（元データがfloat4の場合の問題を回避）
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
            
            # 欠損値を前後の値で補間（時系列データの特性を維持）
            df[col] = df[col].interpolate(method='linear')
            df[col] = df[col].bfill()  # 先頭のNaN処理
            df[col] = df[col].ffill()  # 末尾のNaN処理
            
            # 補間後もNaNが残っているか確認（削除せず警告だけ）
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                st.warning(f"{col}列に補間後も{nan_count}個のNaNが残っています - データ品質問題の可能性")
            
            # すべての値が0になっていないか確認
            non_zero = (df[col] != 0).sum()
            zero_ratio = 1.0 - non_zero / len(df) if len(df) > 0 else 0
            if zero_ratio > 0.9:  # 90%以上が0の場合に警告
                st.warning(f"{col}列が90%以上0値になっています（{zero_ratio:.1%}）- データ型問題の可能性")
                
                # 特に1000秒付近の問題がないか確認（対象範囲を拡大）
                problem_range = df[(df['time_seconds'] >= 950) & (df['time_seconds'] <= 1200)]
                if not problem_range.empty and col in problem_range.columns:
                    nan_count_range = problem_range[col].isna().sum()
                    zero_count_range = (problem_range[col] == 0).sum()
                    if nan_count_range > 0 or zero_count_range > problem_range.shape[0] * 0.3:  # 30%以上が0の場合
                        st.warning(f"問題範囲(950-1200秒)の{col}列に{nan_count_range}個のNaNと{zero_count_range}個の0値があります ({zero_count_range/len(problem_range):.1%})")
                        
                        # もし問題が深刻な場合、1000秒付近のサンプルを出力
                        if zero_count_range > problem_range.shape[0] * 0.7:  # 70%以上が0なら深刻
                            sample = problem_range.sort_values('time_seconds').head(5)
                            print(f"1000秒付近のサンプル（先頭5件）: {sample[['time_seconds', col]].to_dict('records')}")
    
    # 時間順にソート
    df = df.sort_values('time_seconds')
    
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
    required_columns = ['time_seconds', 'emotion_type', 'confidence_score']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        st.warning(f"感情分析データに必要な列が不足しています: {', '.join(missing)}")
        return pd.DataFrame()
    
    # 表示用にデータを整理（ピボットせずに元の形式を維持）
    # 必要な列だけを選択
    result_df = df[['time_seconds', 'emotion_type', 'confidence_score']].copy()
    
    # 時間順にソート
    result_df = result_df.sort_values('time_seconds')
    
    return result_df


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
    if metrics_df.empty or 'time_seconds' not in metrics_df.columns:
        return []

    df = metrics_df.copy() # 元のDataFrameを変更しないようにコピー

    # ハイライトスコア計算に必要な列が存在するか確認
    has_comments = 'comment_cnt' in df.columns
    has_norm_mean = 'norm_mean' in df.columns

    if not has_comments and not has_norm_mean:
        st.warning("ハイライト計算に必要な 'comment_cnt' または 'norm_mean' がデータフレームにありません。")
        return []

    # 各指標を正規化 (0除算を回避)
    norm_comments = 0
    if has_comments:
        max_comments = df['comment_cnt'].max()
        norm_comments = df['comment_cnt'] / max_comments if max_comments > 0 else 0
        df['norm_comments'] = norm_comments # デバッグ用に列を追加しておく

    norm_mean_val = 0
    if has_norm_mean:
        # norm_mean は既に 0-1 の範囲のはずだが、念のため最大値で割る
        max_norm_mean = df['norm_mean'].max()
        norm_mean_val = df['norm_mean'] / max_norm_mean if max_norm_mean > 0 else 0
        df['norm_mean_scaled'] = norm_mean_val # デバッグ用に列を追加しておく

    # 複合スコアの計算（コメント数: 0.7, 正規化音量: 0.3 の重み）
    # 片方しかなくても計算できるように調整
    if has_comments and has_norm_mean:
        df['highlight_score'] = norm_comments * 0.7 + norm_mean_val * 0.3
    elif has_comments:
        df['highlight_score'] = norm_comments # コメント数のみ
    else: # has_norm_mean のみ
        df['highlight_score'] = norm_mean_val # 正規化音量のみ

    # highlight_score が NaN になっていないか確認
    if df['highlight_score'].isna().any():
        st.warning("ハイライトスコア計算中にNaNが発生しました。0で補完します。")
        df['highlight_score'] = df['highlight_score'].fillna(0)

    # スコアが全て0の場合、パーセンタイル計算でエラーになるため早期リターン
    if df['highlight_score'].max() <= 0:
        return []

    # 閾値を設定 (スコアが全て同じ場合のエラーを回避)
    try:
        # スコアのばらつきが小さい場合、percentileがエラーを出すことがある
        if df['highlight_score'].nunique() <= 1:
             threshold = df['highlight_score'].iloc[0] # 全て同じ値ならその値を閾値に
        else:
             threshold = np.percentile(df['highlight_score'].dropna(), threshold_percentile)
    except IndexError: # データが空、または NaN のみの場合
        return []
    except Exception as e:
        st.error(f"ハイライト閾値計算中にエラー: {e}")
        return []
    
    # 閾値を超えるポイントを抽出 (閾値が0の場合は、スコアが0より大きいものを対象とする)
    if threshold <= 0:
        highlights_df = df[df['highlight_score'] > 0]
    else:
        highlights_df = df[df['highlight_score'] >= threshold]

    if highlights_df.empty:
        return []

    # ハイライトポイントのリストを作成（時間とスコア、および元指標）
    highlight_points = []
    for _, row in highlights_df.iterrows():
        point = {
            'time_seconds': row['time_seconds'],
            'score': row['highlight_score'],
        }
        if has_comments:
            point['comment_cnt'] = row.get('comment_cnt', 0)
        if has_norm_mean:
            point['norm_mean'] = row.get('norm_mean', 0) # 元の norm_mean を含める
        highlight_points.append(point)
    
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


@st.cache_data
def load_and_prepare_secondly_metrics(video_id: int, granularity: int = 1):
    """
    新しい metrics_secondly RPC からデータを取得し、指定された粒度で集計・補間する関数

    Args:
        video_id (int): 動画ID
        granularity (int): 集計する時間粒度（秒）。デフォルトは1秒（集計なし）。

    Returns:
        pd.DataFrame: 処理済みのメトリクスデータ
    """
    supabase = get_supabase_client()
    if not supabase:
        st.error("Supabaseクライアントの取得に失敗しました。")
        return pd.DataFrame()

    try:
        # ① 新しいRPC metrics_secondly_g からデータを取得 (粒度パラメータ _g を渡す)
        response = supabase.rpc("metrics_secondly_g", {"_vid": video_id, "_g": granularity}).execute()
        if not response.data:
            st.warning(f"動画ID {video_id}、粒度 {granularity}秒 の metrics_secondly_g データが見つかりません。")
            return pd.DataFrame()

        df = pd.DataFrame(response.data)

        # time_bucket を time_seconds として扱う (グラフ描画のため)
        # RPCが time_bucket を返すので、それを time_seconds にリネーム
        if 'time_bucket' in df.columns:
            df = df.rename(columns={"time_bucket": "time_seconds"})
        else:
            st.error("RPCからの応答に time_bucket 列が含まれていません。")
            return pd.DataFrame()

        # 型固定 (time_seconds はリネーム後)
        df = df.astype({
            "time_seconds": "int64",
            "norm_mean": "float64",
            "inter_mean_delta": "float64",
            "dynamic_range": "float64",
            "is_peak": "int64", # boolではなくintとして扱う
            "is_silent": "int64", # boolではなくintとして扱う
            "comment_cnt": "int64"
        })

        # ② Python側での粒度変更処理は不要 (RPCが既に行っている)

        # ③ 欠損補間（実数列のみ）- RPCはNULLを返すはずなので補間は必要
        numeric_cols = ["norm_mean", "inter_mean_delta", "dynamic_range"]
        # interpolateはDataFrame全体に適用できるが、NaNがない場合はスキップされる
        df[numeric_cols] = df[numeric_cols].interpolate(method="linear", limit_direction="both")

        # 補間後もNaNが残っていないか確認
        if df[numeric_cols].isna().sum().sum() > 0:
             st.warning(f"線形補間後も実数メトリクス列にNaNが残っています: {df[numeric_cols].isna().sum()}")
             # 残ったNaNは0で埋める（グラフ描画エラーを防ぐため）
             df[numeric_cols] = df[numeric_cols].fillna(0)

        # フラグ列 (is_peak, is_silent) と comment_cnt は欠損しない想定だが念のため確認
        flag_cols = ["is_peak", "is_silent", "comment_cnt"]
        if df[flag_cols].isna().sum().sum() > 0:
            st.warning(f"フラグ列またはコメント数列に予期せぬNaNがあります: {df[flag_cols].isna().sum()}")
            df[flag_cols] = df[flag_cols].fillna(0) # 0で埋める

        # 時間順にソートしておく (time_seconds はリネーム後の列名)
        df = df.sort_values("time_seconds").reset_index(drop=True)

        return df

    except Exception as e:
        st.error(f"metrics_secondly データの処理中にエラーが発生しました: {e}")
        import traceback
        st.error(traceback.format_exc()) # 詳細なエラーログ
        return pd.DataFrame()


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
