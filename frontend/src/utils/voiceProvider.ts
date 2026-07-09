/**
 * voiceProvider.ts
 *
 * Thin adapter that abstracts STT and TTS behind a unified interface,
 * switching implementations based on the VITE_VOICE_PROVIDER env variable.
 *
 * VITE_VOICE_PROVIDER=webapi  (default)
 *   - STT: browser's SpeechRecognition API (continuous + interim results)
 *   - TTS: browser's SpeechSynthesis API
 *
 * VITE_VOICE_PROVIDER=deepgram
 *   - STT: MediaRecorder → POST blob to /stt → transcript text
 *   - TTS: POST text to /tts → MP3 ArrayBuffer → AudioContext playback
 *
 * VoiceAgent.tsx calls ONLY this adapter — never vendor APIs directly.
 */

import { voiceApi } from './api';

// ─── Shared types ──────────────────────────────────────────────────────────────

export type TranscriptCallback = (text: string, isFinal: boolean) => void;
export type StatusCallback = (status: 'listening' | 'idle' | 'error') => void;
export type TtsDoneCallback = () => void;

export interface VoiceProviderAdapter {
  /** Start listening for speech. Calls onTranscript as text comes in. */
  startListening(onTranscript: TranscriptCallback, onStatus: StatusCallback): void;
  /** Stop the active STT session. */
  stopListening(): void;
  /** Speak the given text. Calls onDone when finished. */
  speak(text: string, onDone?: TtsDoneCallback): void;
  /** Cancel any ongoing TTS playback. */
  cancelSpeech(): void;
  /** Whether this provider supports voice input at all in the current browser. */
  isSupported(): boolean;
}

// ─── Read env ──────────────────────────────────────────────────────────────────

const VOICE_PROVIDER = import.meta.env.VITE_VOICE_PROVIDER ?? 'webapi';

// ─── WebAPI provider (browser-native) ─────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

class WebApiVoiceProvider implements VoiceProviderAdapter {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private recognition: any = null;

  isSupported() {
    return !!SpeechRecognitionAPI;
  }

  startListening(onTranscript: TranscriptCallback, onStatus: StatusCallback) {
    if (!SpeechRecognitionAPI) {
      onStatus('error');
      return;
    }

    this.recognition = new SpeechRecognitionAPI();
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';

    this.recognition.onstart = () => onStatus('listening');

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    this.recognition.onresult = (event: any) => {
      let interim = '';
      let final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t;
        else interim += t;
      }
      if (interim) onTranscript(interim, false);
      if (final) onTranscript(final, true);
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    this.recognition.onerror = (event: any) => {
      if (event.error === 'not-allowed') {
        onStatus('error');
      } else {
        onStatus('idle');
      }
    };

    this.recognition.onend = () => onStatus('idle');

    this.recognition.start();
  }

  stopListening() {
    this.recognition?.stop();
    this.recognition = null;
  }

  speak(text: string, onDone?: TtsDoneCallback) {
    if (!window.speechSynthesis) {
      onDone?.();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(
      v => v.name.includes('Google') || v.name.includes('Natural') || v.lang.startsWith('en'),
    );
    if (preferred) utterance.voice = preferred;
    utterance.onend = () => onDone?.();
    utterance.onerror = () => onDone?.();
    window.speechSynthesis.speak(utterance);
  }

  cancelSpeech() {
    window.speechSynthesis?.cancel();
  }
}

// ─── Deepgram provider (server-side REST) ─────────────────────────────────────

class DeepgramVoiceProvider implements VoiceProviderAdapter {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;
  private onDoneCallback: TtsDoneCallback | null = null;

  isSupported() {
    return !!(navigator.mediaDevices && window.MediaRecorder);
  }

  async startListening(onTranscript: TranscriptCallback, onStatus: StatusCallback) {
    if (!this.isSupported()) {
      onStatus('error');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioChunks = [];

      // Prefer webm/opus, fall back to whatever the browser supports
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      this.mediaRecorder = new MediaRecorder(stream, { mimeType });

      this.mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };

      this.mediaRecorder.onstop = async () => {
        // Stop all tracks so the mic indicator goes away
        stream.getTracks().forEach(t => t.stop());

        const blob = new Blob(this.audioChunks, { type: mimeType });
        this.audioChunks = [];

        try {
          const { text } = await voiceApi.stt(blob);
          if (text.trim()) {
            onTranscript(text.trim(), true);
          }
        } catch (err) {
          console.error('[DeepgramVoiceProvider] STT error:', err);
        }
        onStatus('idle');
      };

      this.mediaRecorder.start();
      onStatus('listening');
    } catch (err) {
      console.error('[DeepgramVoiceProvider] Mic access error:', err);
      onStatus('error');
    }
  }

  stopListening() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    this.mediaRecorder = null;
  }

  async speak(text: string, onDone?: TtsDoneCallback) {
    this.onDoneCallback = onDone ?? null;
    try {
      const arrayBuffer = await voiceApi.tts(text);

      if (!this.audioContext || this.audioContext.state === 'closed') {
        this.audioContext = new AudioContext();
      }

      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      this.currentSource = this.audioContext.createBufferSource();
      this.currentSource.buffer = audioBuffer;
      this.currentSource.connect(this.audioContext.destination);
      this.currentSource.onended = () => {
        this.currentSource = null;
        this.onDoneCallback?.();
        this.onDoneCallback = null;
      };
      this.currentSource.start();
    } catch (err) {
      console.error('[DeepgramVoiceProvider] TTS error:', err);
      onDone?.();
    }
  }

  cancelSpeech() {
    this.currentSource?.stop();
    this.currentSource = null;
    this.onDoneCallback = null;
  }
}

// ─── Factory + singleton export ───────────────────────────────────────────────

function createVoiceProvider(): VoiceProviderAdapter {
  if (VOICE_PROVIDER === 'deepgram') {
    console.info('[voiceProvider] Using DeepgramVoiceProvider');
    return new DeepgramVoiceProvider();
  }
  console.info('[voiceProvider] Using WebApiVoiceProvider');
  return new WebApiVoiceProvider();
}

/** Singleton voice provider — share across the app. */
export const voiceProvider = createVoiceProvider();
