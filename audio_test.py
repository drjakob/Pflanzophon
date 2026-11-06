"""Prüft, ob Mikrofon und Lautsprecher mit 16000 Hz (wie ElevenLabs) geöffnet werden können."""
import pyaudio

ABTASTRATE = 16000
BLOCKGROESSE = 4000

audio = pyaudio.PyAudio()

print("--- Gefundene Audiogeräte ---")
for geraete_index in range(audio.get_device_count()):
    geraet = audio.get_device_info_by_index(geraete_index)
    print(f"[{geraete_index}] {geraet['name']}  "
          f"(Eingänge: {geraet['maxInputChannels']}, Ausgänge: {geraet['maxOutputChannels']}, "
          f"Standardrate: {int(geraet['defaultSampleRate'])} Hz)")

for beschreibung, ist_eingang in (("Mikrofon", True), ("Lautsprecher", False)):
    try:
        datenstrom = audio.open(format=pyaudio.paInt16, channels=1, rate=ABTASTRATE,
                                input=ist_eingang, output=not ist_eingang,
                                frames_per_buffer=BLOCKGROESSE)
        datenstrom.close()
        print(f"OK:     {beschreibung} lässt sich mit {ABTASTRATE} Hz öffnen.")
    except Exception as fehler:
        print(f"FEHLER: {beschreibung} mit {ABTASTRATE} Hz: {fehler}")

audio.terminate()
