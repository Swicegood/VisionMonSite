import { updateFacilityState, updateCameraStates, updateSingleCamera,
    updateCameraFeeds, updateLLMOutput
 } from './uIUpdates.js';

const maxCameras = 16;
const maxLLMMessages = 50;
const cameraMap = new Map();
const llmMessages = [];

export function initializePage(initialData) {
    if (initialData && typeof initialData === 'object') {
        if (initialData.facility_state) {
            updateFacilityState(initialData.facility_state);
        }
        if (initialData.camera_states) {
            updateCameraStates(initialData.camera_states);
        }
        if (initialData.camera_feeds && Array.isArray(initialData.camera_feeds)) {
            initialData.camera_feeds.forEach(feed => {
                if (feed && feed.cameraIndex) {
                    cameraMap.set(feed.cameraIndex, feed);
                }
            });
            updateCameraFeeds(initialData.camera_states, cameraMap);
        }
        if (initialData.llm_outputs && Array.isArray(initialData.llm_outputs)) {
            initialData.llm_outputs.forEach(output => {
                if (output) {
                    llmMessages.push(output);
                }
            });
            updateLLMOutput(llmMessages);
        }
    } else {
        console.warn('Initial data is missing or invalid');
    }
}

export function addLLMMessage(message) {
    llmMessages.unshift(message);
    if (llmMessages.length > maxLLMMessages) {
        llmMessages.pop();
    }
    updateLLMOutput(llmMessages);
}

export function updateCamera(camera) {
    if (camera && camera.cameraIndex) {
        cameraMap.set(camera.cameraIndex, camera);
        updateSingleCamera(camera);
    }
}

export { cameraMap, llmMessages };