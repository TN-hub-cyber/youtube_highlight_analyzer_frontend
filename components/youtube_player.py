import streamlit as st
import streamlit.components.v1 as components
from utils.formatting import format_time

def youtube_player(video_id, width=700, height=400, start_seconds=0, auto_play=True, 
                   show_seek_buttons=False, seek_points=None):
    """
    YouTube IFrame Player APIを使用したカスタムプレイヤーコンポーネント
    
    Args:
        video_id: YouTube動画ID
        width: プレイヤーの幅
        height: プレイヤーの高さ
        start_seconds: 開始位置（秒）
        auto_play: 自動再生するかどうか
        show_seek_buttons: シークボタンを表示するかどうか
        seek_points: シークボタンで移動する時間点のリスト [(秒, ラベル), ...]
    
    Returns:
        現在の再生位置（秒）を返すコンポーネント
    """
    # 現在の再生位置がセッション状態にない場合は初期化
    if 'current_time' not in st.session_state:
        st.session_state.current_time = start_seconds
    
    # シーク命令がある場合、start_secondsにセットする
    if 'sec' in st.session_state:
        start_seconds = st.session_state['sec']
        del st.session_state['sec']  # 使用したらクリア
    
    # シークボタンのHTML生成（必ず表示されるようにデバッグ情報も追加）
    seek_buttons_html = ""
    if show_seek_buttons and seek_points:
        seek_buttons_html = f'''
        <div class="seek-buttons" style="margin-top:10px;display:flex;flex-wrap:wrap;gap:5px;">
            <div style="width:100%;margin-bottom:5px;font-weight:bold;color:#444;font-size:14px;">
                チャプタージャンプ ({len(seek_points)}件)
            </div>
        '''
        
        # ボタン数のカウンター（デバッグ用）
        button_count = 0
        
        for i, (sec, label) in enumerate(seek_points):
            # HTMLとJSの安全なエスケープ処理
            safe_label = str(label).replace('"', '&quot;').replace("'", "&apos;")
            
            # すべてのボタンを表示（制限なし）
            seek_buttons_html += f'''
            <button onclick="seekTo({sec})" 
                    style="padding:5px 8px;background:#f0f0f0;border:1px solid #ddd;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;">
                {safe_label}
            </button>
            '''
            button_count += 1
        
        # デバッグ情報を追加（開発中のみ、後で削除可能）
        seek_buttons_html += f'''
            <script>
                console.log("シークボタン生成完了: {button_count}個のボタンを表示");
            </script>
        </div>
        '''
    
    # JavaScriptのコード
    player_code = f"""
    <div id="youtube_player_container" style="width:{width}px;margin:0 auto;">
        <div id="player" style="width:{width}px;height:{height}px;"></div>
        {seek_buttons_html}
    </div>
    
    <script>
        // グローバル変数
        var player;
        var playerReady = false;
        var lastTimeUpdate = 0;
        var updateInterval = 500; // 更新間隔（ミリ秒）
        
        // シーク関数の定義（フレーム内で直接使用できる）
        function seekTo(seconds) {{
            console.log('seekTo called with seconds:', seconds);
            if (player && playerReady) {{
                try {{
                    player.seekTo(seconds);
                    player.playVideo();
                    return true;
                }} catch (e) {{
                    console.error('Seek error:', e);
                    return false;
                }}
            }} else {{
                console.warn('Player not ready yet, cannot seek');
                return false;
            }}
        }};
        
        // グローバルなシーク関数も定義（外部スクリプトからの直接アクセス用）
        window.seekToYouTubeTime = seekTo;

        // YouTubeプレイヤーAPI読み込み
        var tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        
        // シークキューを作成（プレイヤー準備前に命令を受け取った場合用）
        var seekQueue = [];
        
        // プレイヤー初期化
        function onYouTubeIframeAPIReady() {{
            console.log('YouTube IFrame API Ready - プレイヤー初期化中');
            player = new YT.Player('player', {{
                videoId: '{video_id}',
                playerVars: {{
                    'autoplay': {1 if auto_play else 0},
                    'start': {start_seconds},
                    'rel': 0,
                    'fs': 1,
                    'modestbranding': 1
                }},
                events: {{
                    'onReady': onPlayerReady,
                    'onStateChange': onPlayerStateChange,
                    'onError': onPlayerError
                }}
            }});
            
            // グローバル関数としてシーク機能を公開（直接呼び出し用）
            window.seekYouTubePlayerTo = function(seconds) {{
                if (player && playerReady) {{
                    console.log("seekYouTubePlayerTo: " + seconds + "秒に移動");
                    player.seekTo(seconds);
                    if (player.getPlayerState() !== YT.PlayerState.PLAYING) {{
                        player.playVideo();
                    }}
                    return true;
                }} else {{
                    console.log("プレイヤー未準備: シーク命令をキューに追加 " + seconds + "秒");
                    seekQueue.push(seconds);
                    return false;
                }}
            }};
        }}
        
        // エラー処理
        function onPlayerError(event) {{
            console.error('YouTubeプレイヤーエラー:', event.data);
        }}
        
        // プレイヤー準備完了時
        function onPlayerReady(event) {{
            console.log('YouTubeプレイヤー準備完了');
            playerReady = true;
            
            // ティック機能を開始
            setInterval(tick, updateInterval);
            
            // キューに溜まったシーク命令を処理
            if (seekQueue.length > 0) {{
                console.log("キューに" + seekQueue.length + "個のシーク命令があります");
                var lastSeek = seekQueue[seekQueue.length - 1];
                player.seekTo(lastSeek);
                if (player.getPlayerState() !== YT.PlayerState.PLAYING) {{
                    player.playVideo();
                }}
                seekQueue = [];
            }}
        }}
        
        // プレイヤー状態変更時
        function onPlayerStateChange(event) {{
            // 再生中の場合のみティックを送信
            if (event.data == YT.PlayerState.PLAYING) {{
                tick();
            }}
        }}
        
        // 定期的に現在位置を送信
        function tick() {{
            if (player && player.getPlayerState() == YT.PlayerState.PLAYING) {{
                var currentTime = Math.floor(player.getCurrentTime());
                
                // 前回の更新から変化があった場合のみ送信
                if (currentTime != lastTimeUpdate) {{
                    lastTimeUpdate = currentTime;
                    
                    // Streamlitに現在位置を通知
                    try {{
                        window.parent.postMessage({{
                            type: 'tick',
                            sec: currentTime
                        }}, '*');
                        
                        // Componentへのメッセージ（SetValue用）
                        window.parent.postMessage({{
                            type: 'streamlit:setComponentValue',
                            value: currentTime
                        }}, '*');
                    }} catch (err) {{
                        console.error('現在位置の通知中にエラー:', err);
                    }}
                }}
            }}
        }}
        
        // シーク命令を受け取る - 複数のメッセージ形式に対応
        window.addEventListener('message', function(e) {{
            try {{
                // 文字列データの場合はJSONとしてパース
                var data = e.data;
                if (typeof data === 'string') {{
                    try {{
                        data = JSON.parse(data);
                    }} catch (parseErr) {{
                        // パースエラーは無視（文字列形式でない場合）
                    }}
                }}
                
                // TypeがSeekの場合
                if (data && data.type === 'seek' && typeof data.sec !== 'undefined') {{
                    console.log('シーク命令を受信: ' + data.sec + '秒');
                    window.seekYouTubePlayerTo(data.sec);
                }}
                
                // CommandがSeekの場合（代替形式）
                else if (data && data.command === 'seek' && typeof data.seconds !== 'undefined') {{
                    console.log('コマンド形式のシーク命令を受信: ' + data.seconds + '秒');
                    window.seekYouTubePlayerTo(data.seconds);
                }}
                
                // その他のメッセージは無視
            }} catch (err) {{
                console.error('メッセージ処理中にエラー:', err);
            }}
        }});
    </script>
    """
    
    # プレイヤーコンポーネントの高さを調整（ボタン表示スペース追加）
    component_height = height + 80 if show_seek_buttons and seek_points else height
    
    # プレイヤーを表示し、現在の再生位置を取得
    component_instance = components.html(player_code, height=component_height, width=width)
    
    # component_instanceの戻り値ではなく、セッション状態から現在の時間を取得
    if 'current_time' not in st.session_state:
        st.session_state.current_time = start_seconds
    
    return st.session_state.current_time


