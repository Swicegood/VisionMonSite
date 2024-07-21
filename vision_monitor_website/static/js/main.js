import { initializeWebSocket } from './websocket.js';
import { initializePage } from './stateManagement.js';
import { refreshImages } from './utils.js';

document.addEventListener('DOMContentLoaded', function () {
    initializePage(window.initialData);
    initializeWebSocket();
    setInterval(refreshImages, 30000);
});