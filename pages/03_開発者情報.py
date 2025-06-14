import streamlit as st

# --------------------------------------------------
# ページ設定
# --------------------------------------------------
st.set_page_config(
    page_title="YouTube分析 - 開発者情報",
    page_icon="ℹ️",
    layout="wide"
)

# --------------------------------------------------
# システム関連図関数定義
# --------------------------------------------------
def show_system_architecture():
    """システム構成図を表示"""
    system_graph = """
    digraph {
        rankdir=LR
        node [shape=box style="rounded,filled" fontname="Meiryo"]
        edge [fontname="Meiryo"]
        
        subgraph cluster_user {
            label="ユーザー環境"
            style=filled
            color=lightgrey
            Browser [label="ブラウザ" color="#4c78a8" fontcolor="white"]
        }
        
        subgraph cluster_frontend {
            label="フロントエンド"
            style=filled
            color=lightblue
            Streamlit [label="Streamlit アプリ\\n(Python)" color="#ff4b4b" fontcolor="white"]
        }
        
        subgraph cluster_backend {
            label="データレイヤー"
            style=filled
            color=lightgreen
            Supabase [label="Supabase\\n(PostgreSQL)" color="#3ecf8e" fontcolor="white"]
        }
        
        subgraph cluster_external {
            label="外部API"
            style=filled
            color=lightyellow
            YouTube [label="YouTube\\nData API" color="#ff0000" fontcolor="white"]
        }
        
        subgraph cluster_processing {
            label="分析処理"
            style=filled
            color=lightcoral
            Backend [label="分析エンジン\\n(Python)" color="#666666" fontcolor="white"]
        }
        
        Browser -> Streamlit [label="HTTPS"]
        Streamlit -> Supabase [label="REST API\\n(データ取得)"]
        Backend -> Supabase [label="データ保存"]
        Backend -> YouTube [label="メタデータ取得" style=dashed]
        Backend -> Backend [label="音声・チャット分析\\n(処理詳細は非公開)" style=dotted]
    }
    """
    
    st.graphviz_chart(system_graph, use_container_width=True)

def show_user_workflow():
    """ユーザーワークフロー図を表示"""
    workflow_graph = """
    digraph {
        rankdir=TB
        node [shape=box style="rounded,filled" fontname="Meiryo"]
        edge [fontname="Meiryo"]
        
        Start [label="開始" shape=ellipse color="#4c78a8" fontcolor="white"]
        
        subgraph cluster_selection {
            label="Step 1: 選択"
            style=filled
            color=lightblue
            ChannelList [label="チャンネル一覧\\n表示" color="#ff4b4b" fontcolor="white"]
            VideoList [label="動画一覧\\n表示" color="#ff4b4b" fontcolor="white"]
            VideoSelect [label="動画選択" color="#ff4b4b" fontcolor="white"]
        }
        
        subgraph cluster_analysis {
            label="Step 2: 分析・可視化"
            style=filled
            color=lightgreen
            Player [label="YouTube\\nプレイヤー" color="#ff0000" fontcolor="white"]
            Metrics [label="メトリクス\\nグラフ" color="#636efa" fontcolor="white"]
            Comments [label="コメント\\n分析" color="#00cc96" fontcolor="white"]
            Highlights [label="ハイライト\\nセグメント" color="#ab63fa" fontcolor="white"]
            Transcripts [label="文字起こし\\nデータ" color="#ffa15a" fontcolor="white"]
        }
        
        subgraph cluster_interaction {
            label="Step 3: インタラクション"
            style=filled
            color=lightyellow
            TimeJump [label="時間ジャンプ" color="#19d3f3" fontcolor="white"]
            Search [label="検索・フィルタ" color="#ff6692" fontcolor="white"]
            Export [label="結果エクスポート" color="#b6e880" fontcolor="white"]
        }
        
        Start -> ChannelList
        ChannelList -> VideoList
        VideoList -> VideoSelect
        VideoSelect -> Player
        VideoSelect -> Metrics
        VideoSelect -> Comments
        VideoSelect -> Highlights
        VideoSelect -> Transcripts
        
        Metrics -> TimeJump [label="クリック"]
        Comments -> Search [label="キーワード検索"]
        Highlights -> TimeJump [label="セグメント選択"]
        Transcripts -> Search [label="テキスト検索"]
        
        TimeJump -> Player [label="再生位置更新"]
        Search -> Comments [style=dashed]
        Search -> Transcripts [style=dashed]
    }
    """
    
    st.graphviz_chart(workflow_graph, use_container_width=True)

