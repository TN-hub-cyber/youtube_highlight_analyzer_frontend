import streamlit as st
import streamlit.components.v1 as components
from utils.formatting import format_time

def youtube_player(video_id, width=700, height=400, start_seconds=0, auto_play=True):
    """
    YouTube IFrame Player APIを使用したカスタムプレイヤーコンポーネント
    
    Args:
        video_id: YouTube動画ID
        width: プレイヤーの幅
        height: プレイヤーの高さ
        start_seconds: 開始位置（秒）
        auto_play: 自動再生するかどうか
    
    Returns:
        現在の再生位置（秒）を返すコンポーネント
    """
    # 現在の再生位置がセッション状態にない場合は初期化
    if 'current_time' not in st.session_state:
        st.session_state.current_time = start_seconds
    
    # JavaScriptのコード
    player_code = f"""
    <div id="player" style="width:{width}px;height:{height}px;margin:0 auto;"></div>
    
    <script>
        // YouTubeプレイヤーAPI読み込み
        var tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        
        var player;
        var lastTimeUpdate = 0;
        var updateInterval = 500; // 更新間隔（ミリ秒）
        
        // プレイヤー初期化
        function onYouTubeIframeAPIReady() {{
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
                    'onStateChange': onPlayerStateChange
                }}
            }});
        }}
        
        // プレイヤー準備完了時
        function onPlayerReady(event) {{
            // ティック機能を開始
            setInterval(tick, updateInterval);
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
                    window.parent.postMessage({{
                        type: 'tick',
                        sec: currentTime
                    }}, '*');
                    
                    // Componentへのメッセージ（SetValue用）
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: currentTime
                    }}, '*');
                }}
            }}
        }}
        
        // シーク命令を受け取る
        window.addEventListener('message', function(e) {{
            if (e.data.type === 'seek' && player) {{
                player.seekTo(e.data.sec);
                if (player.getPlayerState() != YT.PlayerState.PLAYING) {{
                    player.playVideo(); // シーク後に再生開始
                }}
            }}
        }});
    </script>
    """
    
    # プレイヤーを表示し、現在の再生位置を取得
    component_instance = components.html(player_code, height=height, width=width)
    
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
        
        # シーク命令を送信するJavaScript（デバッグ情報を追加）
        js_code = f"""
        <script>
        // デバッグ情報
        console.log('シーク命令: {sec}秒に移動します');
        
        // YouTubeプレイヤーにシーク命令を送信
        var message = {{
            type: 'seek',
            sec: {sec}
        }};
        
        // スマートなセレクタを使用してYouTubeプレイヤーのiframeを探す
        function findYouTubeIframe() {{
            // ID付きのYouTubeプレイヤー要素を探す
            var playerDiv = document.getElementById('player');
            if (playerDiv && playerDiv.querySelector('iframe')) {{
                return playerDiv.querySelector('iframe');
            }}
            
            // class名でYouTube iframeを探す
            var youtubeFrames = document.querySelectorAll('iframe[src*="youtube.com"]');
            if (youtubeFrames.length > 0) {{
                return youtubeFrames[0];
            }}
            
            // 全てのiframeを返す（最後の手段）
            return document.getElementsByTagName('iframe');
        }}
        
        var youtubeIframes = findYouTubeIframe();
        
        // 単一の要素の場合
        if (youtubeIframes.tagName === 'IFRAME') {{
            console.log('YouTube iframeが見つかりました');
            try {{
                youtubeIframes.contentWindow.postMessage(message, '*');
                console.log('シーク命令を送信しました:', message);
            }} catch(err) {{
                console.error('シーク命令の送信中にエラーが発生しました:', err);
            }}
        }} 
        // 複数要素のコレクションの場合
        else if (youtubeIframes.length > 0) {{
            console.log('iframeが' + youtubeIframes.length + '個見つかりました');
            for (var i = 0; i < youtubeIframes.length; i++) {{
                try {{
                    youtubeIframes[i].contentWindow.postMessage(message, '*');
                    console.log('iframe[' + i + ']にシーク命令を送信しました');
                }} catch(err) {{
                    console.error('iframe[' + i + ']へのシーク命令の送信中にエラー:', err);
                }}
            }}
        }} else {{
            console.error('YouTubeプレイヤーIFrameが見つかりません');
        }}
        
        // ウィンドウにも送信（iframe内のコードが親ウィンドウをリッスンしている場合）
        try {{
            window.postMessage(message, '*');
            console.log('ウィンドウにもシーク命令を送信しました');
        }} catch(err) {{
            console.error('ウィンドウへのシーク命令の送信中にエラー:', err);
        }}
        </script>
        """
        
        # JavaScriptを実行
        container.components.v1.html(js_code, height=0)
        
        # デバッグ情報（開発時のみ表示）
        # st.info(f"DEBUG: シーク命令 {sec}秒")
        
        # 命令をクリア
        del st.session_state['sec']
