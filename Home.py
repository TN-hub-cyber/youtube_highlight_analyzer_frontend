import streamlit as st
import pandas as pd
from utils.supabase_client import get_supabase_client, show_connection_error, init_supabase

# ページ設定
st.set_page_config(
    page_title="YouTube分析 - チャンネル一覧",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Supabase接続の初期化とキャッシュ
supabase = get_supabase_client(st)
if supabase is None:
    show_connection_error(st)
    st.stop()

# ここでget_channelsをインポート（supabase初期化後）
from utils.supabase_client import get_channels

# サイドバー
with st.sidebar:
    st.title("YouTube動画分析")
    st.markdown("YouTube動画のデータを可視化し、分析するためのツールです。")
    st.markdown("---")
    st.markdown("### 使い方")
    st.markdown("1. チャンネルを選択")
    st.markdown("2. 動画一覧から分析したい動画を選択")
    st.markdown("3. 分析画面で詳細データを確認")
    st.markdown("---")
    st.caption("Powered by Streamlit & Supabase")

# メインコンテンツ
st.title("📺 YouTube チャンネル一覧")
st.markdown("分析したいYouTubeチャンネルを選択してください。")

# チャンネル検索フィルター
search_query = st.text_input("🔍 チャンネル名で検索", "")

# データロード中の表示
with st.spinner("チャンネルデータを読み込み中..."):
    # チャンネルデータの取得
    channels = get_channels()
    
    if not channels:
        st.error("チャンネルデータの取得に失敗しました。Supabase接続を確認してください。")
        st.stop()

# DataFrameに変換
channels_df = pd.DataFrame(channels)

# 検索フィルタリング
if search_query:
    filtered_channels = channels_df[
        channels_df['title'].str.contains(search_query, case=False, na=False)
    ]
else:
    filtered_channels = channels_df

# チャンネル数の表示
st.markdown(f"### 全 {len(filtered_channels)} チャンネル")

# チャンネル一覧表示
if not filtered_channels.empty:
    # テーブルヘッダー
    header_cols = st.columns([3, 5, 1, 1])
    header_cols[0].markdown("#### チャンネル名")
    header_cols[1].markdown("#### 説明")
    header_cols[2].markdown("#### 動画数")
    header_cols[3].markdown("#### アクション")
    st.markdown("---")  # ヘッダーとデータの区切り線
    
    # チャンネル一覧を表形式で表示
    for _, channel in filtered_channels.iterrows():
        cols = st.columns([3, 5, 1, 1])
        
        # チャンネル名
        cols[0].markdown(f"**{channel['title']}**")
        
        # チャンネルの説明（最初の100文字まで）
        description = channel.get('description', '')
        if description:
            short_desc = description[:100] + ('...' if len(description) > 100 else '')
            cols[1].markdown(f"{short_desc}")
        else:
            cols[1].markdown("*説明なし*")
        
        # チャンネルの動画数
        video_count = channel.get('video_count', '不明')
        cols[2].markdown(f"{video_count}")
        
        # チャンネル選択ボタン
        if cols[3].button("選択", key=f"select_channel_{channel['id']}"):
            # セッション状態にチャンネルIDを保存
            st.session_state['cid'] = channel['id']
            
            # 動画一覧ページに遷移
            st.switch_page("pages/01_Videos.py")
        
        st.markdown("---")  # 各行の区切り線

else:
    st.info("条件に一致するチャンネルがありません。検索条件を変更してください。")
