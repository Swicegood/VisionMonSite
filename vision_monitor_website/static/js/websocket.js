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

function updateCameraFeeds(cameraStates) {
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
            <div class="camera-state"></div>
        `;
        const cameraStateElement = cameraElement.querySelector('.camera-state');
        if (cameraStates && cameraStates[camera.cameraName]) {
            cameraStateElement.textContent = cameraStates[camera.cameraName];
            colorCodeState(cameraStateElement, cameraStates[camera.cameraName]);
        }
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

function updateCameraStates(cameraStates) {
    const cameraStatesDiv = document.getElementById('camera-states');
    cameraStatesDiv.innerHTML = '';
    for (const [cameraId, state] of Object.entries(cameraStates)) {
        const stateDiv = document.createElement('div');
        stateDiv.className = 'camera-state';
        stateDiv.textContent = `${cameraId}: ${state}`;
        cameraStatesDiv.appendChild(stateDiv);
    }
}

function colorCodeState(element, state) {
    element.classList.remove('bg-primary', 'bg-secondary', 'bg-success', 'bg-danger', 'bg-warning', 'bg-info', 'text-white');
    if (state.includes('busy')) {
        element.classList.add('bg-danger', 'text-white');
    } else if (state.includes('off-hours') || state.includes('night-time')) {
        element.classList.add('bg-secondary', 'text-white');
    } else if (state.includes('festival happening')) {
        element.classList.add('bg-warning');
    } else if (state.includes('quiet')) {
        element.classList.add('bg-success', 'text-white');
    } else if (state.includes('meal time')) {
        element.classList.add('bg-info', 'text-white');
    } else {
        element.classList.add('bg-light');
    }
}

socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    if (data.facility_state) {
        console.log("Data Facility state", data.facility_state);
        facilityState.textContent = data.facility_state;
        colorCodeState(facilityState, data.facility_state);
        updateCameraFeeds(data.camera_states);
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
    if (data.camera_states) {
        console.log("Data Camrea states", data.camera_states);
        updateCameraStates(data.camera_states);
    }
    socket.onerror = function(error) {
        console.error(`WebSocket Error: ${error.message}`);
    };
    
    socket.onclose = function(e) {
        console.log("WebSocket connection closed:", e.code, e.reason);
    };

};