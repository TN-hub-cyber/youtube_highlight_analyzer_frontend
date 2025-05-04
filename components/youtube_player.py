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
    
    # セッション状態のデバッグ情報
    session_keys = [key for key in st.session_state.keys() if key in ['_seek_sec', 'sec', 'current_time']]
    print(f"YouTubeプレイヤー初期化時のセッション状態: {session_keys}")
    for key in session_keys:
        print(f"  {key}: {st.session_state.get(key)}")
    
    # 新しいシーク変数を確認（_seek_secがある場合はこちらを優先）
    seek_target = None
    if '_seek_sec' in st.session_state:
        seek_target = st.session_state['_seek_sec']
        print(f"シーク命令を検出: {seek_target}秒")
        # youtube_player.py内ではまだ削除しない（使用後にAnalysis.py側で削除）
    elif 'sec' in st.session_state:
        # 旧方式との互換性のため残す
        seek_target = st.session_state['sec']
        print(f"旧式シーク命令を検出: {seek_target}秒")
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
            
            // Streamlitから渡されたシーク命令を確認し実行（他タブからのジャンプ用）
            const seekTarget = {seek_target if seek_target is not None else 'null'};
            if (seekTarget !== null) {{
                console.log("Pythonから渡されたシーク命令を実行: " + seekTarget + "秒");
                player.seekTo(seekTarget, true);
                if (player.getPlayerState() !== YT.PlayerState.PLAYING) {{
                    player.playVideo();
                }}
                
                // 完了を通知（Analysis.py側でフラグをクリアするため）
                try {{
                    window.parent.postMessage({{type:'seek_completed'}}, '*');
                }} catch (e) {{}}
            }}
            
            // 既存のキューに溜まったシーク命令を処理
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


def seek_to(time_seconds, source_id=None):
    """
    指定時間にシークするコールバック関数
    
    Args:
        time_seconds: シーク先の時間（秒）
        source_id: シーク命令の発生源を示す識別子（オプション）
    """
    if time_seconds is not None:
        # ===== ステップ1: 呼び出し情報の記録 =====
        # 引数の時間値をローカル変数にコピーして明示的に処理
        target_seconds = float(time_seconds)
        
        # 発生源の識別（呼び出し元の情報を取得）
        import traceback
        import time
        import random
        
        # 呼び出し元の詳細情報を取得
        call_stack = traceback.format_stack()
        caller_info = call_stack[-2]
        
        # 発生源IDがない場合は、呼び出し元の情報から抽出を試みる
        if source_id is None:
            if "display_metrics_graph" in caller_info:
                source_id = "metrics_graph"
            elif "display_search_graph" in caller_info:
                source_id = "search_graph"
            elif "display_emotion_graph" in caller_info:
                source_id = "emotion_graph"
            elif "chapter_" in caller_info:
                source_id = "chapter_button"
            elif "comment_" in caller_info:
                source_id = "comment_button"
            elif "transcript_" in caller_info:
                source_id = "transcript_button"
            elif "emotion_seek" in caller_info:
                source_id = "emotion_slider"
            else:
                source_id = "unknown"
        
        # 現在のタイムスタンプをミリ秒単位で取得
        timestamp = int(time.time() * 1000)
        
        # ランダムなユニークIDを生成（衝突を避けるため）
        unique_id = random.randint(10000, 99999)
        
        # 完全に一意のシーク操作IDを生成
        seek_operation_id = f"{source_id}_{timestamp}_{unique_id}"
        
        # ===== ステップ2: デバッグログの出力 =====
        print(f"\n===== シーク操作開始: ID={seek_operation_id} =====")
        print(f"➤ 実行時間: {time.strftime('%H:%M:%S')}")
        print(f"➤ シーク先: {target_seconds}秒（元の値: {time_seconds}）")
        print(f"➤ 発生源: {source_id}")
        print(f"➤ 呼び出し元: {caller_info.strip()}")
        
        # セッション状態の現在値をデバッグ出力
        print("\n現在のセッション状態:")
        seek_vars = [k for k in st.session_state.keys() if any(x in k for x in ['seek', 'sec', 'reload', 'command'])]
        for k in seek_vars:
            print(f"  {k} = {st.session_state.get(k)}")
        
        # ===== ステップ3: トランザクション的アプローチ =====
        try:
            # ステップ3.1: 新しいシーク操作のための準備
            # 進行中のシーク操作をキャンセル（前回の操作が途中で中断されている可能性がある）
            for key in ['_active_seek_operation', '_seek_sec', 'sec', '_force_reload', 
                        '_direct_seek_command', '_seek_id', '_seek_command_executed']:
                if key in st.session_state:
                    print(f"  前回の値をクリア: {key}={st.session_state[key]}")
                    del st.session_state[key]
            
            # ステップ3.2: 完全に新しいシーク操作の開始
            # アクティブなシーク操作としてマーク
            st.session_state['_active_seek_operation'] = seek_operation_id
            print(f"  新しいシーク操作を設定: _active_seek_operation={seek_operation_id}")
            
            # 新しいシーク値を設定（数値として明示的に処理）
            st.session_state['_seek_sec'] = target_seconds
            st.session_state['sec'] = target_seconds  # 互換性のため
            print(f"  新しいシーク値を設定: _seek_sec={target_seconds}")
            
            # 即時プレイヤー更新を行うためのマーカーを設定
            st.session_state['_force_reload'] = True
            print(f"  _force_reload=True を設定")
            
            # 明示的なシーク命令フラグを追加
            st.session_state['_direct_seek_command'] = True
            print(f"  _direct_seek_command=True を設定")
            
            # 発生源情報を保存
            st.session_state['_seek_source'] = source_id
            print(f"  _seek_source={source_id} を設定")
            
            # スケジュールされたクリーンアップフラグを設定（シーク完了後、全変数をクリアするため）
            st.session_state['_pending_cleanup'] = True
            print(f"  _pending_cleanup=True を設定")
            
            # シーク命令IDを関連付け
            st.session_state['_seek_id'] = unique_id
            print(f"  _seek_id={unique_id} を設定")
            
            # 操作完了ステータスを記録
            print("\n⚑ シーク操作の設定が完了しました。リロード後に実行されます。")
            
        except Exception as e:
            print(f"\n❌ エラー: seek_to関数内で例外が発生しました: {e}")
            import traceback
            traceback.print_exc()


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
                            // 両方のフォーマットでメッセージを送信（一方が失敗しても他方が動作する可能性がある）
                            // type形式のメッセージ（リスナーが期待する形式）
                            var typeMsg = {{
                                'type': 'seek',
                                'sec': {sec}
                            }};
                            youtubeIframes[i].contentWindow.postMessage(JSON.stringify(typeMsg), '*');
                            
                            // command形式のメッセージ（従来の形式）
                            var commandMsg = {{
                                'command': 'seek',
                                'seconds': {sec}
                            }};
                            youtubeIframes[i].contentWindow.postMessage(JSON.stringify(commandMsg), '*');
                            
                            console.log('YouTube iframe[' + i + ']に両形式のシーク命令を送信しました');
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
