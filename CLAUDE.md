# appcine-radar — per a Claude

Aquest repositori és la sortida de la tasca programada diària del Radar d'AppCine. Abans de fer res, llegeix `INSTRUCCIONS.md` i segueix-lo pas a pas. Regles curtes:

- Només es toquen `ca/latest.json`, `en/latest.json`, `podcast/en.json` i `arxiu/`. `INSTRUCCIONS.md`, `eines/` i aquest fitxer només els canvia el propietari (o Claude quan ell ho demana en una conversa).
- `python3 eines/validar.py` ha de dir «TOT CORRECTE» abans de cada commit.
- L'àudio el fa `python3 eines/audio.py` (pas 9): reescriu la branca `audio` amb l'àudio del dia (i el podcast, si hi ha `GEMINI_API_KEY` a l'entorn). No es toca a mà. La clau no s'escriu mai enlloc.
- El repositori és públic: cap clau, token, contrasenya ni dada personal.
- Commit «Edició AAAA-MM-DD» a `main`.
