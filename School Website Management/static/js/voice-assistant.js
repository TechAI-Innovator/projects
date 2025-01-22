
document.addEventListener("DOMContentLoaded", () => {
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    const synth = window.speechSynthesis;
    let sessionActive = false; // Tracks if the session is active
    let inactivityTimer; // Tracks inactivity

    recognition.lang = "en-US";
    recognition.continuous = true;

    // Start listening for voice input
    function startRecognition() {
        recognition.start();
        console.log("Voice assistant is listening...");
    }

    // Stop listening for voice input
    function stopRecognition() {
        recognition.stop();
        console.log("Voice assistant has stopped.");
    }

    // Reset inactivity timer
    function resetInactivityTimer() {
        clearTimeout(inactivityTimer);
        inactivityTimer = setTimeout(() => {
            console.log("Session timed out due to inactivity.");
            stopRecognition();
            sessionActive = false;
        }, 10 * 60 * 1000); // 5 minutes
    }

    // Handle received voice input
    recognition.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript.trim().toLowerCase();
        console.log("Received command:", transcript);

        if (transcript.includes("hello")) {
            sessionActive = true;
            resetInactivityTimer();
            console.log("Session activated.");
            speakMessage("Voice assistant is listening");
            return;
        }

        if (!sessionActive) {
            return; // Ignore input if the session is not active
        }

        resetInactivityTimer();

        if (transcript.includes("goodbye")) {
            sessionActive = false;
            stopRecognition();
            speakMessage("Voice assistant deactivated. Goodbye!");
            return;
        }

        // Send the command to the backend
        fetch("/dashboard", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ 
                command: transcript, 
                input_type: "voice"  // Specify input type
            }),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.message) {
                    speakMessage(data.message); // Respond with a message
                }

                if (data.redirect) {
                    // Navigate to the route if available
                    window.location.href = data.redirect;
                }
            })
            .catch((error) => {
                console.error("Error processing voice command:", error);
                speakMessage("An error occurred. Please try again.");
            });
    };

    // Speak a given message
    function speakMessage(message) {
        const utterance = new SpeechSynthesisUtterance(message);
        synth.speak(utterance);
    }

    // Handle errors during recognition
    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        speakMessage("An error occurred with speech recognition.");
    };

    // Start recognition initially
    startRecognition();
});