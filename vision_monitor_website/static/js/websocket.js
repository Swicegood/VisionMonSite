const socket = new WebSocket('ws://' + window.location.host + '/ws/llm_output/');
const cameraFeeds = document.getElementById('camera-feeds');
const llmOutput = document.getElementById('llm-output');
const facilityState = document.getElementById('facility-state');
const overall = document.getElementById('overall');
const maxCameras = 16;
const maxLLMMessages = 50;
const cameraMap = new Map();
const llmMessages = [];

function initializePage() {
    if (initialData.facility_state) {
        updateFacilityState(initialData.facility_state);
    }
    if (initialData.camera_states) {
        updateCameraStates(initialData.camera_states);
    }
    if (initialData.camera_feeds) {
        initialData.camera_feeds.forEach(feed => {
            cameraMap.set(feed.cameraIndex, feed);
        });
        updateCameraFeeds(initialData.camera_states);
    }
    if (initialData.llm_outputs) {
        initialData.llm_outputs.forEach(output => {
            llmMessages.push(output);
        });
        updateLLMOutput();
    }
}

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

function getCompositeImageUrl(cameraName) {
    return `/get_composite_image/${cameraName}/?t=${new Date().getTime()}`;
}

function updateCameraStates(cameraStates) {
    const cameraStatesDiv = document.getElementById('camera-states');
    cameraStatesDiv.innerHTML = '';
    for (const [cameraId, state] of Object.entries(cameraStates)) {
        const stateDiv = document.createElement('div');
        stateDiv.className = 'camera-state';
        const cameraIndex = cameraId.split(' ').slice(-1)[0];
        const thumbnailUrl = getCompositeImageUrl(cameraId.split(' ')[0]);
        stateDiv.innerHTML = `
            <img src="${thumbnailUrl}" alt="Camera ${cameraIndex}" class="img-fluid" 
                data-bs-toggle="modal" data-bs-target="#imageModal" 
                data-camera-name="${cameraId.split(' ')[0]}">
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
    [...cameraMap.values()].forEach(camera => {
        let cameraElement = document.getElementById(`camera-${camera.cameraIndex}`);
        if (!cameraElement) {
            cameraElement = document.createElement('div');
            cameraElement.className = 'camera-feed';
            cameraElement.id = `camera-${camera.cameraIndex}`;
            cameraFeeds.appendChild(cameraElement);
        }
        const imageUrl = getLatestImageUrl(camera.cameraIndex);
        cameraElement.innerHTML = `
            <h3>${camera.cameraIndex} (Camera ${camera.cameraIndex})</h3>
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
    });
    setupModalListeners();
}

function setupModalListeners() {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');

    modal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;
        const cameraName = button.getAttribute('data-camera-name');
        modalImage.src = getCompositeImageUrl(cameraName);
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

function updateSingleCamera(camera) {
    const cameraElement = document.getElementById(`camera-${camera.cameraIndex}`);
    if (cameraElement) {
        const imageElement = cameraElement.querySelector('img');
        const timestampElement = cameraElement.querySelector('.timestamp');
        const descriptionElement = cameraElement.querySelector('.description');

        imageElement.src = getLatestImageUrl(camera.cameraIndex);
        timestampElement.textContent = new Date(camera.timestamp).toLocaleString();
        descriptionElement.textContent = camera.description;
    }
}
function addLLMMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    messageElement.innerHTML = `
        <div class="timestamp">${new Date(message.timestamp).toLocaleString()}</div>
        <div class="camera-info">Camera ${message.cameraName} (Index: ${message.cameraIndex})</div>
        <div class="description">${message.description}</div>
    `;
    llmOutput.insertBefore(messageElement, llmOutput.firstChild);
    if (llmOutput.children.length > maxLLMMessages) {
        llmOutput.removeChild(llmOutput.lastChild);
    }
}
function colorCodeState(element, state) {
    element.classList.remove('bg-primary', 'bg-secondary', 'bg-success', 'bg-danger', 'bg-warning', 'bg-info', 'text-white');

    const lowerState = state.toLowerCase();

    if (lowerState.includes('busy')) {
        element.classList.add('bg-danger', 'text-white');
    } else if (lowerState.includes('night-time')) {
        element.classList.add('bg-secondary', 'text-white');
    } else if (lowerState.includes('festival happening') || lowerState.includes('crowd gathering') 
        || lowerState.includes('eating') ) {
        element.classList.add('bg-warning');
    } else if (lowerState.includes('quiet')) {
        element.classList.add('bg-success', 'text-white');
    } else if (lowerState.includes('person')) {
        element.classList.add('bg-info', 'text-white');
    } else {
        element.classList.add('bg-light');
    }
}

socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
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
                    updateSingleCamera(camera);
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


function handleUnstructuredMessage(message) {
    console.log("Handling unstructured message:", message);
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

        // Update camera map and single camera
        const camera = { cameraName, cameraIndex, timestamp, description };
        cameraMap.set(cameraIndex, camera);
        updateSingleCamera(camera);

        // Apply typing effect to the latest LLM message
        const latestMessage = llmOutput.firstElementChild;
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


function updateFacilityState(state) {
    const stateTimestamp = initialData.facility_state.timestamp || new Date().toLocaleString();
    overall.innerHTML = `<div class="overall">Overall Facility State: ${stateTimestamp}</div>`;
    facilityState.textContent = state.trim();
    colorCodeState(facilityState, state.trim());
}

// Refresh images every 30 seconds
setInterval(refreshImages, 30000);
document.addEventListener('DOMContentLoaded', function () {
    initializePage();
    setupModalListeners();
});