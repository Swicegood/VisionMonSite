import { updateFacilityState, updateCameraStates, updateSingleCamera } from './uIUpdates.js';
import { addLLMMessage, updateCamera } from './stateManagement.js';
import { typeWriter } from './utils.js';

export function handleStructuredMessage(innerData) {
    if (innerData.facility_state) {
        console.log("Facility state:", innerData.facility_state);
        updateFacilityState(innerData.facility_state.trim());
    }
    if (innerData.camera_states) {
        console.log("Camera states:", innerData.camera_states);
        updateCameraStates(innerData.camera_states);
    }
}

export function handleUnstructuredMessage(message) {
    console.log("Handling unstructured message:", message);
    const parts = message.split(' ');
    if (parts.length >= 4) {
        const cameraName = parts[0];
        const cameraIndex = parts[1];
        const timestamp = parts.slice(2, 4).join(' ');
        const description = parts.slice(4).join(' ');

        const newMessage = { cameraName, cameraIndex, timestamp, description };
        addLLMMessage(newMessage);

        const camera = { cameraName, cameraIndex, timestamp, description };
        updateCamera(camera);

        const latestMessage = document.querySelector('#llm-output .message:first-child');
        if (latestMessage) {
            const descriptionElement = latestMessage.querySelector('.description');
            descriptionElement.innerHTML = '';
            typeWriter(descriptionElement, description, 20);
        }
    } else {
        console.error("Received message in unexpected format:", message);
    }
}