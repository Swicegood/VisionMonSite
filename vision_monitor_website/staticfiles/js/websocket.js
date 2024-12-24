import { handleStructuredMessage, handleUnstructuredMessage, handleAlertMessage } from './messageHandlers.js';
import { updateTimelinePage } from './uIUpdates.js'; // A new function to update the timeline


let socket;

export function initializeWebSocket() {
    socket = new WebSocket('ws://' + window.location.host + '/ws/llm_output/');

    socket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.message) {
            try {
                const parsedData = JSON.parse(data.message);
                if (parsedData.type === "alert") {
                    handleAlertMessage(parsedData);
                } else if (parsedData.type === "timeline") {
                    updateTimelinePage(parsedData);
                } else if (parsedData.message) {
                    const innerData = JSON.parse(parsedData.message);
                    handleStructuredMessage(innerData);
                } else {
                    handleUnstructuredMessage(parsedData);
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