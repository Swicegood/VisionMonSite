import { cameraMap } from './stateManagement.js';
import { getLatestImageUrl, getCompositeImageUrl, colorCodeState } from './utils.js';
import logger from './logger.js';

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
        const truncatedDescription = camera.description.length > 150 
        ? camera.description.substring(0, 150) + '...' 
        : camera.description;
        
        feedDiv.id = `camera-${camera.cameraIndex}`;
        feedDiv.innerHTML = `
            <img src="${imageUrl}" alt="Camera ${camera.cameraIndex}" class="camera-image img-fluid" 
                data-bs-toggle="modal" data-bs-target="#imageModal" 
                data-camera-index="${camera.cameraIndex}">
            <div class="camera-name">${camera.cameraName} (Camera ${camera.cameraIndex})</div>
            <div class="camera-timestamp">${new Date(camera.timestamp).toLocaleString()}</div>
            <div class="camera-description" data-bs-toggle="modal" data-bs-target="#textModal" 
                data-camera-index="${camera.cameraIndex}">${truncatedDescription}</div>
        `;
        
        if (cameraStates && cameraStates[camera.cameraName]) {
            colorCodeState(feedDiv, cameraStates[camera.cameraName]);
        }
        
        cameraFeeds.appendChild(feedDiv);
    });
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
    if (!cameraElement) {
        logger.warn(`Camera element not found for index ${camera.cameraIndex}`);
        return;
    }

    try {
        const imageElement = cameraElement.querySelector('.camera-image');
        const timestampElement = cameraElement.querySelector('.camera-timestamp');
        const descriptionElement = cameraElement.querySelector('.camera-description');
        const truncatedDescription = camera.description.length > 150 
        ? camera.description.substring(0, 150) + '...' 
        : camera.description;

        if (imageElement) {
            imageElement.src = getLatestImageUrl(camera.cameraIndex);
        } else {
            logger.warn(`Image element not found for camera ${camera.cameraIndex}`);
        }

        if (timestampElement) {
            timestampElement.textContent = new Date(camera.timestamp).toLocaleString();
        } else {
            logger.warn(`Timestamp element not found for camera ${camera.cameraIndex}`);
        }

        if (descriptionElement) {
            descriptionElement.textContent = truncatedDescription;
        } else {
            logger.warn(`Description element not found for camera ${camera.cameraIndex}`);
        }

        logger.info(`Updated camera ${camera.cameraIndex} successfully`);
    } catch (error) {
        logger.error(`Error updating camera ${camera.cameraIndex}: ${error.message}`);
    }
}


export function updateFacilityState(state, timestamp) {
    if (overall) overall.innerHTML = `<div class="overall">Overall Facility State: ${timestamp || new Date().toLocaleString()}</div>`;
    if (facilityState) {
        facilityState.textContent = state.trim();
        colorCodeState(facilityState, state.trim());
    }
}

export function setupModalListeners() {
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
            const camera = cameraMap.get(cameraIndex);
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

// Call this function after updating the DOM
export function initializeModalListeners() {
    setupModalListeners();
}

export function initializeTimelinePage(initialData) {
    logger.debug("Initializing timeline page with ",initialData);
    if (initialData && initialData.cameras) {
        const thumbnailsGrid = document.getElementById('thumbnailsGrid');
        thumbnailsGrid.innerHTML = ''; // Clear current thumbnails

        initialData.cameras.forEach(camera => {
            logger.debug("Initializing page with ",camera);
            const cameraName = camera.id.split(' ')[0];
            const thumbnail = document.createElement('div');
            thumbnail.className = 'thumbnail';
            thumbnail.innerHTML = `
                <img src="${camera.image}" alt="${cameraName}">
                <div class="thumbnail-label">${cameraName}</div>
            `;
            thumbnail.onclick = () => selectCamera(cameraName);
            thumbnailsGrid.appendChild(thumbnail);
        });
    }
}


export function updateTimelinePage(data) {
    if (data.cameras) {
        const thumbnailsGrid = document.getElementById('thumbnailsGrid');
        const timelineContainer = document.getElementById('timelineContainer');

        // Update thumbnails
        if (thumbnailsGrid) {
            thumbnailsGrid.innerHTML = ''; // Clear current thumbnails
            data.cameras.forEach(camera => {
                const cameraName = camera.id.split(' ')[0];
                const thumbnail = document.createElement('div');
                thumbnail.className = 'thumbnail';
                thumbnail.innerHTML = `
                    <img src="${camera.image}" alt="${cameraName}">
                    <div class="thumbnail-label">${cameraName}</div>
                `;
                thumbnail.onclick = () => selectCamera(cameraName);
                thumbnailsGrid.appendChild(thumbnail);
            });
        }

        // Update timeline content
        if (timelineContainer) {
            timelineContainer.innerHTML = ''; // Clear current timeline
            data.events.forEach(event => {
                const timelineRow = document.createElement('div');
                timelineRow.className = 'timeline-row';
                timelineRow.innerHTML = `
                    <div class="time-marker">${event.time}</div>
                    <div class="middle-strip"></div>
                    <img
                        class="event-thumbnail"
                        src="${event.image}"
                        alt="Event"
                    >
                `;
                timelineContainer.appendChild(timelineRow);
            });
        }
    }
}