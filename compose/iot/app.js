const express = require('express');
const bodyParser = require('body-parser');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const port = 5000;
let temperature = 21;

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.use(express.static(path.join(__dirname, 'public')));

app.get('/temperature', (req, res) => {
    res.json({ temperature });
});

app.post('/set', (req, res) => {
    const value = req.body.value;

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
