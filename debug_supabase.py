import os
import sys
import pathlib
from supabase import create_client

# プロジェクトルートの取得
project_root = pathlib.Path(__file__).parent.absolute()

# Supabase接続情報（ハードコード）
SUPABASE_URL = "https://crzdckxjivovcvtnrmwg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyemRja3hqaXZvdmN2dG5ybXdnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzc3NzEsImV4cCI6MjA2MDcxMzc3MX0.mfvta0xzbnTc_PQWlIb9mSvBUr4c7GsNZydV7vgAKsQ"

print("--- Supabase接続テスト ---")
print(f"URL: {SUPABASE_URL}")
print(f"KEY: {SUPABASE_KEY[:10]}...{SUPABASE_KEY[-10:]}")

try:
    print("接続試行中...")
    
    # Supabaseクライアントの作成
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("クライアント作成成功")
    
    # テストクエリ実行
    response = supabase.table("youtube_channels").select("*").limit(1).execute()
    print(f"テストクエリ実行結果: {response}")
    
    if response.data:
        print(f"データ取得成功: {len(response.data)}件")
        print(f"最初のレコード: {response.data[0]}")
    else:
        print("データ取得成功、結果は空です。")
    
    print("--- 接続テスト成功 ---")

except Exception as e:
    print(f"エラー発生: {e}")
    print(f"エラータイプ: {type(e)}")
    print("--- 接続テスト失敗 ---")
    sys.exit(1)
