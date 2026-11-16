/* ========================================================
   LifeAI - Study Planner & Interactive Pomodoro Timer
   ======================================================== */

document.addEventListener('DOMContentLoaded', () => {
    let timerDuration = 25 * 60; // default 25 mins
    let timeLeft = timerDuration;
    let timerInterval = null;
    let isRunning = false;
    let currentMode = 'focus'; // focus, shortBreak, longBreak

    const timerDisplay = document.getElementById('timerDisplay');
    const toggleBtn = document.getElementById('timerToggleBtn');
    const resetBtn = document.getElementById('timerResetBtn');
    const modeButtons = document.querySelectorAll('.pomodoro-mode-btn');
    const subjectSelect = document.getElementById('pomodoroSubjectSelect');

    const MODES = {
        focus: 25 * 60,
        shortBreak: 5 * 60,
        longBreak: 15 * 60
    };

    function updateDisplay() {
        if (!timerDisplay) return;
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        document.title = `${timerDisplay.textContent} - LifeAI Pomodoro`;
    }

    function playChime() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();
            
            // Pleasant two-tone chime
            const playTone = (freq, start, duration) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, ctx.currentTime + start);
                gain.gain.setValueAtTime(0.2, ctx.currentTime + start);
                gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + duration);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(ctx.currentTime + start);
                osc.stop(ctx.currentTime + start + duration);
            };

            playTone(587.33, 0, 0.5); // D5
            playTone(880.00, 0.25, 0.8); // A5
        } catch (e) {
            console.warn('Audio chime unsupported or blocked', e);
        }
    }

    function setMode(mode) {
        currentMode = mode;
        timerDuration = MODES[mode];
        timeLeft = timerDuration;
        pauseTimer();
        updateDisplay();

        modeButtons.forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
        });
    }

    function startTimer() {
        if (isRunning) return;
        isRunning = true;
        if (toggleBtn) toggleBtn.innerHTML = '⏸';

        timerInterval = setInterval(() => {
            if (timeLeft > 0) {
                timeLeft--;
                updateDisplay();
            } else {
                completeSession();
            }
        }, 1000);
    }

    function pauseTimer() {
        isRunning = false;
        clearInterval(timerInterval);
        if (toggleBtn) toggleBtn.innerHTML = '▶';
    }

    async function completeSession() {
        pauseTimer();
        playChime();

        if (currentMode === 'focus') {
            const subjectId = subjectSelect ? subjectSelect.value : null;
            const minutesLogged = Math.round(timerDuration / 60);

            // Log session automatically to backend
            try {
                await fetch('/api/study/sessions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        subject_id: subjectId ? parseInt(subjectId) : null,
                        duration_minutes: minutesLogged,
                        notes: 'Completed 25-minute Pomodoro focus block'
                    })
                });
                showToast(`🎉 Focus session completed! Logged ${minutesLogged} minutes to your study log.`, 'success');
            } catch (err) {
                console.error(err);
            }

            // Prompt for short break
            setTimeout(() => {
                if (confirm('Great job! Would you like to start a 5-minute restorative break?')) {
                    setMode('shortBreak');
                    startTimer();
                } else {
                    setMode('focus');
                }
            }, 500);
        } else {
            showToast('Break completed! Ready for your next focus session?', 'info');
            setMode('focus');
        }
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            if (isRunning) {
                pauseTimer();
            } else {
                startTimer();
            }
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            pauseTimer();
            timeLeft = timerDuration;
            updateDisplay();
        });
    }

    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.getAttribute('data-mode');
            if (mode) setMode(mode);
        });
    });

    // Initial display
    updateDisplay();
});
