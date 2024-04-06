window.AudioContext = window.AudioContext || window.webkitAudioContext || window.mozAudioContext;
let CONTROLS_HEIGHT = 60;
let CAP_HEIGHT = 2;
let BAR_WIDTH = 10, GAP = 2;
let CAP_COLOR = '#ddd';
let FPS = 35;
var enabled = false;

let audio = document.getElementById('player');
let audioContext = new AudioContext();
let analyser = audioContext.createAnalyser();
analyser.fftSize = 1024;
let audioSrc = audioContext.createMediaElementSource(audio);
audioSrc.connect(audioContext.destination);


const canvas = document.getElementById('canvas');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight - CONTROLS_HEIGHT;
let ctx = canvas.getContext('2d');
var cwidth = canvas.width,
    cheight = canvas.height - 2,
    numBars = Math.floor(canvas.width / (BAR_WIDTH + GAP)),
    capYPositionArray = new Array(numBars).fill(0),
    gradient = ctx.createLinearGradient(0, 0, 0, canvas.height - CONTROLS_HEIGHT);
gradient.addColorStop(1, '#0f0');
gradient.addColorStop(0.5, '#ff0');
gradient.addColorStop(0, '#f00');

const data = new Uint8Array(analyser.frequencyBinCount);
var prevTs = Date.now();

function renderFrame() {
    let now = Date.now();
    if ((now - prevTs) > (1000 / FPS)) {
        prevTs = now;

        // Resize canvas:
        if (canvas.height !== (window.innerHeight - CONTROLS_HEIGHT) || canvas.width !== window.innerWidth) {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight - CONTROLS_HEIGHT;
            cwidth = canvas.width;
            cheight = canvas.height - CAP_HEIGHT;
            numBars = Math.floor(canvas.width / (BAR_WIDTH + GAP));
            capYPositionArray = new Array(numBars).fill(0);
            console.log('canvas.height: ' + canvas.height);
            console.log('canvas.width: ' + canvas.width);
        }

        analyser.getByteFrequencyData(data);

        const step = Math.round(data.length / numBars);
        ctx.clearRect(0, 0, cwidth, cheight);
        for (let i = 0; i < numBars; i++) {
            let value = Math.floor(data[i * step] * (cheight / 256));

            ctx.fillStyle = CAP_COLOR;
            //draw the cap, with transition effect
            if (value < capYPositionArray[i]) {
                ctx.fillRect(i * (BAR_WIDTH + CAP_HEIGHT), cheight - (--capYPositionArray[i]), BAR_WIDTH, CAP_HEIGHT);
            } else {
                ctx.fillRect(i * (BAR_WIDTH + CAP_HEIGHT), cheight - value, BAR_WIDTH, CAP_HEIGHT);
                capYPositionArray[i] = value;
            }
            ctx.fillStyle = gradient;
            ctx.fillRect(i * (BAR_WIDTH + CAP_HEIGHT), cheight - value + CAP_HEIGHT, BAR_WIDTH, cheight);
        }
    }
    if (enabled || capYPositionArray.some(value => value !== 0)) {    // Wait for all the caps to hit the floor
        requestAnimationFrame(renderFrame);
    }
}

let toggle = function () {
    if (enabled) {
        enabled = false;
        audioSrc.disconnect(analyser);
    } else {
        enabled = true;
        audioSrc.connect(analyser);
        renderFrame();
    }
    localStorage.setItem('visualization', JSON.stringify(enabled));
}

if (JSON.parse(localStorage.getItem('visualization')) === true) {
    toggle();
}
console.log('Visualization loaded');
