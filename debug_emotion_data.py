import streamlit as st
import pandas as pd
from utils.supabase_client import get_supabase_client, get_emotion_analysis

# Supabaseクライアントの初期化
supabase = get_supabase_client(st)

# 動画IDをハードコード（テスト用）
# 本番環境では動的に取得するべきだが、デバッグ目的では固定値を使用
video_id = 1  # テスト用動画ID

# 感情分析データの取得
with st.spinner("感情分析データを取得中..."):
    emotion_data = get_emotion_analysis(video_id)

# データの表示
st.title("感情分析データのデバッグ")

if emotion_data:
    st.write(f"取得レコード数: {len(emotion_data)}")
    
    # 元のデータをサンプル表示
    st.subheader("元のデータ（最初の10行）")
    st.write(pd.DataFrame(emotion_data).head(10))
    
    # データ内のemotion_typeの種類を確認
    emotion_types = set()
    for item in emotion_data:
        if 'emotion_type' in item:
            emotion_types.add(item['emotion_type'])
    
    st.subheader("検出された感情タイプ")
    st.write(sorted(list(emotion_types)))
    
    # 感情タイプごとのデータ数をカウント
    emotion_counts = {}
    for item in emotion_data:
        emotion_type = item.get('emotion_type', 'unknown')
        emotion_counts[emotion_type] = emotion_counts.get(emotion_type, 0) + 1
    
    st.subheader("感情タイプごとのデータ数")
    st.write(emotion_counts)
    
    # utils/data_utils.pyのprepare_emotion_data関数を実行
    from utils.data_utils import prepare_emotion_data
    
    st.subheader("prepare_emotion_data関数の結果")
    emotion_df = prepare_emotion_data(emotion_data)
    
    if not emotion_df.empty:
        st.write("変換後のデータ列: ", emotion_df.columns.tolist())
        st.write("変換後のデータ（最初の10行）")
        st.write(emotion_df.head(10))
    else:
        st.error("データの変換に失敗しました")
else:
    st.error("感情分析データが取得できませんでした")
