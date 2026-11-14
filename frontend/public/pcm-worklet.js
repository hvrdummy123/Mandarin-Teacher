/* AudioWorklet: downsample to 16 kHz mono PCM Int16 frames (20 ms). */
class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._ratio = sampleRate / 16000;
    this._buf = [];
    this._acc = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const channel = input[0];
    for (let i = 0; i < channel.length; i++) {
      this._acc += 1;
      if (this._acc >= this._ratio) {
        this._acc -= this._ratio;
        const s = Math.max(-1, Math.min(1, channel[i]));
        this._buf.push(s < 0 ? s * 0x8000 : s * 0x7fff);
        // 20 ms at 16 kHz = 320 samples
        if (this._buf.length >= 320) {
          const frame = new Int16Array(this._buf.splice(0, 320));
          this.port.postMessage(frame.buffer, [frame.buffer]);
        }
      }
    }
    return true;
  }
}

registerProcessor("pcm-capture", PcmCaptureProcessor);
