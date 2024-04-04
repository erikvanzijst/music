let CAP_HEIGHT = 2;
let BAR_WIDTH = 10, GAP = 2;
let CAP_COLOR = '#ddd';
var canvas = null;
var ctx = null;
var gradient = null;
var capYPositionArray = null;


const drawVisualizer = ({ height, width, data }) => {
    let numBars = Math.floor(width / (BAR_WIDTH + GAP));
    if (canvas.height !== height || canvas.width !== width) {
        console.log(canvas.width + " " + width + " x " + canvas.height + " " + height);
        canvas.width = width;
        canvas.height = height;
        capYPositionArray = new Array(numBars).fill(0);
        gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(1, '#0f0');
        gradient.addColorStop(0.5, '#ff0');
        gradient.addColorStop(0, '#f00');

        console.log('canvas.height: ' + canvas.height);
        console.log('canvas.width: ' + canvas.width);
    }
    cwidth = canvas.width;
    cheight = canvas.height - CAP_HEIGHT;

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


onmessage = function (e) {
    const {width, height, data, canvas: canvasMessage} = e.data;
    if (canvasMessage) {
        canvas = canvasMessage;
        ctx = canvas.getContext('2d');
        capYPositionArray = new Array(1024).fill(0);
        gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(1, '#0f0');
        gradient.addColorStop(0.5, '#ff0');
        gradient.addColorStop(0, '#f00');
        console.log("Canvas transferred to worker.");

    } else {
        drawVisualizer({width, height, data});
    }
}
