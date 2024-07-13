const socket = new WebSocket('ws://' + window.location.host + '/ws/llm_output/');
const cameraFeeds = document.getElementById('camera-feeds');
const llmOutput = document.getElementById('llm-output');
const facilityState = document.getElementById('facility-state');
const maxCameras = 16;
const maxLLMMessages = 50;
const cameraMap = new Map();
const llmMessages = [];

function typeWriter(element, text, speed) {
    let i = 0;
    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    type();
}

function updateCameraFeeds() {
    cameraFeeds.innerHTML = '';
    [...cameraMap.values()].forEach(camera => {
        const cameraElement = document.createElement('div');
        cameraElement.className = 'camera-feed';
        cameraElement.innerHTML = `
            <h3>${camera.cameraName} (Camera ${camera.cameraIndex})</h3>
            <div class="timestamp">${new Date(camera.timestamp).toLocaleString()}</div>
            <img src="/get_latest_image/${camera.cameraIndex}/" alt="Camera ${camera.cameraIndex}" class="img-fluid">
            <div class="camera-info">Description:</div>
            <div class="description">${camera.description}</div>
        `;
        cameraFeeds.appendChild(cameraElement);
    });
    cameraFeeds.scrollTop = cameraFeeds.scrollHeight;
}

function updateLLMOutput() {
    llmOutput.innerHTML = '';
    llmMessages.forEach(message => {
        const messageElement = document.createElement('div');
        messageElement.className = 'message';
        messageElement.innerHTML = `
            <div class="timestamp">${new Date(message.timestamp).toLocaleString()}</div>
            <div class="camera-info">Camera ${message.cameraName} (Index: ${message.cameraIndex})</div>
            <div class="description">${message.description}</div>
        `;
        llmOutput.appendChild(messageElement);
    });
    llmOutput.scrollTop = llmOutput.scrollHeight;
}

function colorCodeState(state) {
    facilityState.classList.remove('bg-primary', 'bg-secondary', 'bg-success', 'bg-danger', 'bg-warning', 'bg-info', 'text-white');
    if (state.includes('busy')) {
        facilityState.classList.add('bg-danger', 'text-white');
    } else if (state.includes('off-hours') || state.includes('night-time')) {
        facilityState.classList.add('bg-secondary', 'text-white');
    } else if (state.includes('festival happening')) {
        facilityState.classList.add('bg-warning');
    } else if (state.includes('quiet')) {
        facilityState.classList.add('bg-success', 'text-white');
    } else if (state.includes('meal time')) {
        facilityState.classList.add('bg-info', 'text-white');
    } else {
        facilityState.classList.add('bg-light');
    }
}

socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    if (data.facility_state) {
        facilityState.textContent = data.facility_state;
        colorCodeState(data.facility_state);
    } else if (data.message) {
        const [cameraName, cameraIndex, timestamp, ...descriptionParts] = data.message.split(' ');
        const description = descriptionParts.join(' ');

        // Update camera feeds
        cameraMap.set(cameraIndex, { cameraName, cameraIndex, timestamp, description });
        if (cameraMap.size > maxCameras) {
            const oldestKey = cameraMap.keys().next().value;
            cameraMap.delete(oldestKey);
        }
        updateCameraFeeds();

        // Update LLM output
        llmMessages.push({ cameraName, cameraIndex, timestamp, description });
        if (llmMessages.length > maxLLMMessages) {
            llmMessages.shift();
        }
        updateLLMOutput();

        // Apply typing effect to the latest LLM message
        const latestMessage = llmOutput.lastElementChild;
        if (latestMessage) {
            const descriptionElement = latestMessage.querySelector('.description');
            descriptionElement.innerHTML = '';
            typeWriter(descriptionElement, description, 20);
        }
    }
};