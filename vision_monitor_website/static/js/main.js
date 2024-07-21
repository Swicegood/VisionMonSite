import { initializeWebSocket } from './websocket.js';
import { initializePage } from './stateManagement.js';
import { refreshImages } from './utils.js';

document.addEventListener('DOMContentLoaded', function () {
    const initialDataElement = document.getElementById('initial-data');
    let initialData = {};
    
    if (initialDataElement) {
        try {
            initialData = JSON.parse(initialDataElement.textContent);
        } catch (error) {
            console.error('Error parsing initial data:', error);
        }
    }

    initializePage(initialData);
    initializeWebSocket();
    setInterval(refreshImages, 30000);
});