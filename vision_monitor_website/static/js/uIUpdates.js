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
    logger.debug("Initializing timeline page with ", initialData);
    if (initialData && initialData.cameras) {
        const thumbnailsGrid = document.getElementById('thumbnailsGrid');
        thumbnailsGrid.innerHTML = ''; // Clear current thumbnails

        initialData.cameras.forEach(camera => {
            logger.debug("Initializing page with ", camera);
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
    console.log('Updating timeline page with data:', data);

    if (data.cameras) {
        const thumbnailsGrid = document.getElementById('thumbnailsGrid');
        const timelineContainer = document.getElementById('timelineContainer');

        logger.debug('Found DOM elements:', {
            thumbnailsGrid: !!thumbnailsGrid,
            timelineContainer: !!timelineContainer
        });

        // Update thumbnails
        if (thumbnailsGrid) {
            thumbnailsGrid.innerHTML = ''; // Clear current thumbnails
            logger.debug('Updating thumbnails for cameras:', data.cameras);

            data.cameras.forEach(camera => {
                const cameraName = camera.name
                logger.debug('Creating thumbnail for camera:', cameraName);

                const thumbnail = document.createElement('div');
                thumbnail.className = 'thumbnail';
                thumbnail.innerHTML = `
                    <img src="${camera.image}" alt="${cameraName}">
                    <div class="thumbnail-label">${cameraName}</div>
                `;
                thumbnail.onclick = () => selectCamera(camera.index, camera.id);
                thumbnailsGrid.appendChild(thumbnail);
            });
        }

        // Update timeline content
        if (timelineContainer) {
            timelineContainer.innerHTML = ''; // Clear current timeline
            logger.debug('Updating timeline events:', data.events?.length || 0);

            data.events.forEach((event, index) => {
                logger.debug(`Processing timeline event ${index}:`, event);

                const timelineRow = document.createElement('div');
                timelineRow.className = 'timeline-row';
                const imageUrl = `/get_frame_image/${event.data_id}`;
                timelineRow.innerHTML = `
                    <div class="time-marker">${formatTimestamp(event.timestamp)}</div>
                    <div class="middle-strip">
                        <div class="event-bubble"></div>
                    </div>
                    <div class="event-motion-symbol" style="display: flex; align-items: center; gap: 5px; padding-left: 10px;">
                    <div style="width: 20px; height: 1px; background-color: #d3d3d3;"></div>
                    <i class="fas fa-wind" style="font-size: 16px;" title="Person Detection"></i>
                    <div style="width: 20px; height: 1px; background-color: #d3d3d3;"></div>
                    </div>
                    <div class="event-type-symbol" style="display: flex; align-items: center; gap: 5px; padding-left: 5px;">
                        ${getStateIcon(event.state)}
                        <div style="width: 20px; height: 1px; background-color: #d3d3d3;"></div>
                    </div>
                    <img
                        class="event-thumbnail"
                        src="${imageUrl}"
                        alt="Event"
                    >
                `;
                // Add click handler to both row and image
                timelineRow.onclick = () => {
                    const mainCameraImage = document.getElementById('mainCameraImage');
                    mainCameraImage.src = imageUrl;
                };
                timelineContainer.appendChild(timelineRow);
            });
        }
    } else {
        logger.warn('No camera data provided for timeline update');
    }
}

// ... existing code ...

function formatTimestamp(timestamp) {
    try {
        // Parse the ISO string directly
        const date = new Date(timestamp);

        if (isNaN(date.getTime())) {
            console.error('Invalid timestamp:', timestamp);
            return 'Invalid Date';
        }

        return date.toLocaleString('en-US', {
            timeZone: 'America/New_York',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch (error) {
        console.error('Error formatting timestamp:', error);
        return 'Invalid Date';
    }
}

// Main camera selection
export function selectCamera(cameraIndex, cameraId) {
    logger.debug(`Selecting camera with index ${cameraIndex} and ID ${cameraId}`);

    const mainCameraImage = document.getElementById('mainCameraImage');
    const imageUrl = `/get_latest_image/${cameraIndex}`;
    logger.debug(`Setting main camera image src to: ${imageUrl}`);
    mainCameraImage.src = imageUrl;

    // Fetch both timeline events and latest frame analyses
    const timelineUrl = `/get_timeline_events/${cameraId}`;
    const analysesUrl = '/get_latest_frame_analyses/';
    logger.debug(`Fetching timeline events from: ${timelineUrl}`);
    logger.debug(`Fetching latest analyses from: ${analysesUrl}`);

    // Use Promise.all to fetch both in parallel
    const [timelinePromise, analysesPromise] = [
        fetch(timelineUrl),
        fetch(analysesUrl)
    ];

    Promise.all([timelinePromise, analysesPromise])
        .then(responses => {
            logger.debug(`Timeline API response status: ${responses[0].status}`);
            logger.debug(`Analyses API response status: ${responses[1].status}`);
            return Promise.all(responses.map(r => r.json()));
        })
        .then(([timelineData, analysesData]) => {
            logger.debug('Received timeline and analyses data');
            const combinedData = {
                cameras: analysesData.latest_analyses.map(analysis => ({
                    id: analysis[0],
                    name: analysis[4],
                    image: `/get_latest_image/${analysis[1]}`,
                    index: analysis[1]
                })),
                events: timelineData.events
            };
            updateTimelinePage(combinedData);
        })
        .catch(error => {
            logger.error('Error fetching data:', error);
            logger.error('Error details:', {
                cameraIndex,
                cameraId,
                errorMessage: error.message,
                errorStack: error.stack
            });
        });
}

export function getStateIcon(state) {
    const lowerState = state.toLowerCase();
    if (lowerState.includes('bustling')) {
        return '<i class="fas fa-users" title="Bustling"></i>';
    } else if (lowerState.includes('night-time')) {
        return '<i class="fas fa-moon" title="Night-time"></i>';
    } else if (lowerState.includes('festival happening') || lowerState.includes('crowd gathering')) {
        return '<i class="fas fa-star" title="Festival/Crowd"></i>';
    } else if (lowerState.includes('quiet')) {
        return '<i class="fas fa-volume-mute" title="Quiet"></i>';
    } else if (lowerState.includes('person')) {
        return '<i class="fas fa-walking" title="Person Present"></i>';
    } else if (lowerState.includes('eating')) {
        return '<i class="fas fa-utensils" title="People Eating"></i>';
    } else if (lowerState.includes('door open')) {
        return '<i class="fas fa-door-open" title="Door Open"></i>';
    }
    return '<i class="fas fa-camera" title="Default State"></i>';
}