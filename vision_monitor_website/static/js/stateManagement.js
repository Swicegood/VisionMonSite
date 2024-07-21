import { updateFacilityState, updateCameraStates, updateSingleCamera,
    updateCameraFeeds, updateLLMOutput
 } from './uIUpdates.js';

const maxCameras = 16;
const maxLLMMessages = 50;
const cameraMap = new Map();
const llmMessages = [];

export function initializePage(initialData) {
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
        updateCameraFeeds(initialData.camera_states, cameraMap);
    }
    if (initialData.llm_outputs) {
        initialData.llm_outputs.forEach(output => {
            llmMessages.push(output);
        });
        updateLLMOutput(llmMessages);
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
    cameraMap.set(camera.cameraIndex, camera);
    updateSingleCamera(camera);
}

export { cameraMap, llmMessages };