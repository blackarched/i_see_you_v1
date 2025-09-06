// Main application file to handle requests and calls to the attack functions

const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const attackFunctions = require('./attacks'); // Import the attack functions

const app = express();
const PORT = 3000;

// Middleware
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// Routes
app.post('/synFlood', (req, res) => {
    const { targetIP, packetRate } = req.body;
    attackFunctions.synFlood(targetIP, packetRate);
    res.send('SYN Flood attack initiated');
});

app.post('/dnsSpoofing', (req, res) => {
    const { targetDomain, fakeIP } = req.body;
    attackFunctions.dnsSpoof(targetDomain, fakeIP);
    res.send('DNS Spoofing attack initiated');
});

app.post('/mitm', (req, res) => {
    const { targetIP1, targetIP2 } = req.body;
    attackFunctions.mitm(targetIP1, targetIP2);
    res.send('MITM attack initiated');
});

app.post('/passwordCracking', (req, res) => {
    const { targetIP, wordlistPath } = req.body;
    attackFunctions.passwordCracking(targetIP, wordlistPath);
    res.send('Password Cracking attack initiated');
});

app.post('/phishing', (req, res) => {
    const { targetEmail, phishingLink } = req.body;
    attackFunctions.phishing(targetEmail, phishingLink);
    res.send('Phishing attack initiated');
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});