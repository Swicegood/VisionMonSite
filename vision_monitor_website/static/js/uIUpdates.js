import { getLatestImageUrl, getCompositeImageUrl, colorCodeState } from './utils.js';
const cameraFeeds = document.getElementById('camera-feeds');
const llmOutput = document.getElementById('llm-output');
const facilityState = document.getElementById('facility-state');
const overall = document.getElementById('overall');

export function updateCameraStates(cameraStates) {
    const cameraStatesDiv = document.getElementById('camera-states');
    cameraStatesDiv.innerHTML = '';
    for (const [cameraId, state] of Object.entries(cameraStates)) {
        const stateDiv = document.createElement('div');
        stateDiv.className = 'camera-state';
        const cameraIndex = cameraId.split(' ').slice(-1)[0];
        const thumbnailUrl = getCompositeImageUrl(cameraId.split(' ')[0]);
        stateDiv.innerHTML = `
            <img src="${thumbnailUrl}" alt="Camera ${cameraIndex}" class="img-fluid" 
                data-bs-toggle="modal" data-bs-target="#compositeImageModal" 
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

export function updateCameraFeeds(cameraStates, cameraMap) {
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
            <img src="${imageUrl}" alt="Camera ${camera.cameraIndex}" class="img-fluid" 
                data-bs-toggle="modal" data-bs-target="#plainImageModal" 
                data-camera-index="${camera.cameraIndex}">
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


export function updateLLMOutput(llmMessages) {
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

export function updateSingleCamera(camera) {
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

export function updateFacilityState(state, timestamp) {
    overall.innerHTML = `<div class="overall">Overall Facility State: ${timestamp || new Date().toLocaleString()}</div>`;
    facilityState.textContent = state.trim();
    colorCodeState(facilityState, state.trim());
}


function setupModalListeners() {
    const compositeModal = document.getElementById('compositeImageModal');
    const compositeModalImage = document.getElementById('compositeModalImage');

    compositeModal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;
        const cameraName = button.getAttribute('data-camera-name');
        compositeModalImage.src = getCompositeImageUrl(cameraName);
    });

    const plainModal = document.getElementById('plainImageModal');
    const plainModalImage = document.getElementById('plainModalImage');

    plainModal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;
        const cameraIndex = button.getAttribute('data-camera-index');
        plainModalImage.src = getLatestImageUrl(cameraIndex);
    });
}

export function updateAlertStatus(cameraId, status) {
    const cameraElement = document.getElementById(`camera-${cameraId}`);
    if (cameraElement) {
        const alertStatusElement = cameraElement.querySelector('.alert-status');
        if (!alertStatusElement) {
            const newAlertStatusElement = document.createElement('div');
            newAlertStatusElement.className = 'alert-status';
            cameraElement.appendChild(newAlertStatusElement);
        }
        alertStatusElement.textContent = status;
        colorCodeAlertStatus(alertStatusElement, status);
    }
}

function colorCodeAlertStatus(element, status) {
    element.classList.remove('bg-success', 'bg-danger', 'bg-warning');
    switch (status) {
        case "Alert triggered":
            element.classList.add('bg-danger');
            break;
        case "Alert resolved":
            element.classList.add('bg-success');
            break;
        case "Alert flapping":
            element.classList.add('bg-warning');
            break;
        default:
            element.classList.add('bg-secondary');
    }
}