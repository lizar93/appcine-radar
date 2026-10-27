#!/usr/bin/env python3
"""Grava l'edició del dia en àudio i la publica a la branca «audio» del repositori.

    python3 eines/audio.py              # grava i publica (força la branca «audio», que només guarda l'últim dia)
    python3 eines/audio.py --sense-pujar  # només grava a ./audio-sortida (per provar)

Veus (gratuïtes, s'executen aquí mateix, sense claus):
- Català: Matxa-TTS v2 del Projecte AINA / BSC (ús no comercial), veu «Elia» (catalana central, dona).
- Anglès: Piper, «Cori» (britànica) i «Alan» (britànic).

Deixa a la branca «audio»:
- latest.json — data de l'edició, i per a cada pista: idioma, veu, fitxer, durada i capítols (un per reportatge).
- ca/AAAA-MM-DD-elia.m4a, en/AAAA-MM-DD-cori.m4a, en/AAAA-MM-DD-alan.m4a

A més, si hi ha podcast/en.json i la clau GEMINI_API_KEY, hi afegeix el podcast (eines/podcast.py):
- en/AAAA-MM-DD-podcast-uk.m4a i en/AAAA-MM-DD-podcast-us.m4a (pistes amb "kind": "podcast").

Si falla, l'edició escrita no es toca: l'app llegeix amb la veu de l'iPhone.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import wave
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.expanduser("~/.cache/appcine-radar-veus")
MADRID = ZoneInfo("Europe/Madrid")
REPO = "https://github.com/lizar93/appcine-radar"
HF = "https://huggingface.co"
MATXA = HF + "/BSC-LT/matxa-tts-v2-ca-multiaccent-graphemes/resolve/main/matxa_v2_multiaccent_graphemes_20_steps_wavenext.onnx"
PIPER = HF + "/rhasspy/piper-voices/resolve/main/"
RATE = 22050

VEUS = {
    "ca": [{"id": "elia", "name": "Elia", "gender": "female", "engine": "matxa", "speaker": 3}],
    "en": [
        {"id": "cori", "name": "Cori", "gender": "female", "engine": "piper", "model": "en/en_GB/cori/high/en_GB-cori-high"},
        {"id": "alan", "name": "Alan", "gender": "male", "engine": "piper", "model": "en/en_GB/alan/medium/en_GB-alan-medium"},
    ],
}


def instala():
    """Instal·la el que falti, sense aturar-se per la xarxa de cada entorn.

    - Primer amb la configuració de xarxa de l'entorn tal qual; si falla, sense no_proxy (en alguns entorns PyPI només
      surt pel servidor intermediari).
    - num2words va sense dependències: només necessita docopt per a la seva línia d'ordres, i docopt no té paquet binari
      i a vegades no s'instal·la (26/10/2026, entorn «Default»).
    """
    import importlib.util

    def pip(*args):
        for env in (dict(os.environ), {**os.environ, "no_proxy": "", "NO_PROXY": ""}):
            fet = subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages", "-q", *args],
                                 env=env)
            if fet.returncode == 0:
                return
        raise SystemExit("No s'han pogut instal·lar: " + " ".join(args))

    falten = [paquet for modul, paquet in (("numpy", "numpy"), ("onnxruntime", "onnxruntime"), ("piper", "piper-tts"))
              if importlib.util.find_spec(modul) is None]
    if falten:
        pip(*falten)
    if importlib.util.find_spec("num2words") is None:
        pip("--no-deps", "num2words")


def baixa(url, desti):
    if os.path.exists(desti) and os.path.getsize(desti) > 0:
        return desti
    os.makedirs(os.path.dirname(desti), exist_ok=True)
    temporal = desti + ".part"
    with urllib.request.urlopen(url, timeout=600) as resposta, open(temporal, "wb") as sortida:
        shutil.copyfileobj(resposta, sortida)
    os.replace(temporal, desti)
    return desti


# --- Text per llegir -------------------------------------------------------------------------------------------------

def data_llarga(dia, catala):
    d = datetime.strptime(dia, "%Y-%m-%d")
    if catala:
        dies = ["dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"]
        mesos = ["de gener", "de febrer", "de març", "d'abril", "de maig", "de juny", "de juliol", "d'agost",
                 "de setembre", "d'octubre", "de novembre", "de desembre"]
        return f"{dies[d.weekday()]}, {d.day} {mesos[d.month - 1]}"
    return d.strftime("%A, %-d %B")


def normalitza(text, catala):
    from num2words import num2words
    text = re.sub(r"https?://\S+", "", text)
    text = text.replace("4K", "4 K").replace("&", " i " if catala else " and ")
    if catala:
        text = re.sub(r"(\d+)\s*/\s*(\d+)", lambda m: f"{m.group(1)} sobre {m.group(2)}", text)
        text = re.sub(r"(\d+)\s*%", lambda m: f"{m.group(1)} per cent", text)
        # Primer els milers amb punt (725.000), després els decimals amb coma (7,8).
        text = re.sub(r"\b\d{1,3}(?:\.\d{3})+\b", lambda m: m.group(0).replace(".", ""), text)
        text = re.sub(r"(\d+),(\d+)", lambda m: f"{num2words(int(m.group(1)), lang='ca')} coma {num2words(int(m.group(2)), lang='ca')}", text)
        text = re.sub(r"\d+", lambda m: num2words(int(m.group(0)), lang="ca"), text)
    else:
        text = re.sub(r"(\d+)\s*/\s*(\d+)", lambda m: f"{m.group(1)} out of {m.group(2)}", text)
    return re.sub(r"\s+", " ", text).strip()


def guio(edicio, catala):
    """Capítols: (id, títol, text)."""
    capitols = [("intro", "Radar", (
        f"Radar cinematogràfic mundial. Edició de {data_llarga(edicio['date'], True)}."
        if catala else f"World Cinema Radar. The edition for {data_llarga(edicio['date'], False)}."))]
    for r in edicio["reports"]:
        cos = " ".join([r["headline"].rstrip(".") + ".", r["deck"]] + r["paragraphs"])
        capitols.append((r["id"], r["headline"], cos))
    capitols.append(("fi", "Fi" if catala else "End", "Fins demà." if catala else "That's all for today."))
    return [(i, t, normalitza(c, catala)) for i, t, c in capitols]


def frases(text, maxim=280):
    trossos = []
    for frase in re.split(r"(?<=[.!?])\s+", text):
        while len(frase) > maxim:
            tall = frase.rfind(",", 0, maxim)
            tall = tall if tall > 60 else frase.rfind(" ", 0, maxim)
            trossos.append(frase[:tall + 1].strip())
            frase = frase[tall + 1:].strip()
        if frase:
            trossos.append(frase)
    return trossos


# --- Veus --------------------------------------------------------------------------------------------------------------

class Matxa:
    _pad = "_"
    _punt = ';:,.!?¡¿—…"«»“”()- '
    _lletres = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    _ipa = "ɑɐɒæɓʙβɔɕçɗɖðʤəɘɚɛɜɝɞɟʄɡɠɢʛɦɧħɥʜɨɪʝɭɬɫɮʟɱɯɰŋɳɲɴøɵɸθœɶʘɹɺɾɻʀʁɽʂʃʈʧʉʊʋⱱʌɣɤʍχʎʏʑʐʒʔʡʕʢǀǁǂǃˈˌːˑʼʴʰʱʲʷˠˤ˞↓↑→↗↘'̩'ᵻ"
    _accents = "àáèéìíòóùú·üïöñ’#´"

    def __init__(self, speaker):
        import numpy as np
        import onnxruntime as ort
        self.np = np
        simbols = [self._pad] + list(self._punt) + list(self._lletres) + list(self._ipa) + list(self._accents)
        self.ids = {s: i for i, s in enumerate(simbols)}
        self.speaker = speaker
        self.sessio = ort.InferenceSession(baixa(MATXA, os.path.join(CACHE, "matxa_v2.onnx")),
                                           providers=["CPUExecutionProvider"])

    def llegeix(self, text):
        np = self.np
        sortida = []
        for frase in frases(text):
            s = [self.ids[c] for c in re.sub(r"\s+", " ", frase.lower()) if c in self.ids]
            if not s:
                continue
            x = [0] * (len(s) * 2 + 1)
            x[1::2] = s
            x = np.array(x, dtype=np.int64)[None]
            _, ona = self.sessio.run(None, {"x": x, "x_lengths": np.array([x.shape[1]], dtype=np.int64),
                                            "scales": np.array([0.5, 0.95], dtype=np.float32),
                                            "spks": np.array([self.speaker], dtype=np.int64)})
            sortida += [ona.squeeze(0).astype(np.float32), np.zeros(int(RATE * 0.28), dtype=np.float32)]
        return np.concatenate(sortida) if sortida else np.zeros(1, dtype=np.float32)


class Piper:
    def __init__(self, model):
        base = os.path.join(CACHE, os.path.basename(model))
        baixa(PIPER + model + ".onnx", base + ".onnx")
        baixa(PIPER + model + ".onnx.json", base + ".onnx.json")
        self.model = base + ".onnx"

    def llegeix(self, text):
        import numpy as np
        with tempfile.TemporaryDirectory() as tmp:
            sortida = os.path.join(tmp, "t.wav")
            subprocess.run([sys.executable, "-m", "piper", "-m", self.model, "-f", sortida],
                           input=text.encode("utf-8"), check=True, capture_output=True)
            with wave.open(sortida) as w:
                assert w.getframerate() == RATE, w.getframerate()
                return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def grava(edicio, catala, veu, desti):
    import numpy as np
    motor = Matxa(veu["speaker"]) if veu["engine"] == "matxa" else Piper(veu["model"])
    peces, capitols, posicio = [], [], 0.0
    for ident, titol, text in guio(edicio, catala):
        so = motor.llegeix(text)
        capitols.append({"id": ident, "title": titol, "start": round(posicio, 2)})
        peces += [so, np.zeros(int(RATE * 0.8), dtype=np.float32)]
        posicio += (len(so) + int(RATE * 0.8)) / RATE
    tot = np.clip(np.concatenate(peces), -1, 1)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "tot.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes((tot * 32767).astype(np.int16).tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-ar", "22050", "-ac", "1", "-c:a", "aac", "-b:a", "48k", "-movflags", "+faststart", desti],
                       check=True)
    return round(len(tot) / RATE, 1), capitols


def main():
    pujar = "--sense-pujar" not in sys.argv
    instala()
    sortida = os.path.join(ARREL, "audio-sortida") if not pujar else tempfile.mkdtemp(prefix="radar-audio-")
    os.makedirs(sortida, exist_ok=True)
    pistes = []
    data = None
    for idioma, veus in VEUS.items():
        edicio = json.load(open(os.path.join(ARREL, idioma, "latest.json"), encoding="utf-8"))
        data = edicio["date"]
        for veu in veus:
            fitxer = f"{idioma}/{data}-{veu['id']}.m4a"
            os.makedirs(os.path.join(sortida, idioma), exist_ok=True)
            inici = datetime.now()
            # Si una veu falla (p. ex. la xarxa no deixa baixar-ne el model), es continua amb les altres i el podcast.
            try:
                durada, capitols = grava(edicio, idioma == "ca", veu, os.path.join(sortida, fitxer))
            except Exception as error:  # noqa: BLE001
                print(f"{fitxer}: no s'ha pogut gravar.", repr(error)[:300], flush=True)
                continue
            print(f"{fitxer}: {durada / 60:.1f} min d'àudio en {(datetime.now() - inici).seconds / 60:.1f} min", flush=True)
            pistes.append({"language": idioma, "voice": veu["id"], "name": veu["name"], "gender": veu["gender"],
                           "file": fitxer, "durationSeconds": durada, "chapters": capitols})
    # El podcast (en anglès, amb Gemini): si falla o no hi ha clau, l'àudio llegit surt igual.
    # El motiu queda a latest.json («podcastError»), sense la clau, per poder-lo llegir des de GitHub.
    avis_podcast = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import podcast
        noves = podcast.grava_tots(sortida, data)
        pistes += noves
        # Sense parelles actives no és cap error: el podcast el grava el Mac mini (Dia) i l'afegeix després.
        if not noves and podcast.ACTIVES:
            avis_podcast = "No s'ha gravat cap podcast (falta el guió del dia)."
    except SystemExit as error:
        avis_podcast = str(error)
    except Exception as error:  # noqa: BLE001 — qualsevol error del podcast no ha d'aturar l'àudio
        avis_podcast = repr(error)
    if avis_podcast:
        secret = os.environ.get("GEMINI_API_KEY", "").strip()
        if secret:
            avis_podcast = avis_podcast.replace(secret, "•••")
        avis_podcast = avis_podcast[:400]
        print("Podcast: no s'ha fet.", avis_podcast, flush=True)
    if not pistes:
        raise SystemExit("No s'ha pogut gravar cap pista: la branca «audio» es queda com estava.")
    manifest = {"schemaVersion": 1, "date": data,
                "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tracks": pistes}
    if avis_podcast:
        manifest["podcastError"] = avis_podcast
    json.dump(manifest, open(os.path.join(sortida, "latest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(os.path.join(sortida, "README.md"), "w", encoding="utf-8").write(
        "# Àudio del Radar\n\nNomés l'última edició (la branca es reescriu cada dia). La genera `eines/audio.py` de la branca `main`.\n")
    if not pujar:
        print("Àudio a", sortida)
        return
    git = lambda *args: subprocess.run(["git", "-C", sortida, *args], check=True)
    git("init", "-q")
    git("checkout", "-q", "--orphan", "audio")
    git("add", "-A")
    git("-c", "user.name=Claude", "-c", "user.email=noreply@anthropic.com", "commit", "-q", "-m", f"Àudio {data}")
    git("remote", "add", "origin", REPO)
    git("push", "-q", "-f", "origin", "audio")
    print(f"TOT CORRECTE: àudio del {data} publicat ({len(pistes)} pistes).")


if __name__ == "__main__":
    main()
