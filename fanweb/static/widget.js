(function () {
    // Configuración
    const API_URL = "http://localhost:5000/api/voice-chat";
    let isRecording = false;
    let recognition = null;

    // Crear estilos
    const style = document.createElement('style');
    style.innerHTML = `
        .aurora-widget-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            font-family: 'Segoe UI', sans-serif;
        }
        .aurora-btn {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(45deg, #ff4757, #ff6b81);
            box-shadow: 0 4px 15px rgba(255, 71, 87, 0.4);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s;
            animation: pulse-widget 2s infinite;
        }
        .aurora-btn:hover { transform: scale(1.1); }
        .aurora-btn img { width: 40px; height: 40px; border-radius: 50%; }
        
        .aurora-chat-window {
            position: absolute;
            bottom: 80px;
            right: 0;
            width: 320px;
            height: 450px;
            background: #1e1e1e;
            border-radius: 12px;
            box-shadow: 0 5px 25px rgba(0,0,0,0.5);
            display: none;
            flex-direction: column;
            overflow: hidden;
            border: 1px solid #333;
        }
        .aurora-header {
            background: #ff4757;
            padding: 15px;
            color: white;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .aurora-messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .msg {
            padding: 8px 12px;
            border-radius: 10px;
            max-width: 80%;
            font-size: 0.9em;
            line-height: 1.4;
        }
        .msg-user { align-self: flex-end; background: #333; color: white; }
        .msg-bot { align-self: flex-start; background: #ff4757; color: white; }
        
        .aurora-input-area {
            padding: 10px;
            background: #252525;
            display: flex;
            gap: 5px;
        }
        .aurora-input {
            flex: 1;
            padding: 8px;
            border-radius: 20px;
            border: none;
            background: #333;
            color: white;
        }
        .aurora-send-btn, .aurora-mic-btn {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1.2em;
            color: #ccc;
        }
        .aurora-mic-btn.recording { color: #ff4757; animation: pulse-mic 1s infinite; }
        
        @keyframes pulse-widget {
            0% { box-shadow: 0 0 0 0 rgba(255, 71, 87, 0.4); }
            70% { box-shadow: 0 0 0 15px rgba(255, 71, 87, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 71, 87, 0); }
        }
        @keyframes pulse-mic { 50% { opacity: 0.5; } }
    `;
    document.head.appendChild(style);

    // Crear HTML
    const container = document.createElement('div');
    container.className = 'aurora-widget-container';
    container.innerHTML = `
        <div class="aurora-chat-window" id="auroraChat">
            <div class="aurora-header">
                <span>Luz de Aurora (IA) 🎙️</span>
                <span style="cursor:pointer" onclick="toggleAurora()">✖</span>
            </div>
            <div class="aurora-messages" id="auroraMessages">
                <div class="msg msg-bot">Hola amor, soy Aurora. ¿Tienes dudas sobre el manual? Pregúntame lo que quieras... 💕</div>
            </div>
            <div class="aurora-input-area">
                <button class="aurora-mic-btn" id="micBtn">🎤</button>
                <input type="text" class="aurora-input" id="auroraInput" placeholder="Escribe aquí..." />
                <button class="aurora-send-btn" id="sendBtn">➤</button>
            </div>
        </div>
        <div class="aurora-btn" onclick="toggleAurora()">
            <div style="font-size: 30px;">💬</div>
        </div>
        <audio id="auroraAudio" style="display:none"></audio>
    `;
    document.body.appendChild(container);

    // Lógica
    const chatWindow = document.getElementById('auroraChat');
    const messages = document.getElementById('auroraMessages');
    const input = document.getElementById('auroraInput');
    const sendBtn = document.getElementById('sendBtn');
    const micBtn = document.getElementById('micBtn');
    const audioPlayer = document.getElementById('auroraAudio');

    window.toggleAurora = function () {
        if (chatWindow.style.display === 'none' || !chatWindow.style.display) {
            chatWindow.style.display = 'flex';
            // Play welcome sound if needed? Maybe later.
        } else {
            chatWindow.style.display = 'none';
        }
    };

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `msg msg-${sender}`;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    async function sendMessage(text) {
        if (!text.trim()) return;
        addMessage(text, 'user');
        input.value = '';

        // Add loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'msg msg-bot';
        loadingDiv.textContent = '...';
        loadingDiv.id = 'loadingMsg';
        messages.appendChild(loadingDiv);

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, user_id: 'web_visitor' })
            });
            const data = await response.json();

            // Remove loading
            document.getElementById('loadingMsg').remove();

            if (data.status === 'success') {
                addMessage(data.text, 'bot');
                if (data.audio) {
                    audioPlayer.src = 'data:audio/mp3;base64,' + data.audio;
                    audioPlayer.play().catch(e => console.log("Audio play error:", e));
                }
            } else {
                addMessage("Ups, tuve un error amor. Intenta de nuevo.", 'bot');
            }
        } catch (e) {
            if (document.getElementById('loadingMsg')) document.getElementById('loadingMsg').remove();
            addMessage("Error de conexión. ¿Está prendido mi servidor?", 'bot');
            console.error(e);
        }
    }

    sendBtn.onclick = () => sendMessage(input.value);
    input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(input.value); };

    // Speech Recognition
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.lang = 'es-ES';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add('recording');
        };
        recognition.onend = () => {
            isRecording = false;
            micBtn.classList.remove('recording');
        };
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            input.value = transcript;
            sendMessage(transcript);
        };

        micBtn.onclick = () => {
            if (isRecording) recognition.stop();
            else recognition.start();
        };
    } else {
        micBtn.style.display = 'none'; // No soportado
    }

})();
