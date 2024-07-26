import { initializeWebSocket } from './websocket.js';
import { initializePage } from './stateManagement.js';
import { refreshImages } from './utils.js';
import { initializeModalListeners } from './uIUpdates.js';

document.addEventListener('DOMContentLoaded', function () {
    const initialDataElement = document.getElementById('initial-data');
    let initialData = {};
    
    if (initialDataElement) {
        try {
            initialData = JSON.parse(initialDataElement.textContent);
        } catch (error) {
            console.error('Error parsing initial data:', error);
        }
    } else {
        console.warn('Initial data element not found');
    }

    initializePage(initialData);
    initializeWebSocket();
    initializeModalListeners();
    setInterval(refreshImages, 30000);
});