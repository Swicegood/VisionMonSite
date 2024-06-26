const socket = new WebSocket('ws://' + window.location.host + '/ws/llm_output/');

   socket.onopen = function(e) {
       console.log("WebSocket connection established");
   };

   socket.onmessage = function(event) {
       console.log("Received message:", event.data);
       const data = JSON.parse(event.data);
       const outputElement = document.getElementById('llm-output');
       if (outputElement) {
           outputElement.innerHTML += data.message;
       } else {
           console.error("Element with id 'llm-output' not found");
       }
   };

   socket.onclose = function(event) {
       if (event.wasClean) {
           console.log(`Connection closed cleanly, code=${event.code}, reason=${event.reason}`);
       } else {
           console.error('Connection died');
       }
   };

   socket.onerror = function(error) {
       console.error(`WebSocket Error: ${error.message}`);
   };