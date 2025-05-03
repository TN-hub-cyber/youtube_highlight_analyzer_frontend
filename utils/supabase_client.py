import os
import pathlib
from dotenv import load_dotenv
from supabase import create_client
import streamlit as st
from utils.data_utils import client_side_metrics_agg, client_side_multi_term_comment_hist, client_side_search_comments_multi

# プロジェクトルートの絶対パスを取得
project_root = pathlib.Path(__file__).parent.parent.absolute()

# .envファイルの絶対パスを指定して読み込む
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path=str(dotenv_path))

# 環境変数から接続情報を取得
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 環境変数が取得できない場合、ハードコードされた値をバックアップとして使用
# 本番環境では使用しないことが推奨されますが、開発環境では便利です
if not SUPABASE_URL or not SUPABASE_KEY:
    # プロジェクトで提供された接続情報をフォールバックとして使用
    SUPABASE_URL = "https://crzdckxjivovcvtnrmwg.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyemRja3hqaXZvdmN2dG5ybXdnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzc3NzEsImV4cCI6MjA2MDcxMzc3MX0.mfvta0xzbnTc_PQWlIb9mSvBUr4c7GsNZydV7vgAKsQ"

def show_connection_error(st):
    """
    Supabase接続情報が設定されていない場合のエラーメッセージを表示
    
    Args:
        st: Streamlitモジュール（競合を避けるために引数として渡す）
    """
    st.error("""
    Supabase接続情報が設定されていません。
    以下のいずれかの方法で設定してください：
    
    1. .envファイルをプロジェクトルートに作成し、以下の内容を設定
       ```
       SUPABASE_URL=your_supabase_url
       SUPABASE_KEY=your_supabase_key
       ```
    
    2. Streamlit Cloudにデプロイする場合は、シークレット設定で環境変数を設定
    """)

# グローバル変数としてのクライアントインスタンス
supabase = None

def init_supabase():
    """
    Supabaseクライアントを初期化する
    import時には実行されないよう関数として定義
    """
    global supabase
    
    if supabase is not None:
        return supabase
        
    # クライアント作成（バージョン1.0.3対応）
    try:
        # 直接URLとキーだけを指定して作成
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        # エラーはログに記録するだけで、表示はアプリ側で行う
        print(f"Supabase接続エラー: {e}")
        return None

def get_supabase_client(st=None):
    """
    Supabaseクライアントのインスタンスを返す
    初回呼び出し時に初期化を行う
    
    Args:
        st: Streamlitモジュール（キャッシュに使用、オプション）
    """
    global supabase
    
    # すでに初期化されていればそれを返す
    if supabase is not None:
        return supabase
    
    # 初期化されていなければ初期化する
    if st is None:
        # streamlitなしで初期化
        return init_supabase()
    else:
        # streamlitのキャッシュを使って初期化
        @st.cache_resource
        def cached_init():
            return init_supabase()
        return cached_init()

# 基本的なデータアクセス関数
@st.cache_data(ttl=60)
def get_channels():
    """チャンネル一覧を取得"""
    if supabase is None:
        return []
    try:
        response = supabase.table("youtube_channels").select("*").execute()
        return response.data
    except Exception as e:
        print(f"チャンネル一覧の取得エラー: {e}")
        return []

@st.cache_data(ttl=60)
def get_videos_by_channel(channel_id):
    """指定されたチャンネルの動画一覧を取得"""
    if supabase is None:
        return []
    try:
        response = supabase.table("videos").select("*").eq("channel_id", channel_id).order("published_at", desc=True).execute()
        return response.data
    except Exception as e:
        print(f"動画一覧の取得エラー: {e}")
        return []

@st.cache_data(ttl=60)
def get_video_details(video_id):
    """指定された動画の詳細情報を取得"""
    if supabase is None:
        return None
    try:
        # single()を使わず、最初の結果を取得する方法に変更
        response = supabase.table("videos").select("*").eq("video_id", video_id).limit(1).execute()
        
        # レスポンスのデータ内に結果があるか確認
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            print(f"動画詳細情報が見つかりません: video_id={video_id}")
            # 内部ID（数値ID）で検索を試みる
            try:
                vid_int = int(video_id)
                response = supabase.table("videos").select("*").eq("id", vid_int).limit(1).execute()
                if response.data and len(response.data) > 0:
                    return response.data[0]
            except (ValueError, Exception):
                # 数値に変換できない場合は何もしない
                pass
                
            # デフォルト値を返す
            return {
                'id': video_id,
                'video_id': video_id,
                'title': '動画情報取得エラー',
                'description': '',
                'duration': 0,
                'view_count': 0,
                'comment_count': 0
            }
    except Exception as e:
        print(f"動画詳細情報の取得エラー: {e}")
        # デフォルト値を返す
        return {
            'id': video_id,
            'video_id': video_id,
            'title': '動画情報取得エラー',
            'description': '',
            'duration': 0,
            'view_count': 0,
            'comment_count': 0
        }

