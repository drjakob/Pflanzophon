import os
import sys
import time
import threading
from gpiozero import Button
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ConversationInitiationData
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

# --- KONFIGURATION LADEN ---
load_dotenv()

AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_SCHLUESSEL = os.getenv("ELEVENLABS_API_KEY")
PIN_SCHALTER = 17

if not AGENT_ID or not API_SCHLUESSEL:
    print("FEHLER: ELEVENLABS_API_KEY oder ELEVENLABS_AGENT_ID fehlen in der .env Datei!")
    sys.exit(1)

dynamische_variablen = {
    'user_name': 'Jakob',
    'greeting': 'Hallo'
}

konfiguration = ConversationInitiationData(
    dynamic_variables=dynamische_variablen
)

eleven_client = ElevenLabs(api_key=API_SCHLUESSEL)
hoerer_schalter = Button(PIN_SCHALTER)

ki_aktiv = False
aktuelle_konversation = None
sperre = threading.Lock()


def erstelle_konversation():
    """Erstellt eine neue Instanz der KI-Konversation.

    Das DefaultAudioInterface öffnet Mikrofon und Lautsprecher mit 16000 Hz.
    Damit das mit dem USB-Hörer klappt, MUSS /etc/asound.conf ein "plug"-Gerät
    verwenden (siehe config/asound.conf und README.md).
    """
    return Conversation(
        eleven_client,
        AGENT_ID,
        config=konfiguration,
        requires_auth=bool(API_SCHLUESSEL),
        audio_interface=DefaultAudioInterface(),
        callback_agent_response=lambda antwort: print(f"KI: {antwort}"),
        callback_user_transcript=lambda transkript: print(f"Nutzer: {transkript}"),
    )


def starte_session():
    global ki_aktiv, aktuelle_konversation
    with sperre:
        if ki_aktiv:
            return
        ki_aktiv = True

    print("\n--- Session startet ---")
    try:
        aktuelle_konversation = erstelle_konversation()
        aktuelle_konversation.start_session()
        konversations_id = aktuelle_konversation.wait_for_session_end()
        print(f"Session beendet. ID: {konversations_id}")
        if konversations_id is None:
            print("HINWEIS: Keine Session-ID -> meist Audio-Fehler (siehe Meldungen oben).")
            print("Teste mit:  python audio_test.py   und prüfe /etc/asound.conf (README.md).")
    except Exception as fehler:
        print(f"Fehler während der Konversation: {fehler}")
    finally:
        aktuelle_konversation = None
        ki_aktiv = False
        print("--- Bereit für nächsten Anruf / Tastendruck ---")


def beende_session():
    """Wird aufgerufen, wenn der Hörer aufgelegt wird."""
    konversation = aktuelle_konversation
    if konversation is not None:
        print("\nHörer aufgelegt – Session wird beendet.")
        try:
            konversation.end_session()
        except Exception as fehler:
            print(f"Fehler beim Beenden: {fehler}")


def tastatur_listener():
    while True:
        try:
            eingabe = input()
        except EOFError:
            break
        if 'a' in eingabe.lower():
            print("Tastendruck 'a' erkannt!")
            threading.Thread(target=starte_session, daemon=True).start()
        elif 'q' in eingabe.lower():
            print("Tastendruck 'q' erkannt – Session wird beendet.")
            beende_session()


hoerer_schalter.when_released = beende_session

print("--- Telefon-Assistent bereit ---")
print("Konfiguration aus .env geladen.")
print(f"Aktivierung via: GPIO {PIN_SCHALTER} (Hörer) ODER Taste 'a' + Enter im Terminal")
print("Beenden einer laufenden Session: Hörer auflegen ODER Taste 'q' + Enter")

eingabe_thread = threading.Thread(target=tastatur_listener, daemon=True)
eingabe_thread.start()

try:
    while True:
        if hoerer_schalter.is_pressed and not ki_aktiv:
            print("\nHörer abgehoben!")
            starte_session()
            # Erst neu starten, wenn der Hörer zwischendurch aufgelegt wurde
            while hoerer_schalter.is_pressed:
                time.sleep(0.1)
        time.sleep(0.1)
except KeyboardInterrupt:
    beende_session()
    print("\nProgramm beendet.")
