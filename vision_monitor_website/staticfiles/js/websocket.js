const socket = new WebSocket('ws://' + window.location.host + '/ws/llm_output/');
const cameraFeeds = document.getElementById('camera-feeds');
const llmOutput = document.getElementById('llm-output');
const facilityState = document.getElementById('facility-state');
const overall = document.getElementById('overall');
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


function getLatestImageUrl(cameraIndex) {
    return `/get_latest_image/${cameraIndex}/?t=${new Date().getTime()}`;
}

function updateCameraStates(cameraStates) {
    const cameraStatesDiv = document.getElementById('camera-states');
    cameraStatesDiv.innerHTML = '';
    for (const [cameraId, state] of Object.entries(cameraStates)) {
        const stateDiv = document.createElement('div');
        stateDiv.className = 'camera-state';
        const cameraIndex = cameraId.split(' ').slice(-1)[0];
        const thumbnailUrl = getLatestImageUrl(cameraIndex);
        stateDiv.innerHTML = `
            <img src="${thumbnailUrl}" alt="Camera ${cameraIndex}" class="img-fluid" data-bs-toggle="modal" data-bs-target="#imageModal" data-camera-index="${cameraIndex}">
            <div>${cameraId.split(' ')[0].replace('_', ' ')}</div>
            <div>(Camera ${cameraIndex})</div>
            <div>${state}</div>
        `;
        colorCodeState(stateDiv, state);
        cameraStatesDiv.appendChild(stateDiv);
    }
    setupModalListeners();
}

function updateCameraFeeds(cameraStates) {
    cameraFeeds.innerHTML = '';
    [...cameraMap.values()].forEach(camera => {
        const cameraElement = document.createElement('div');
        cameraElement.className = 'camera-feed';
        const imageUrl = getLatestImageUrl(camera.cameraIndex);
        cameraElement.innerHTML = `
            <h3>${camera.cameraName} (Camera ${camera.cameraIndex})</h3>
            <div class="timestamp">${new Date(camera.timestamp).toLocaleString()}</div>
            <img src="${imageUrl}" alt="Camera ${camera.cameraIndex}" class="img-fluid" data-bs-toggle="modal" data-bs-target="#imageModal" data-camera-index="${camera.cameraIndex}">
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

    // Always scroll to the bottom
    cameraFeeds.scrollTop = cameraFeeds.scrollHeight;

    setupModalListeners();
}

function setupModalListeners() {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');

    modal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;
        const cameraIndex = button.getAttribute('data-camera-index');
        modalImage.src = getLatestImageUrl(cameraIndex);
    });
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
    
    socket.onmessage = function (e) {
        const data = JSON.parse(e.data);  // First level of parsing to get the outer structure
    
        if (data.message) {
            try {
                // The first parse of the message attribute which should reveal another JSON string
                const intermediateData = JSON.parse(data.message);
                console.log("Parsed intermediate message data:", intermediateData);
    
                // Now parse the inner JSON from the intermediateData's message attribute
                if (intermediateData.message) {
                    const innerData = JSON.parse(intermediateData.message);
                    console.log("Parsed inner message data (facility_state and camera_states):", innerData);
    
                    // Handling structured message content
                    if (innerData.facility_state) {
                        overall.innerHTML = `
                        <div class="overall">Overall Facility State: ${new Date().toLocaleString()}</div>`;
                        console.log("Facility state:", innerData.facility_state);
                        facilityState.textContent = innerData.facility_state.trim();  // Use trim() to remove any extra spaces
                        colorCodeState(facilityState, innerData.facility_state.trim());
                    }
                    if (innerData.camera_states) {
                        console.log("Camera states:", innerData.camera_states);
                        updateCameraStates(innerData.camera_states);
                        updateCameraFeeds(innerData.camera_states);
                    }
                } else {
                    // Handle unstructured messages (e.g., direct camera updates)
                    handleUnstructuredMessage(intermediateData);
                }
            } catch (error) {
                console.error("Error parsing JSON:", error);
                // Handle the message as unstructured data
                handleUnstructuredMessage(data.message);
            }
        }
    };
    
    function updateCameraFeeds(cameraStates) {
        cameraFeeds.innerHTML = '';
        [...cameraMap.values()].forEach(camera => {
            const cameraElement = document.createElement('div');
            cameraElement.className = 'camera-feed';
            const imageUrl = getLatestImageUrl(camera.cameraIndex);
            cameraElement.innerHTML = `
                <h3>${camera.cameraName} (Camera ${camera.cameraIndex})</h3>
                <div class="timestamp">${new Date(camera.timestamp).toLocaleString()}</div>
                <img src="${imageUrl}" alt="Camera ${camera.cameraIndex}" class="img-fluid" data-bs-toggle="modal" data-bs-target="#imageModal" data-camera-index="${camera.cameraIndex}">
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
        
        // Ensure scrolling happens after the DOM has been updated
        setTimeout(() => {
            cameraFeeds.scrollTop = cameraFeeds.scrollHeight;
        }, 0);
    
        setupModalListeners();
    }
    
    function handleUnstructuredMessage(message) {
        console.log("Handling unstructured message:", message);
        // Assuming the message format is "cameraName cameraIndex timestamp description"
        const parts = message.split(' ');
        if (parts.length >= 4) {
            const cameraName = parts[0];
            const cameraIndex = parts[1];
            const timestamp = parts.slice(2, 4).join(' ');
            const description = parts.slice(4).join(' ');
    
            // Update LLM output
            llmMessages.push({ cameraName, cameraIndex, timestamp, description });
            if (llmMessages.length > maxLLMMessages) {
                llmMessages.shift();
            }
            updateLLMOutput();
    
            // Update camera map
            cameraMap.set(cameraIndex, { cameraName, cameraIndex, timestamp, description });
            if (cameraMap.size > maxCameras) {
                const oldestKey = cameraMap.keys().next().value;
                cameraMap.delete(oldestKey);
            }
            updateCameraFeeds();
    
            // Apply typing effect to the latest LLM message
            const latestMessage = llmOutput.lastElementChild;
            if (latestMessage) {
                const descriptionElement = latestMessage.querySelector('.description');
                descriptionElement.innerHTML = '';
                typeWriter(descriptionElement, description, 20);
            }
        } else {
            console.error("Received message in unexpected format:", message);
        }
    }

socket.onerror = function (error) {
    console.error(`WebSocket Error: ${error.message}`);
};

socket.onclose = function (e) {
    console.log("WebSocket connection closed:", e.code, e.reason);
};

// Function to periodically refresh images
function refreshImages() {
    const allImages = document.querySelectorAll('#camera-feeds img, #camera-states img');
    allImages.forEach(img => {
        const currentSrc = new URL(img.src);
        currentSrc.searchParams.set('t', new Date().getTime());
        img.src = currentSrc.toString();
    });
}

// Refresh images every 30 seconds
setInterval(refreshImages, 30000);

// Initial setup of modal listeners
document.addEventListener('DOMContentLoaded', setupModalListeners);