def player_controls(time_seconds=None, show_time=True):
    """
    プレイヤーコントロールエリアを表示
    
    Args:
        time_seconds: 表示する時間（秒）
        show_time: 時間を表示するかどうか
    """
    col1, col2 = st.columns([1, 9])
    
    with col1:
        st.button('▶️', on_click=seek_to, args=(time_seconds,), help="この位置から再生")
    
    with col2:
        if show_time and time_seconds is not None:
            st.text(f"🕒 {format_time(time_seconds)}")


def seek_to(time_seconds):
    """
    指定時間にシークするコールバック関数
    
    Args:
        time_seconds: シーク先の時間（秒）
    """
    if time_seconds is not None:
        st.session_state['sec'] = time_seconds


def create_seek_command(container=st):
    """
    シーク命令を送信するJavaScriptを作成
    
    Args:
        container: 命令を表示するStreamlitコンテナ
    """
    # セッション状態にシーク命令がある場合
    if 'sec' in st.session_state:
        sec = st.session_state['sec']
        
        # 大幅に改善したシーク命令を送信するJavaScript
        js_code = f"""
        <script>
        // デバッグ情報
        console.log('シーク命令: {sec}秒に移動します');
        
        // グローバルプレイヤー変数を探す試み
        function seekToPosition() {{
            // 方法1: グローバルなYouTubeプレイヤーオブジェクトを使用（最も信頼性が高い）
            if (typeof player !== 'undefined' && player && typeof player.seekTo === 'function') {{
                console.log('グローバルプレイヤーオブジェクトを使用します');
                player.seekTo({sec});
                if (player.getPlayerState() !== 1) {{ // 1はYT.PlayerState.PLAYING
                    player.playVideo();
                }}
                return true;
            }}
            
            // 方法2: YouTubeインターフェースを直接探す
            try {{
                var youtubeIframes = document.querySelectorAll('iframe[src*="youtube.com"]');
                if (youtubeIframes.length > 0) {{
                    for (var i = 0; i < youtubeIframes.length; i++) {{
                        // iframeのYouTubeプレイヤーオブジェクトにアクセスを試みる
                        // 注：Same-Originポリシーにより通常は失敗するが、実験的に試みる
                        try {{
                            var target = {{
                                'command': 'seek',
                                'seconds': {sec}
                            }};
                            youtubeIframes[i].contentWindow.postMessage(JSON.stringify(target), '*');
                            console.log('YouTube iframe[' + i + ']にシーク命令を送信しました');
                        }} catch (e) {{
                            console.log('iframe[' + i + ']へのアクセスに失敗: ' + e);
                        }}
                    }}
                    
                    // 通信がうまくいかない場合はページをリロード
                    setTimeout(function() {{
                        var url = new URL(window.location.href);
                        url.searchParams.set('t', {sec});
                        console.log('t={sec}のURLパラメータを付与してリロードします');
                        // window.location.href = url.toString();
                    }}, 3000);
                }}
            }} catch (err) {{
                console.error('ブラウザセキュリティ制限によりiframeへの直接アクセスが制限されています:', err);
            }}
            
            return false;
        }}
        
        // 最初の試行
        var succeeded = seekToPosition();
        
        // 失敗した場合は少し遅延して再試行（DOM完全読み込み後）
        if (!succeeded) {{
            setTimeout(seekToPosition, 1000);
            // 3秒後に最終試行
            setTimeout(seekToPosition, 3000);
        }}
        </script>
        """
        
        # JavaScriptを実行
        container.components.v1.html(js_code, height=0)
        
        # デバッグ情報（運用環境では無効化）
        # st.info(f"DEBUG: シーク命令 {sec}秒")
        
        # 命令をクリア
        del st.session_state['sec']
