const express = require('express');
const bodyParser = require('body-parser');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const port = 5000;
let temperature = 21;

const ACCESS_LOG = '/var/log/iot/access.log';

function logAccess(entry) {
    fs.appendFile(ACCESS_LOG, JSON.stringify(entry) + '\n', () => {});
}

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.use(express.static(path.join(__dirname, 'public')));

app.get('/temperature', (req, res) => {
    res.json({ temperature });
});

app.post('/set', (req, res) => {
    const value = req.body.value;

    logAccess({
        ts: new Date().toISOString(),
        ip: req.ip,
        endpoint: '/set',
        value: value,
    });

    exec(value, (err, stdout, stderr) => {
        if (!isNaN(value)) {
            temperature = parseInt(value);
        }

        res.send(`Temperatura cambiada a ${value}°C`);
    });
});

app.listen(port, () => {
    console.log(`IoT device escuchando en el puerto ${port}`);
});
