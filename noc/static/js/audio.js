(() => {
  let context = null;
  let timer = null;
  let enabled = localStorage.getItem("noc-audio-enabled") === "1";
  let active = [];

  function stop() {
    if (timer) clearTimeout(timer);
    timer = null;
  }

  function tone() {
    if (!enabled || !context || !active.length || timer) return;
    const severity = active.some(item => item.severity === "critical") ? "critical" : "warning";
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sawtooth";
    oscillator.frequency.value = severity === "critical" ? 880 : 620;
    gain.gain.setValueAtTime(0.0001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.13, context.currentTime + 0.025);
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.28);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + 0.3);
    timer = setTimeout(() => { timer = null; tone(); }, severity === "critical" ? 1200 : 2400);
  }

  async function enable() {
    context ||= new (window.AudioContext || window.webkitAudioContext)();
    await context.resume();
    enabled = true;
    localStorage.setItem("noc-audio-enabled", "1");
    tone();
  }

  function disable() {
    enabled = false;
    localStorage.setItem("noc-audio-enabled", "0");
    stop();
  }

  window.NocAudio = {
    get enabled() { return enabled; },
    toggle: async () => enabled && context?.state === "running" ? disable() : enable(),
    update: incidents => {
      active = (incidents || []).filter(item => item.state === "OPEN");
      if (!active.length) stop();
      else tone();
    },
    test: async () => {
      if (!enabled || !context || context.state !== "running") throw new Error("Enable dashboard audio first");
      active = [{severity: "warning", state: "OPEN"}];
      tone();
      setTimeout(() => { active = []; stop(); }, 3000);
    }
  };
})();
