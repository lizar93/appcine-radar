#!/usr/bin/env python3
"""Grava el podcast de l'edició (en anglès, dues veus) amb Gemini TTS.

    python3 eines/podcast.py --mostra            # una mostra curta de cada parella (per triar veus)
    python3 eines/podcast.py --veus              # llista les veus britàniques i americanes de la Voice Library
    python3 eines/podcast.py                     # grava podcast/en.json amb cada parella (ho crida eines/audio.py)

La clau de Gemini (Google AI Studio) es llegeix de la variable d'entorn GEMINI_API_KEY, o d'un fitxer indicat amb
--clau <fitxer>. Mai s'escriu enlloc ni es mostra.

El guió (podcast/en.json) l'escriu la tasca diària (INSTRUCCIONS.md, apartat 10): segments en l'ordre de l'edició,
cada un amb torns de dos presentadors, «A» (dona) i «B» (home). Els noms de cada parella substitueixen {A} i {B}.
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-3.8-flash-tts"
RATE = 24000
# Pla gratuït: unes 3 peticions per minut. Es fan poques peticions (trossos de ~700 paraules, ~5 minuts d'àudio)
# i separades.
PAUSA = 22
MAX_PARAULES = 700
_darrera = [0.0]

# Parelles de presentadors. Les veus són de la Voice Library de Google (accent britànic i americà).
# «voice» buit: es tria sola la primera veu de conversa amb aquest accent i gènere (es pot fixar després de triar).
PARELLES = {
    "uk": {"label": "British", "A": {"name": "Emma", "voice": None}, "B": {"name": "Oliver", "voice": None}},
    "us": {"label": "American", "A": {"name": "Jess", "voice": None}, "B": {"name": "Mike", "voice": None}},
}
ACCENT = {"uk": "British", "us": "American"}


class ErrorGemini(Exception):
    def __init__(self, codi, text):
        super().__init__(f"Gemini ha respost {codi}: {text}")
        self.codi = codi


def clau():
    if "--clau" in sys.argv:
        cami = os.path.expanduser(sys.argv[sys.argv.index("--clau") + 1])
        return open(cami, encoding="utf-8").read().strip()
    valor = os.environ.get("GEMINI_API_KEY", "").strip()
    if not valor:
        raise SystemExit("Falta GEMINI_API_KEY: sense clau no hi ha podcast (l'edició i l'àudio llegit no es toquen).")
    return valor


def peticio(metode, cami, cos=None, consulta=None):
    espera_minima = _darrera[0] + PAUSA - time.time()
    if metode == "POST" and espera_minima > 0:
        time.sleep(espera_minima)
    if metode == "POST":
        _darrera[0] = time.time()
    url = f"{API}/{cami}" + (("?" + urllib.parse.urlencode(consulta, doseq=True)) if consulta else "")
    dades = json.dumps(cos).encode() if cos is not None else None
    req = urllib.request.Request(url, data=dades, method=metode,
                                 headers={"x-goog-api-key": clau(), "Content-Type": "application/json"})
    espera = 30
    for intent in range(5):
        try:
            with urllib.request.urlopen(req, timeout=600) as resposta:
                return json.loads(resposta.read())
        except urllib.error.HTTPError as error:
            text = error.read().decode("utf-8", "replace")[:300]
            if error.code in (429, 500, 502, 503, 504) and intent < 4:
                print(f"  Gemini {error.code}, reintento en {espera} s", flush=True)
                time.sleep(espera)
                espera *= 2
                continue
            raise ErrorGemini(error.code, text)
        except urllib.error.URLError as error:
            if intent < 4:
                time.sleep(espera)
                espera *= 2
                continue
            raise SystemExit(f"No s'ha pogut connectar amb Gemini: {error.reason}")


def veus(accent, genere):
    """Veus de la Voice Library amb aquest accent i gènere, les de conversa primer."""
    consulta = {"accent": accent, "gender": genere, "page_size": 200}
    dades = peticio("GET", "voices", consulta=consulta)
    llista = dades.get("voices", [])
    conversa = [v for v in llista if "conversational" in json.dumps(v).lower()]
    return conversa + [v for v in llista if v not in conversa]


def tria_veus():
    """Fixa la veu de cada presentador (si no està fixada a PARELLES) amb la primera de conversa de la Library."""
    for clau_parella, parella in PARELLES.items():
        for rol, genere in (("A", "female"), ("B", "male")):
            if parella[rol]["voice"]:
                continue
            candidates = veus(ACCENT[clau_parella], genere)
            if not candidates:
                raise SystemExit(f"No hi ha veus {ACCENT[clau_parella]} {genere} a la Voice Library.")
            triada = candidates[0]
            parella[rol]["voice"] = triada.get("id") or triada.get("name")
            parella[rol]["alt"] = triada.get("display_name")


def sintetitza(torns, parella, camp="voice"):
    """Un tros de diàleg (llista de torns) → àudio PCM 24 kHz 16 bits mono."""
    noms = {"A": parella["A"]["name"], "B": parella["B"]["name"]}
    contingut = []
    for torn in torns:
        text = torn["text"].replace("{A}", noms["A"]).replace("{B}", noms["B"])
        meta = {"type": "speech_metadata", "speaker": noms[torn["speaker"]]}
        if torn.get("style"):
            meta["style"] = torn["style"]
        contingut.append({"type": "text", "text": text, "annotations": [meta]})
    cos = {
        "model": MODEL,
        "input": [{"type": "user_input", "content": contingut}],
        "response_format": {"type": "audio", "mime_type": "audio/l16"},
        "generation_config": {"speech_config": {"mode": "conversational", "speakers": [
            {"speaker": noms["A"], "voice": parella["A"].get(camp) or parella["A"]["voice"]},
            {"speaker": noms["B"], "voice": parella["B"].get(camp) or parella["B"]["voice"]},
        ]}},
    }
    try:
        resposta = peticio("POST", "interactions", cos)
    except ErrorGemini as error:
        # Les veus de la Voice Library potser s'han de donar pel nom en lloc de l'identificador.
        if error.codi == 400 and camp == "voice" and (parella["A"].get("alt") or parella["B"].get("alt")):
            return sintetitza(torns, parella, camp="alt")
        raise
    trossos = [c.get("data") for pas in resposta.get("steps", []) if pas.get("type") == "model_output"
               for c in pas.get("content", []) if c.get("type") == "audio" and c.get("data")]
    if not trossos:
        raise SystemExit("Gemini no ha tornat àudio: " + json.dumps(resposta)[:300])
    return base64.b64decode(trossos[-1])


def a_m4a(pcm, desti):
    with tempfile.NamedTemporaryFile(suffix=".pcm") as cru:
        cru.write(pcm)
        cru.flush()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", cru.name,
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(RATE), "-ac", "1", "-c:a", "aac",
                        "-b:a", "64k", "-movflags", "+faststart", desti], check=True)


def paraules(segment):
    return sum(len(re.sub(r"<[^<>]+>|\|[^|]*\|", " ", torn["text"]).split()) for torn in segment["turns"])


def trossos(segments):
    """Agrupa segments seguits fins a ~MAX_PARAULES per fer poques peticions (i que la conversa flueixi)."""
    grups, actual, total = [], [], 0
    for segment in segments:
        n = paraules(segment)
        if actual and total + n > MAX_PARAULES:
            grups.append(actual)
            actual, total = [], 0
        actual.append(segment)
        total += n
    if actual:
        grups.append(actual)
    return grups


def grava(guio, clau_parella, desti):
    parella = PARELLES[clau_parella]
    silenci = b"\x00\x00" * int(RATE * 0.6)
    pcm, capitols, posicio = b"", [], 0.0
    for grup in trossos(guio["segments"]):
        so = sintetitza([torn for segment in grup for torn in segment["turns"]], parella)
        durada = len(so) / 2 / RATE
        # Dins d'un tros, cada segment comença on li toca per les paraules que hi ha abans (aproximat).
        total = sum(paraules(segment) for segment in grup) or 1
        abans = 0
        for segment in grup:
            capitols.append({"id": segment["id"], "title": segment["title"],
                             "start": round(posicio + durada * abans / total, 2)})
            abans += paraules(segment)
        pcm += so + silenci
        posicio += durada + len(silenci) / 2 / RATE
        print(f"  {clau_parella} · {', '.join(s['id'][-24:] for s in grup)}: {durada:.0f} s", flush=True)
    a_m4a(pcm, desti)
    return round(len(pcm) / 2 / RATE, 1), capitols


def grava_tots(sortida, data):
    """Per a eines/audio.py: grava podcast/en.json amb cada parella. Torna les pistes per a latest.json."""
    cami = os.path.join(ARREL, "podcast", "en.json")
    if not os.path.exists(cami):
        print("Sense podcast/en.json: avui no hi ha podcast.")
        return []
    guio = json.load(open(cami, encoding="utf-8"))
    if guio.get("date") != data:
        print(f"El guió del podcast és del {guio.get('date')}, no del {data}: avui no hi ha podcast.")
        return []
    tria_veus()
    pistes = []
    os.makedirs(os.path.join(sortida, "en"), exist_ok=True)
    for clau_parella, parella in PARELLES.items():
        fitxer = f"en/{data}-podcast-{clau_parella}.m4a"
        inici = time.time()
        durada, capitols = grava(guio, clau_parella, os.path.join(sortida, fitxer))
        print(f"{fitxer}: {durada / 60:.1f} min en {(time.time() - inici) / 60:.1f} min", flush=True)
        pistes.append({"language": "en", "kind": "podcast", "voice": clau_parella,
                       "name": f"{parella['A']['name']} & {parella['B']['name']} · {parella['label']}",
                       "gender": None, "file": fitxer, "durationSeconds": durada, "chapters": capitols})
    return pistes


MOSTRA = [
    {"speaker": "A", "text": "Hello and welcome to World Cinema Radar, the podcast. I'm {A}."},
    {"speaker": "B", "text": "And I'm {B}. And {A}, I have to start with the box office, because <laugh> oh dear."},
    {"speaker": "A", "text": "Oh, Klara and the Sun? |oh no| Taika Waititi's Ishiguro adaptation?"},
    {"speaker": "B", "text": "The very same. Around seven hundred and twenty-five thousand dollars, across eight hundred and eighty screens in the US and Canada."},
    {"speaker": "A", "text": "That's... <short pause> that's not a lot of dollars per screen, is it? <chuckle>"},
    {"speaker": "B", "text": "It is not. But here's the thing: it opens in Spanish cinemas this Friday, the thirtieth, so you can judge it for yourself."},
    {"speaker": "A", "text": "And honestly? Jenna Ortega and Amy Adams in an Ishiguro story. I'm still curious. <sigh> I'm always curious."},
    {"speaker": "B", "text": "That's why we love you. <laugh> Right, and then there's the big one for horror fans: Na Hong-jin is back."},
    {"speaker": "A", "text": "Finally! The Wailing is one of my favourite horror films ever. So, what do we actually know?"},
]


def main():
    try:
        principal()
    except ErrorGemini as error:
        raise SystemExit(str(error))


def principal():
    if "--veus" in sys.argv:
        for accent in ("British", "American"):
            for genere in ("female", "male"):
                print(f"== {accent} {genere}")
                for v in veus(accent, genere)[:12]:
                    print(" ", v.get("id") or v.get("name"), "|", v.get("display_name"), "|", v.get("language_code"),
                          "|", (v.get("description") or "")[:80])
        return
    if "--mostra" in sys.argv:
        tria_veus()
        carpeta = sys.argv[sys.argv.index("--sortida") + 1] if "--sortida" in sys.argv else os.path.join(ARREL, "mostres")
        os.makedirs(carpeta, exist_ok=True)
        for clau_parella, parella in PARELLES.items():
            desti = os.path.join(carpeta, f"podcast-mostra-{clau_parella}.m4a")
            a_m4a(sintetitza(MOSTRA, parella), desti)
            print(desti, parella["A"]["voice"], parella["B"]["voice"])
        return
    data = json.load(open(os.path.join(ARREL, "en", "latest.json"), encoding="utf-8"))["date"]
    carpeta = os.path.join(ARREL, "audio-sortida")
    print(json.dumps(grava_tots(carpeta, data), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
