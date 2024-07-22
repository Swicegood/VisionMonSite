import { getLatestImageUrl, getCompositeImageUrl, colorCodeState } from './utils.js';

const cameraFeeds = document.getElementById('camera-feeds');
const llmOutput = document.getElementById('llm-output');
const facilityState = document.getElementById('facility-state');
const overall = document.getElementById('overall');

export function updateCameraStates(cameraStates) {
    const cameraStatesDiv = document.getElementById('camera-states');
    if (!cameraStatesDiv) {
        console.error('Camera states container not found');
        return;
    }
    cameraStatesDiv.innerHTML = '';
    for (const [cameraId, state] of Object.entries(cameraStates)) {
        const stateDiv = document.createElement('div');
        stateDiv.className = 'camera-state';
        const cameraIndex = cameraId.split(' ').slice(-1)[0];
        const cameraName = cameraId.split(' ')[0];
        const thumbnailUrl = getCompositeImageUrl(cameraName);
        stateDiv.innerHTML = `
            <img src="${thumbnailUrl}" alt="Camera ${cameraIndex}" class="img-fluid"
                data-bs-toggle="modal" data-bs-target="#compositeImageModal" 
                data-camera-name="${cameraName}">
            <div>${cameraName.replace('_', ' ')}</div>
            <div>(Camera ${cameraIndex})</div>
            <div class="state-text">${state}</div>
        `;
        colorCodeState(stateDiv, state);
        cameraStatesDiv.appendChild(stateDiv);
    }
    setupModalListeners();
}

export function updateCameraFeeds(cameraStates, cameraMap) {
    if (!cameraFeeds) {
        console.error('Camera feeds container not found');
        return;
    }
    
    cameraFeeds.innerHTML = '';
    
    [...cameraMap.values()].forEach((camera) => {
        const feedDiv = document.createElement('div');
        feedDiv.className = 'camera-feed';
        const imageUrl = getLatestImageUrl(camera.cameraIndex);
        const truncatedDescription = camera.description.length > 50 
            ? camera.description.substring(0, 150) + '...' 
            : camera.description;
        
        feedDiv.innerHTML = `
            <img src="${imageUrl}" alt="Camera ${camera.cameraIndex}" class="img-fluid" 
                data-bs-toggle="modal" data-bs-target="#imageModal" 
                data-camera-index="${camera.cameraIndex}">
            <div>${camera.cameraName} (Camera ${camera.cameraIndex})</div>
            <div class="description" data-bs-toggle="modal" data-bs-target="#textModal" 
                data-camera-index="${camera.cameraIndex}">${truncatedDescription}</div>
        `;
        
        if (cameraStates && cameraStates[camera.cameraName]) {
            colorCodeState(feedDiv, cameraStates[camera.cameraName]);
        }
        
        cameraFeeds.appendChild(feedDiv);
    });
    
    setupModalListeners(cameraMap);
}

export function updateLLMOutput(llmMessages) {
    if (!llmOutput) {
        console.error('LLM output container not found');
        return;
    }
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
    llmOutput.scrollTop = 0;
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
    if (overall) overall.innerHTML = `<div class="overall">Overall Facility State: ${timestamp || new Date().toLocaleString()}</div>`;
    if (facilityState) {
        facilityState.textContent = state.trim();
        colorCodeState(facilityState, state.trim());
    }
}

function setupModalListeners(cameraMap) {
    const compositeImageModal = document.getElementById('compositeImageModal');
    const compositeModalImage = document.getElementById('compositeModalImage');
    const imageModal = document.getElementById('imageModal');
    const fullImage = document.getElementById('fullImage');
    const textModal = document.getElementById('textModal');
    const fullText = document.getElementById('fullText');

    if (compositeImageModal && compositeModalImage) {
        compositeImageModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const cameraName = button.getAttribute('data-camera-name');
            compositeModalImage.src = getCompositeImageUrl(cameraName);
        });
    }

    if (imageModal && fullImage) {
        imageModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const cameraIndex = button.getAttribute('data-camera-index');
            fullImage.src = getLatestImageUrl(cameraIndex);
        });
    }

    if (textModal && fullText) {
        textModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const cameraIndex = button.getAttribute('data-camera-index');
            const camera = [...cameraMap.values()].find(c => c.cameraIndex == cameraIndex);
            if (camera) {
                fullText.textContent = camera.description;
            }
        });
    }
}

export function updateAlertStatus(cameraId, status) {
    const cameraElement = document.querySelector(`.camera-feed[data-camera-index="${cameraId}"]`);
    if (cameraElement) {
        let alertStatusElement = cameraElement.querySelector('.alert-status');
        if (!alertStatusElement) {
            alertStatusElement = document.createElement('div');
            alertStatusElement.className = 'alert-status';
            cameraElement.appendChild(alertStatusElement);
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