# RPC関数呼び出し
@st.cache_data(ttl=60)
def get_metrics_agg(video_id, granularity=5):
    """メトリクスデータ集計を取得"""
    if supabase is None:
        return []
    try:
        # まずRPC関数を試す
        try:
            response = supabase.rpc("metrics_agg", {"_vid": video_id, "_g": granularity}).execute()
            if response.data:
                return response.data
        except Exception as rpc_error:
            print(f"RPC metrics_agg エラー: {rpc_error}")
            # RPCが失敗した場合はクライアントサイド実装にフォールバック
            
        # クライアントサイド実装（フォールバック）
        print("クライアントサイドの集計処理を実行します")
        return client_side_metrics_agg(video_id, granularity)
    except Exception as e:
        print(f"メトリクスデータ取得エラー: {e}")
        return []

@st.cache_data(ttl=60)
def get_multi_term_comment_hist(video_id, terms, granularity=5):
    """複数検索語のコメント頻度集計を取得"""
    if supabase is None:
        return []
    try:
        # まずRPC関数を試す
        try:
            response = supabase.rpc("multi_term_comment_hist", {"_vid": video_id, "_terms": terms, "_g": granularity}).execute()
            if response.data:
                return response.data
        except Exception as rpc_error:
            print(f"RPC multi_term_comment_hist エラー: {rpc_error}")
            # RPCが失敗した場合はクライアントサイド実装にフォールバック
            
        # クライアントサイド実装（フォールバック）
        print("クライアントサイドのコメント頻度集計処理を実行します")
        return client_side_multi_term_comment_hist(video_id, terms, granularity)
    except Exception as e:
        print(f"コメント頻度データ取得エラー: {e}")
        return []

@st.cache_data(ttl=60)
def search_comments_multi(video_id, terms, match_type="any"):
    """複数検索語でのコメント検索結果を取得"""
    if supabase is None:
        return []
    try:
        # まずRPC関数を試す
        try:
            response = supabase.rpc("search_comments_multi", {"_vid": video_id, "_terms": terms, "_match_type": match_type}).execute()
            if response.data:
                return response.data
        except Exception as rpc_error:
            print(f"RPC search_comments_multi エラー: {rpc_error}")
            # RPCが失敗した場合はクライアントサイド実装にフォールバック
            
        # クライアントサイド実装（フォールバック）
        print("クライアントサイドのコメント検索処理を実行します")
        return client_side_search_comments_multi(video_id, terms, match_type)
    except Exception as e:
        print(f"コメント検索エラー: {e}")
        return []

# データ取得関数（チャプター、文字起こし、感情分析など）
@st.cache_data(ttl=60)
def get_chapters(video_id):
    """チャプター情報を取得"""
    if supabase is None:
        return []
    try:
        response = supabase.table("video_timestamps").select("*").eq("video_id", video_id).order("time_seconds").execute()
        return response.data
    except Exception as e:
        print(f"チャプターデータ取得エラー: {e}")
        return []

@st.cache_data(ttl=60)
def get_transcriptions(video_id):
    """文字起こし情報を取得"""
    if supabase is None:
        return []
    try:
        response = supabase.table("transcriptions").select("*").eq("video_id", video_id).order("time_seconds").execute()
        return response.data
    except Exception as e:
        print(f"文字起こしデータ取得エラー: {e}")
        return []

@st.cache_data(ttl=60)
def get_comments(video_id):
    """コメント情報を取得"""
    if supabase is None:
        return []
    try:
        response = supabase.table("chat_messages").select("*").eq("video_id", video_id).order("time_seconds").execute()
        return response.data
    except Exception as e:
        print(f"コメントデータ取得エラー: {e}")
        return []

@st.cache_data(ttl=60)
def get_emotion_analysis(video_id):
    """感情分析情報を取得"""
    if supabase is None:
        return []
    try:
        response = supabase.table("audio_emotion_analysis").select("*").eq("video_id", video_id).order("time_seconds").execute()
        return response.data
    except Exception as e:
        print(f"感情分析データ取得エラー: {e}")
        return []

@st.cache_data(ttl=60)
def get_volume_analysis(video_id):
    """音量分析情報を取得"""
    if supabase is None:
        return []
    try:
        response = supabase.table("volume_analysis").select("*").eq("video_id", video_id).order("time_seconds").execute()
        return response.data
    except Exception as e:
        print(f"音量分析データ取得エラー: {e}")
        return []

@st.cache_data(ttl=60)
def get_volume_analysis_secondly(video_id):
    """詳細音量分析情報を取得"""
    if supabase is None:
        return []
    try:
        response = supabase.table("volume_analysis_secondly").select("*").eq("video_id", video_id).order("time_seconds").execute()
        return response.data
    except Exception as e:
        print(f"詳細音量分析データ取得エラー: {e}")
        return []
