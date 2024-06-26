let socket;

   function connectWebSocket() {
       socket = new WebSocket('ws://' + window.location.host + '/ws/llm_output/');

       socket.onopen = function(e) {
           console.log("WebSocket connection established");
       };

       socket.onmessage = function(event) {
           console.log("Received message:", event.data);
           const data = JSON.parse(event.data);
           addMessage(data.message);
       };

       socket.onclose = function(event) {
           console.log("WebSocket connection closed. Attempting to reconnect...");
           setTimeout(connectWebSocket, 1000);
       };

       socket.onerror = function(error) {
           console.error(`WebSocket Error: ${error.message}`);
       };
   }

   function addMessage(message) {
       const outputElement = document.getElementById('llm-output');
       if (outputElement) {
           outputElement.innerHTML += message + '<br>';
           // Store messages in localStorage
           let messages = JSON.parse(localStorage.getItem('llmMessages') || '[]');
           messages.push(message);
           localStorage.setItem('llmMessages', JSON.stringify(messages));
       } else {
           console.error("Element with id 'llm-output' not found");
       }
   }

   function loadMessages() {
       const outputElement = document.getElementById('llm-output');
       if (outputElement) {
           let messages = JSON.parse(localStorage.getItem('llmMessages') || '[]');
           outputElement.innerHTML = messages.join('<br>');
       }
   }

   document.addEventListener('DOMContentLoaded', function() {
       loadMessages();
       connectWebSocket();
   });