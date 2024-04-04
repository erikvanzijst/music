window.AudioContext = window.AudioContext || window.webkitAudioContext || window.mozAudioContext;
let CONTROLS_HEIGHT = 60;

let start = function() {
    let audio = document.getElementById('player');
    let audioContext = new AudioContext();
    let analyser = audioContext.createAnalyser();
    analyser.fftSize = 1024;
    let audioSrc = audioContext.createMediaElementSource(audio);

    audioSrc.connect(analyser);
    analyser.connect(audioContext.destination);
    const data = new Uint8Array(analyser.frequencyBinCount);

    let canvas = document.getElementById('canvas').transferControlToOffscreen();
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight - CONTROLS_HEIGHT;

    const worker = new Worker(new URL("./worker.js", import.meta.url));
    worker.postMessage({ canvas }, [canvas]);

    function renderFrame() {
        analyser.getByteFrequencyData(data);
        let width = window.innerWidth,
            height = window.innerHeight - CONTROLS_HEIGHT;
        worker.postMessage({width, height, data }, {});

        requestAnimationFrame(renderFrame);
    }
    renderFrame();
};

start();
console.log('Visualization loaded');