def show_data_flow():
    """データフロー図を表示"""
    dataflow_graph = """
    digraph {
        rankdir=LR
        node [shape=box style="rounded,filled" fontname="Meiryo"]
        edge [fontname="Meiryo"]
        
        subgraph cluster_input {
            label="入力データ"
            style=filled
            color=lightcyan
            Video [label="YouTube動画" color="#ff0000" fontcolor="white"]
            Audio [label="音声データ" color="#ffa500" fontcolor="white"]
            Chat [label="チャットログ" color="#9370db" fontcolor="white"]
            Meta [label="メタデータ" color="#32cd32" fontcolor="white"]
        }
        
        subgraph cluster_processing {
            label="分析処理"
            style=filled
            color=lightgray
            Analytics [label="分析エンジン\\n(詳細非公開)" color="#696969" fontcolor="white"]
        }
        
        subgraph cluster_storage {
            label="データ保存"
            style=filled
            color=lightgreen
            DB [label="Supabase\\nデータベース" color="#3ecf8e" fontcolor="white"]
        }
        
        subgraph cluster_output {
            label="出力・可視化"
            style=filled
            color=lightblue
            WebApp [label="Streamlit\\nWebアプリ" color="#ff4b4b" fontcolor="white"]
            Charts [label="インタラクティブ\\nグラフ" color="#636efa" fontcolor="white"]
            Reports [label="分析レポート" color="#00cc96" fontcolor="white"]
        }
        
        Video -> Analytics
        Audio -> Analytics
        Chat -> Analytics
        Meta -> Analytics
        
        Analytics -> DB [label="構造化データ"]
        
        DB -> WebApp [label="REST API"]
        WebApp -> Charts
        WebApp -> Reports
        
        Charts -> WebApp [label="ユーザー操作" style=dashed]
    }
    """
    
    st.graphviz_chart(dataflow_graph, use_container_width=True)

# --------------------------------------------------
# サイドバー（他ページと共通化）
# --------------------------------------------------
with st.sidebar:
    st.title("YouTube動画分析")
    st.markdown("---")

    if st.button("← チャンネル一覧に戻る"):
        st.switch_page("Home.py")

    st.markdown("---")
    st.caption("Powered by Streamlit & Supabase")

# --------------------------------------------------
# メインコンテンツ
# --------------------------------------------------
st.title("ℹ️ 開発者情報")

# -------------------- プロフィール -------------------
st.header("プロフィール")
col1, col2 = st.columns([1, 2])

with col1:
    st.image("assets/profile.png", width=150)  # 👈 画像パスを差し替え
    # 実際の画像がある場合は下記のようにパスを指定
    # st.image("assets/profile.jpg", width=150)

with col2:
    st.subheader("そらまめ (soramame)")
    st.markdown("""
- **職業**: システムエンジニア／プロジェクトマネージャー  
- **専門**: CI/CD・AI／ビッグデータ活用／会計・人事システム構築
- **実績ハイライト**  
    - 食品製造・不動産向け **会計／連結会計／電子帳票／経費精算／人事** など
      大規模基幹システムを PM として統括
    - BIツールを用いたデータ分析システム構築(Power BI, Tableau, Microsoft SSMS/SSAS etc.)
    - GitLab CI/CD＋SonarQube で Java／Next.js プロジェクトの品質ゲート導入  
    - **YouTube ハイライト自動生成サービス** を個人開発  
- **スキルセット**  
    - Python・Streamlit・Supabase・PostgreSQL  
    - GitLab CI/CD・Docker・SonarQube  
    - AWS（ECS／ALB／Cognito ほか）  
    - 簿記・会計インストラクター経験
    - PMP（Project Management Professional）インストラクター経験※PMP資格保持
    """)

# -------------------- 連絡先 -------------------------
st.header("連絡先")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### ✉️ メール\nsoramame939@gmail.com")
with c2:
    st.markdown("### 🌐 Web\n[example.com](https://example.com)")
with c3:
    st.markdown("### 💼 SNS\n[Twitter](https://x.com/sor24921490)")

# -------------------- プロジェクト概要 --------------
st.header("プロジェクトについて")
st.markdown("""
YouTube チャンネルや動画を分析し、  
コメント・感情・音量など複数の指標から **ハイライトシーン** を自動抽出するツールです。
""")

