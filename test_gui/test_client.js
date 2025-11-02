// ClaudeVoice Test Client - Simple GUI for testing voice agent
// Uses LiveKit Client SDK

let room = null;
let localTrack = null;
let isConnected = false;

const statusEl = document.getElementById('status');
const transcriptEl = document.getElementById('transcript');
const connectBtn = document.getElementById('connect');
const disconnectBtn = document.getElementById('disconnect');
const audioIndicator = document.getElementById('audioIndicator');
const audioStatus = document.getElementById('audioStatus');

// Update UI status
function updateStatus(status, message) {
    statusEl.textContent = message;
    statusEl.className = `status-${status}`;
    
    connectBtn.disabled = isConnected;
    disconnectBtn.disabled = !isConnected;
}

function addMessage(speaker, text, type = 'normal') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${speaker}`;
    
    const timestamp = new Date().toLocaleTimeString();
    const prefix = speaker === 'user' ? '👤 You' : speaker === 'agent' ? '🤖 Agent' : '⚙️ System';
    
    messageDiv.innerHTML = `<strong>${prefix}</strong> [${timestamp}]: ${text}`;
    transcriptEl.appendChild(messageDiv);
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function updateAudioIndicator(speaking) {
    if (speaking) {
        audioIndicator.className = 'audio-indicator speaking';
        audioStatus.textContent = 'Speaking...';
    } else {
        audioIndicator.className = 'audio-indicator silent';
        audioStatus.textContent = 'Listening...';
    }
}

// Connect to LiveKit room
connectBtn.onclick = async () => {
    const url = document.getElementById('url').value;
    const roomName = document.getElementById('room').value;
    const token = document.getElementById('token').value;

    if (!url || !roomName || !token) {
        alert('Please fill in all fields (URL, Room Name, and Token)');
        return;
    }

    try {
        updateStatus('connecting', 'Connecting...');
        addMessage('system', 'Connecting to room: ' + roomName);

        // Check if LiveKit SDK is loaded (try multiple possible names)
        if (typeof LiveKit === 'undefined') {
            if (typeof LivekitClient !== 'undefined') {
                window.LiveKit = LivekitClient;
            } else if (typeof livekit !== 'undefined') {
                window.LiveKit = livekit;
            } else {
                throw new Error('LiveKit SDK not loaded. Check browser console for script loading errors. Available globals: ' + 
                    Object.keys(window).filter(k => k.toLowerCase().includes('livekit')).join(', '));
            }
        }
        
        // Create room instance
        room = new LiveKit.Room({
            adaptiveStream: true,
            dynacast: true,
            publishDefaults: {
                videoSimulcastLayers: [],
            },
        });

        // Handle connection events
        room.on('connected', () => {
            isConnected = true;
            updateStatus('connected', 'Connected ✓');
            addMessage('system', 'Successfully connected to room');
        });

        room.on('disconnected', () => {
            isConnected = false;
            updateStatus('disconnected', 'Disconnected');
            addMessage('system', 'Disconnected from room');
            if (localTrack) {
                localTrack.stop();
                localTrack = null;
            }
        });

        room.on('trackSubscribed', (track, publication, participant) => {
            if (track.kind === 'audio') {
                addMessage('system', `Subscribed to audio from ${participant.identity}`);
                const audioElement = track.attach();
                audioElement.autoplay = true;
                audioElement.style.display = 'none';
                document.body.appendChild(audioElement);

                // Monitor audio levels for visual feedback
                track.on('audioFrame', (frame) => {
                    // Simple audio level detection
                    updateAudioIndicator(true);
                    setTimeout(() => updateAudioIndicator(false), 200);
                });
            }
        });

        room.on('trackUnsubscribed', (track, publication, participant) => {
            track.detach();
            addMessage('system', `Unsubscribed from ${participant.identity}`);
        });

        room.on('participantConnected', (participant) => {
            addMessage('system', `Participant joined: ${participant.identity}`);
        });

        room.on('participantDisconnected', (participant) => {
            addMessage('system', `Participant left: ${participant.identity}`);
        });

        // Handle data messages (transcriptions, tool calls, etc.)
        room.on('dataReceived', (payload, participant, kind, topic) => {
            if (participant !== room.localParticipant) {
                try {
                    const decoder = new TextDecoder();
                    const data = JSON.parse(decoder.decode(payload));
                    
                    if (data.type === 'transcription') {
                        addMessage('agent', data.text);
                    } else if (data.type === 'user_message') {
                        addMessage('user', data.text);
                    } else if (data.type === 'tool_call') {
                        addMessage('system', `Tool called: ${data.tool} - ${data.result}`);
                    }
                } catch (e) {
                    console.error('Error parsing data message:', e);
                }
            }
        });

        // Connect to room
        await room.connect(url, token);
        
        // Get microphone access
        try {
            localTrack = await LiveKit.createLocalAudioTrack({
                echoCancellation: true,
                noiseSuppression: true,
            });
            
            await room.localParticipant.publishTrack(localTrack);
            addMessage('system', 'Microphone enabled and published');
            
            // Monitor local audio for visual feedback
            localTrack.on('audioFrame', () => {
                updateAudioIndicator(true);
                setTimeout(() => updateAudioIndicator(false), 300);
            });
            
        } catch (error) {
            console.error('Microphone access error:', error);
            addMessage('system', '⚠️ Could not access microphone: ' + error.message);
        }

        // Send a test message to indicate user is ready
        const encoder = new TextEncoder();
        const testMessage = JSON.stringify({
            type: 'user_ready',
            timestamp: new Date().toISOString(),
        });
        
        await room.localParticipant.publishData(
            encoder.encode(testMessage),
            LiveKit.DataPacket_Kind.RELIABLE
        );

    } catch (error) {
        console.error('Connection error:', error);
        updateStatus('disconnected', 'Connection Failed');
        addMessage('system', '❌ Connection failed: ' + error.message);
        isConnected = false;
    }
};

// Disconnect from room
disconnectBtn.onclick = async () => {
    if (room) {
        try {
            await room.disconnect();
        } catch (error) {
            console.error('Disconnect error:', error);
        }
        room = null;
    }
    
    if (localTrack) {
        localTrack.stop();
        localTrack = null;
    }
    
    updateStatus('disconnected', 'Disconnected');
};

// Allow Enter key to connect
document.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !isConnected) {
        connectBtn.click();
    }
});

// Initial status
updateStatus('disconnected', 'Not Connected');
addMessage('system', 'Ready to connect. Fill in the fields above and click Connect.');

