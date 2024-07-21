import { handleStructuredMessage, handleUnstructuredMessage } from './messageHandlers.js';

let socket;

export function initializeWebSocket() {
    socket = new WebSocket('ws://' + window.location.host + '/ws/llm_output/');

    socket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.message) {
            try {
                const intermediateData = JSON.parse(data.message);
                console.log("Parsed intermediate message data:", intermediateData);

                if (intermediateData.message) {
                    const innerData = JSON.parse(intermediateData.message);
                    console.log("Parsed inner message data (facility_state and camera_states):", innerData);
                    handleStructuredMessage(innerData);
                } else {
                    handleUnstructuredMessage(intermediateData);
                }
            } catch (error) {
                console.error("Error parsing JSON:", error);
                handleUnstructuredMessage(data.message);
            }
        }
    };

    socket.onerror = function (error) {
        console.error(`WebSocket Error: ${error.message}`);
    };

    socket.onclose = function (e) {
        console.log("WebSocket connection closed:", e.code, e.reason);
    };
}

export function sendWebSocketMessage(message) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(message));
    } else {
        console.error('WebSocket is not connected.');
    }
}