with st.expander("主な機能を見る", expanded=False):
    st.markdown("""
- チャンネル／動画一覧の閲覧  
- チャプター表示  
- コメント／キーワード検索  
- 音声感情の可視化  
- 配信者文字起こし
- ハイライトの自動検出とタイムスタンプ生成
""")

# -------------------- 使用技術 -----------------------
st.header("使用技術")
fc, bc = st.columns(2)
with fc:
    st.markdown("### フロントエンド")
    st.markdown("- Streamlit\n- Python\n- Pandas\n- Plotly")
with bc:
    st.markdown("### バックエンド")
    st.markdown("- Supabase (PostgreSQL)\n- YouTube Data API")

# -------------------- システム構成図 -----------------
st.header("システム構成")

# 既存のシンプルな構成図
st.subheader("🔧 基本構成")
st.markdown("システム全体の基本的な構成図です。")

graph_code = r'''
digraph {
  rankdir=LR
  node [shape=box style="rounded,filled" color="#4c78a8" fontcolor="white" fontname="Meiryo"]
  edge [fontname="Meiryo"]

  Browser  [label="ユーザーのブラウザ"]
  Streamlit [label="Streamlit アプリ\n(Python)"]
  Supabase [label="Supabase\n(データベース)"]
  YTAPI    [label="YouTube Data API" color="#a05d56"]

  Browser  -> Streamlit  [label="HTTP(S)"]
  Streamlit -> Supabase  [label="SQL / REST"]
  Streamlit -> YTAPI     [style=dashed label="動画メタ取得"]
}
'''
st.graphviz_chart(graph_code, use_container_width=True)

# 詳細なシステム関連図（タブ形式）
st.subheader("🏗️ 詳細システム関連図")
st.markdown("システムの詳細な構成と処理フローを複数の視点から表現しています。")

tab1, tab2, tab3 = st.tabs(["システム構成", "ユーザーワークフロー", "データフロー"])

with tab1:
    st.markdown("### システム全体のアーキテクチャ")
    show_system_architecture()
    st.markdown("""
    **システム構成の特徴:**
    - **フロントエンド**: Streamlit による直感的なWeb UI
    - **データベース**: Supabase (PostgreSQL) による堅牢なデータ管理
    - **分析エンジン**: Python による高度な動画・音声・テキスト分析
    - **外部連携**: YouTube Data API によるメタデータ取得
    """)

with tab2:
    st.markdown("### ユーザーの操作フロー")
    show_user_workflow()
    st.markdown("""
    **ユーザーエクスペリエンス:**
    1. **チャンネル・動画選択**: 直感的なリスト表示
    2. **多角的分析**: 音声、コメント、感情、ハイライトの総合分析
    3. **インタラクティブ操作**: クリック一つで動画の該当シーンにジャンプ
    4. **検索・フィルタ**: キーワードや時間軸での絞り込み
    """)

with tab3:
    st.markdown("### データ処理の流れ")
    show_data_flow()
    st.markdown("""
    **データ処理の流れ:**
    - **多様な入力**: 動画、音声、チャット、メタデータを統合分析
    - **高度な分析**: 機械学習と信号処理による自動ハイライト検出
    - **リアルタイム可視化**: Plotlyによるインタラクティブなグラフ表示
    - **効率的なデータ管理**: Supabaseによる高速データアクセス
    """)

# -------------------- 技術的特徴 ---------------------
st.header("技術的特徴")

feat1, feat2 = st.columns(2)

with feat1:
    st.markdown("""
    ### 🎯 分析機能
    - **マルチモーダル分析**: 音声、テキスト、感情を統合
    - **リアルタイム処理**: 高速な分析とレスポンス
    - **インタラクティブUI**: 直感的な操作性
    - **自動ハイライト検出**: AIによる見どころ抽出
    """)

with feat2:
    st.markdown("""
    ### 🔧 技術スタック
    - **スケーラブル**: クラウドベースのアーキテクチャ
    - **高可用性**: Supabaseによる安定したデータ管理
    - **レスポンシブ**: モバイル対応のWebUI
    - **拡張性**: モジュラー設計による機能追加の容易さ
    """)

st.markdown("---")
st.caption("🚀 本プロジェクトは継続的に改善・機能追加を行っています")