// Voice Alert System using Web Speech API & ResponsiveVoice
const voiceAlerts = {
    supportsSpeechSynthesis: () => {
        return 'speechSynthesis' in window || window.responsiveVoice;
    },
    speak: (text, urgency = 'normal') => {
        if (window.responsiveVoice) {
            const rate = urgency === 'critical' ? 1.5 : 1.0;
            window.responsiveVoice.speak(text, "US English Male", { rate });
        } else if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = urgency === 'critical' ? 1.5 : 1.0;
            utterance.pitch = urgency === 'critical' ? 1.3 : 1.0;
            utterance.volume = 1.0;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
        } else {
            console.warn("Speech synthesis not supported");
        }
    },
    alerts: {
        drowsy: { text: "Alert! You are getting drowsy. Wake up immediately!", urgency: 'critical' },
        eyes_closed: { text: "Eyes closed! Please wake up and stay alert!", urgency: 'critical' },
        yawn: { text: "Yawning detected. Stay focused!", urgency: 'normal' },
        distraction: { text: "Attention! Eyes off the road. Look ahead immediately!", urgency: 'critical' },
        fatigue_warning: { text: "Warning: Fatigue detected. Please be careful.", urgency: 'normal' }
    },
    trigger: (eventType) => {
        const alert = voiceAlerts.alerts[eventType];
        if (alert) voiceAlerts.speak(alert.text, alert.urgency);
    }
};
// Load ResponsiveVoice library (optional, for better quality)
const script = document.createElement('script');
script.src = 'https://code.responsivevoice.org/responsivevoice.js';
document.head.appendChild(script);
