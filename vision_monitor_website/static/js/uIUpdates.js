import { cameraMap } from './stateManagement.js';
import { getLatestImageUrl, getCompositeImageUrl, colorCodeState } from './utils.js';
import logger from './logger.js';

const cameraFeeds = document.getElementById('camera-feeds');
const llmOutput = document.getElementById('llm-output');
const facilityState = document.getElementById('facility-state');
const overall = document.getElementById('overall');

// ====== GLOBAL PAGINATION STATE ======
let offset = 0;
let limit = 20;
let isLoading = false;
let currentCameraId = null;  // Track currently selected camera

// Timeline pagination and date-range tracking
let timelineOffset = 0;
const timelineLimit = 20;
let timelineIsLoading = false;
let selectedStartTime = null; // Store selected start time
let selectedEndTime = null;   // Store selected end time

// Define the CameraState module
export const CameraState = (() => {
    let cameraSelected = false;
    let cameraId = null; // Add a variable to store the cameraId

    return {
        isCameraSelected: () => cameraSelected,
        setCameraSelected: (value) => { cameraSelected = value; },
        getCameraId: () => cameraId, // Method to get the cameraId
        setCameraId: (id) => { cameraId = id; } // Method to set the cameraId
    };
})();

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

// Utility function to add new events to the existing timeline
export function appendToTimeline(events) {
    const timelineContainer = document.getElementById('timelineContainer');
    if (!timelineContainer) {
        console.warn('Timeline container not found');
        return;
    }

    events.forEach((event) => {
        const timelineRow = document.createElement('div');
        timelineRow.className = 'timeline-row';
        const time = formatTimestamp(event.timestamp);
        const imageUrl = `/get_frame_image/${event.data_id}`;
        timelineRow.innerHTML = `
            <div class="time-marker">${time}</div>
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
                style="height: 60px; width: 60px;"
                src="${imageUrl}"
                alt="Event"
            >
        `;
        // Click handler to swap main camera image
        timelineRow.onclick = () => {
            const mainCameraImage = document.getElementById('mainCameraImage');
            if (mainCameraImage) {
                mainCameraImage.src = imageUrl;
            }
        };
        timelineRow.ondblclick = () => {
            eventDescriptionModal(event);
        };
        timelineContainer.appendChild(timelineRow);
    });
    updateDateButton();
}

// Set up scroll listener to fetch more data
function setupInfiniteScroll() {
    const container = document.getElementById('timelineContainer');
    if (!container) {
        console.warn('Timeline container not found for infinite scroll');
        return;
    }
    container.addEventListener('scroll', () => {
        if (isLoading) return;
        // If scrolled close to bottom
        if (container.scrollTop + container.clientHeight >= container.scrollHeight - 5) {
            isLoading = true;
            loadMoreTimeline();
        }
    });
}

// Load more timeline events (paginates by offset/limit)
function loadMoreTimeline() {
    const params = new URLSearchParams({
        offset: offset,
        limit: limit
    });
    
    // Add camera_id to query params if we have one selected
    if (currentCameraId) {
        params.append('camera_id', currentCameraId);
    }
    
    const url = `/get_timeline_events_paginated?${params.toString()}`;
    
    fetch(url)
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }
            return response.json();
        })
        .then((data) => {
            appendToTimeline(data.events);
            offset += limit;
            isLoading = false;
        })
        .catch((err) => {
            console.error('Error fetching more timeline events:', err);
            isLoading = false;
        });
}

export function updateTimelinePage(data) {
    console.log('Updating timeline page with data:', data);

    // Reset the timeline container and offset on each update
    offset = 0;
    isLoading = false;
    const timelineContainer = document.getElementById('timelineContainer');
    if (timelineContainer) {
        timelineContainer.innerHTML = '';
    }

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

        // Append initial chunk of events
        if (data.events) {
            appendToTimeline(data.events);
            offset += data.events.length; // Keep track of how many loaded
        }

        // Re-initialize scroll listener after setting initial content
        setupInfiniteScroll();
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
    
    // Update the current camera
    currentCameraId = cameraId;

    const mainCameraImage = document.getElementById('mainCameraImage');
    const imageUrl = `/get_latest_image/${cameraIndex}`;
    logger.debug(`Setting main camera image src to: ${imageUrl}`);
    mainCameraImage.src = imageUrl;

    // Reset pagination when selecting a new camera
    offset = 0;
    isLoading = false;

    // Fetch both timeline events and latest frame analyses
    const timelineUrl = `/get_timeline_events/${cameraId}`;
    const analysesUrl = '/get_latest_frame_analyses/';
    logger.debug(`Fetching timeline events from: ${timelineUrl}`);
    logger.debug(`Fetching latest analyses from: ${analysesUrl}`);

    Promise.all([
        fetch(timelineUrl),
        fetch(analysesUrl)
    ])
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

    // Update the cameraId in the CameraState module
    CameraState.setCameraId(cameraId);
    CameraState.setCameraSelected(true);
}

export function getStateIcon(state) {
    const lowerState = state.toLowerCase();
    if (lowerState.includes('bustling')) {
        return '<i class="fas fa-users" title="Bustling"></i>';
    } else if (lowerState.includes('night-time')) {
        return '<i class="fas fa-moon" title="Night-time"></i>';
    } else if (lowerState.includes('religious') || lowerState.includes('religious')) {
        return '<i class="fas fa-star" title="Festival/Crowd"></i>';
    } else if (lowerState.includes('nothing')) {
        return '<i class="fas fa-volume-mute" title="Nothing"></i>';
    } else if (lowerState.includes('single person')) {
        return '<i class="fas fa-walking" title="single person Present"></i>';
    } else if (lowerState.includes('eating')) {
        return '<i class="fas fa-utensils" title="People Eating"></i>';
    } else if (lowerState.includes('door open')) {
        return '<i class="fas fa-door-open" title="Door Open"></i>';
    }
    return '<i class="fas fa-camera" title="Default State"></i>';
}

