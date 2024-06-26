// visionmon_app/static/js/websocket.js
const socket = new WebSocket('ws://' + window.location.host + '/ws/llm_output/');

socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    document.getElementById('llm-output').innerHTML += data.message;
};