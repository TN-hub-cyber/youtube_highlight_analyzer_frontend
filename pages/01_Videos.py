import streamlit as st
import pandas as pd
from utils.supabase_client import get_videos_by_channel
from utils.formatting import format_time

# ページ設定
st.set_page_config(
    page_title="YouTube分析 - 動画一覧",
    page_icon="🎬",
    layout="wide"
)

# サイドバー
with st.sidebar:
    st.title("YouTube動画分析")
    st.markdown("---")
    
    # ホームに戻るボタン
    if st.button("← チャンネル一覧に戻る"):
        if 'cid' in st.session_state:
            del st.session_state['cid']  # チャンネルID情報をクリア
        st.switch_page("Home.py")
    
    st.markdown("---")
    st.caption("Powered by Streamlit & Supabase")

# チャンネルIDがセッション状態にあるか確認
if 'cid' not in st.session_state:
    st.warning("チャンネルが選択されていません。チャンネル一覧から選択してください。")
    if st.button("チャンネル一覧に戻る"):
        st.switch_page("Home.py")
    st.stop()

# メインコンテンツ
channel_id = st.session_state['cid']

# データロード中の表示
with st.spinner("動画データを読み込み中..."):
    # 動画データの取得
    videos = get_videos_by_channel(channel_id)
    
    if not videos:
        st.error("動画データの取得に失敗しました。")
        st.stop()

# DataFrameに変換
videos_df = pd.DataFrame(videos)

# ページタイトル
channel_title = videos_df.iloc[0].get('channel_title', 'チャンネル') if not videos_df.empty else 'チャンネル'
st.title(f"🎬 {channel_title} の動画一覧")

# 検索フィルター
search_query = st.text_input("🔍 動画タイトルで検索", "")

# 並び替えオプション
sort_options = ['公開日（新しい順）', '公開日（古い順）', '再生回数（多い順）', '再生回数（少ない順）', 'タイトル（A-Z）', 'タイトル（Z-A）']
sort_option = st.selectbox("並び替え", sort_options)

# 検索フィルタリング
if search_query:
    filtered_videos = videos_df[
        videos_df['title'].str.contains(search_query, case=False, na=False)
    ]
else:
    filtered_videos = videos_df

# 並び替え
if sort_option == '公開日（新しい順）':
    filtered_videos = filtered_videos.sort_values('published_at', ascending=False)
elif sort_option == '公開日（古い順）':
    filtered_videos = filtered_videos.sort_values('published_at', ascending=True)
elif sort_option == '再生回数（多い順）':
    filtered_videos = filtered_videos.sort_values('view_count', ascending=False)
elif sort_option == '再生回数（少ない順）':
    filtered_videos = filtered_videos.sort_values('view_count', ascending=True)
elif sort_option == 'タイトル（A-Z）':
    filtered_videos = filtered_videos.sort_values('title', ascending=True)
elif sort_option == 'タイトル（Z-A）':
    filtered_videos = filtered_videos.sort_values('title', ascending=False)

# 動画数の表示
st.markdown(f"### 全 {len(filtered_videos)} 動画")

# ページネーション
VIDEOS_PER_PAGE = 10
total_pages = (len(filtered_videos) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE

# ページネーションコントロール
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    # ページネーションを初期化
    if 'video_page' not in st.session_state:
        st.session_state['video_page'] = 0
    
    current_page = st.session_state['video_page']
    
    # 前後ページボタン
    c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
    
    with c1:
        if st.button("◀️ 最初", disabled=current_page == 0):
            st.session_state['video_page'] = 0
            st.rerun()
    
    with c2:
        if st.button("◀️ 前へ", disabled=current_page == 0):
            st.session_state['video_page'] = max(0, current_page - 1)
            st.rerun()
    
    with c3:
        st.markdown(f"**{current_page + 1} / {max(1, total_pages)}**")
    
    with c4:
        if st.button("次へ ▶️", disabled=current_page >= total_pages - 1):
            st.session_state['video_page'] = min(total_pages - 1, current_page + 1)
            st.rerun()
    
    with c5:
        if st.button("最後 ▶️", disabled=current_page >= total_pages - 1):
            st.session_state['video_page'] = total_pages - 1
            st.rerun()

# 現在のページの動画を表示
start_idx = current_page * VIDEOS_PER_PAGE
end_idx = min(start_idx + VIDEOS_PER_PAGE, len(filtered_videos))
current_videos = filtered_videos.iloc[start_idx:end_idx]

# 動画一覧表示
if not current_videos.empty:
    for _, video in current_videos.iterrows():
        with st.container():
            cols = st.columns([3, 7])
            
            with cols[0]:
                # サムネイル画像があれば表示
                if 'thumbnail_url' in video and video['thumbnail_url']:
                    st.image(video['thumbnail_url'], use_column_width=True)
                else:
                    st.markdown("*サムネイルなし*")
            
            with cols[1]:
                # 動画タイトル
                st.markdown(f"### {video['title']}")
                
                # 動画情報
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # published_atがNoneの場合のチェックを追加
                    published_date = '不明'
                    if 'published_at' in video and video['published_at'] is not None:
                        try:
                            published_date = pd.to_datetime(video['published_at']).strftime('%Y/%m/%d')
                        except:
                            pass
                    st.markdown(f"**公開日**: {published_date}")
                
                with col2:
                    duration = format_time(video['duration']) if 'duration' in video else '不明'
                    st.markdown(f"**長さ**: {duration}")
                
                with col3:
                    view_count = f"{video['view_count']:,}" if 'view_count' in video else '不明'
                    st.markdown(f"**再生回数**: {view_count}")
                
                # 動画選択ボタン
                if st.button("分析する", key=f"select_video_{video['id']}"):
                    # セッション状態に動画IDを保存
                    st.session_state['vid'] = video['id']
                    st.session_state['youtube_video_id'] = video['video_id']
                    
                    # 分析ページに遷移
                    st.switch_page("pages/02_Analysis.py")
            
            st.markdown("---")
else:
    st.info("条件に一致する動画がありません。検索条件を変更してください。")