/**
 * Initialize infinite scroll for the timeline container.
 * @param {string} containerId - The ID of the scroll container element (e.g. 'timelineContainer')
 * @param {Function} loadMoreFn - The function to call when fetching more events
 */
export function setupTimelineInfiniteScroll(containerId, loadMoreFn) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.warn('Timeline container not found for infinite scroll');
        return;
    }
    container.addEventListener('scroll', () => {
        if (timelineIsLoading) return;
        // If scrolled to bottom/near bottom
        if (container.scrollTop + container.clientHeight >= container.scrollHeight - 5) {
            loadMoreFn();
        }
    });
}

/**
 * Load more timeline events. 
 * If cameraId is provided (and cameraSelected is true), we fetch timeline events specifically for that camera 
 * using either the date-paginated camera endpoint or the default camera endpoint. 
 * Otherwise, we use the global timeline endpoints.
 *
 * @param {Function} getAppendFn - The function used to append new events
 * @param {string|null} cameraId - The optional ID of the camera for which to fetch events
 */
export function loadMoreTimelineEvents(getAppendFn, cameraId = null) {
    if (timelineIsLoading) {
        logger.debug('Timeline is already loading, skipping request');
        return;
    }
    timelineIsLoading = true;

    let url = '';
    const params = new URLSearchParams();

    // Decide which endpoint to call based on date range and cameraId
    if (cameraId) {
        // If the user selected a camera, direct requests to the camera-specific endpoints
        if (selectedStartTime && selectedEndTime) {
            url = '/get_timeline_events_by_date';
            params.append('start_time', selectedStartTime);
            params.append('end_time', selectedEndTime);
            logger.debug(`Loading camera ${cameraId} timeline (by date) startTime=${selectedStartTime}, endTime=${selectedEndTime}`);
        } else {
            // If no date range is selected, fall back to the normal paginated endpoint
            // but with a camera_id parameter appended for filtering if your endpoint 
            // supports it (or you might have a separate endpoint).
            url = '/get_timeline_events_paginated';
            logger.debug(`Loading camera ${cameraId} timeline without date range.`);
        }
        params.append('camera_id', cameraId);

    } else {
        // If no camera is selected
        if (selectedStartTime && selectedEndTime) {
            url = '/get_timeline_events_by_date_paginated';
            params.append('start_time', selectedStartTime);
            params.append('end_time', selectedEndTime);
            logger.debug(`Loading timeline by date (no camera). Range: startTime=${selectedStartTime}, endTime=${selectedEndTime}`);
        } else {
            // No date range, no camera => default timeline
            url = '/get_timeline_events_paginated';
            logger.debug(`Loading timeline without camera or date range.`);
        }
    }

    params.append('offset', timelineOffset);
    params.append('limit', timelineLimit);

    const fullUrl = `${url}?${params.toString()}`;
    logger.debug(`Request URL: ${fullUrl} with params: ${params.toString()}`);

    fetch(fullUrl)
        .then(response => {
            logger.debug('Timeline API response status:', response.status);
            return response.json();
        })
        .then(data => {
            logger.debug('Received timeline data:', {
                eventsCount: data.events?.length || 0
            });

            if (data.events && data.events.length > 0) {
                const appendFn = getAppendFn();
                logger.debug('Appending events to timeline, appendFn exists:', !!appendFn);
                appendFn(data.events);
                timelineOffset += data.events.length;
                logger.debug('Updated timeline offset to:', timelineOffset);
            } else {
                logger.debug('No events received from API');
            }
            timelineIsLoading = false;
        })
        .catch(err => {
            logger.error('Error fetching timeline events:', {
                error: err.message,
                url: fullUrl,
                params: Object.fromEntries(params.entries())
            });
            timelineIsLoading = false;
        });
}

/**
 * Let external code set the date range (start/end) and reset pagination.
 */
export function setTimelineDateRangeAndReset(startTimeISO, endTimeISO) {
    selectedStartTime = startTimeISO;
    selectedEndTime = endTimeISO;
    timelineOffset = 0;
    timelineIsLoading = false;
}
 // Function to update the date button based on the first event in the timeline
export function updateDateButton() {
    const timelineGrid = document.getElementById('timelineContainer');
    const dateButton = document.querySelector('.date-button');

    if (!timelineGrid || !dateButton) return;

    const observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
            if (entry.isIntersecting) {
                const hiddenDate = entry.target.querySelector('.hidden-date');
                if (hiddenDate) {
                    const eventDate = new Date(hiddenDate.textContent);
                    dateButton.innerHTML = `<i class="fas fa-calendar"></i> ${formatDate(eventDate)} <i class="fas fa-chevron-down"></i>`;
                    break; // Stop observing once we find the first visible event
                }
            }
        }
    }, {
        root: timelineGrid,
        threshold: 0.1 // Adjust this threshold as needed
    });

    // Observe each timeline row
    const timelineRows = timelineGrid.querySelectorAll('.timeline-row');
    timelineRows.forEach(row => observer.observe(row));
}

export function eventDescriptionModal(event) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Event Description</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>${event.description}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Use Bootstrap's modal API to show the modal with default "backdrop" and "keyboard" behaviors
    const bootstrapModal = new bootstrap.Modal(modal, {
        backdrop: true,  // Clicking outside the modal closes it
        keyboard: true   // Pressing Escape closes the modal
    });
    bootstrapModal.show();

    // Remove the modal from the DOM after it is hidden
    modal.addEventListener('hidden.bs.modal', () => {
        modal.remove();
    });
}