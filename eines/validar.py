#!/usr/bin/env python3
"""Comprova les edicions del Radar abans de pujar-les.

Fa les mateixes comprovacions que AppCine (AppCine/Models/EditorialIssue.swift) i unes quantes de més, perquè una edició
que l'app rebutgi no arribi mai a `latest.json`:

    python3 eines/validar.py                # ca/latest.json i en/latest.json, amb la data d'avui (Europe/Madrid)
    python3 eines/validar.py --sense-data   # sense exigir que siguin d'avui (per provar)

Acaba amb «TOT CORRECTE» o amb la llista d'errors (i codi de sortida 1).
"""
import json
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MADRID = ZoneInfo("Europe/Madrid")
MAX_BYTES = 100_000
MAX_REPORTS = 12
SECTIONS = {"news", "cinema", "services", "physical", "stage", "projects", "festivals", "calendar", "recommendation"}
STATUSES = {"confirmed", "announced", "negotiation", "rumour", "unverified"}
EVIDENCE = {"primarySource", "corroborated", "singleSource", "unverified"}
SOURCE_KINDS = {"official", "catalogue", "tradePress", "other"}
SUBJECTS = {"film", "series"}
ACCESS_MODES = {"free", "subscription", "rental", "purchase", "liveBroadcast", "physical"}
SCOPES = {"selectedHighlights", "reportedComplete"}
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
TERRITORY = re.compile(r"^[A-Z]{2}$")
URL = re.compile(r"^https?://[A-Za-z0-9.-]+(:\d+)?(/[!-~]*)?$")


class Errors(list):
    def need(self, ok, message):
        if not ok:
            self.append(message)
        return ok


def valid_day(text):
    if not isinstance(text, str) or not DAY.match(text):
        return False
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%Y-%m-%d") == text
    except ValueError:
        return False


def valid_stamp(text):
    if not isinstance(text, str) or not STAMP.match(text):
        return False
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def valid_url(text):
    return isinstance(text, str) and text.isascii() and bool(URL.match(text)) and '"' not in text and " " not in text


def text_ok(value, low, high):
    return isinstance(value, str) and value.strip() != "" and low <= len(value) <= high


def optional_text(value, high=200):
    return value is None or text_ok(value, 1, high)


def check_issue(path, errors, today):
    tag = os.path.relpath(path, ARREL)
    if not errors.need(os.path.exists(path), f"{tag}: no existeix"):
        return None
    raw = open(path, "rb").read()
    errors.need(len(raw) <= MAX_BYTES, f"{tag}: fa {len(raw)} bytes (màxim {MAX_BYTES})")
    try:
        issue = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        errors.append(f"{tag}: no és JSON UTF-8 vàlid ({error})")
        return None
    if not errors.need(isinstance(issue, dict), f"{tag}: ha de ser un objecte JSON"):
        return None
    errors.need(issue.get("schemaVersion") == 1, f"{tag}: schemaVersion ha de ser 1")
    errors.need(valid_day(issue.get("date")), f"{tag}: date ha de ser AAAA-MM-DD")
    if today:
        errors.need(issue.get("date") == today, f"{tag}: la data és {issue.get('date')} i avui (Madrid) és {today}")
    errors.need(isinstance(issue.get("territory"), str) and bool(TERRITORY.match(issue["territory"])),
                f"{tag}: territory ha de ser dues lletres majúscules")
    errors.need(valid_stamp(issue.get("generatedAt")), f"{tag}: generatedAt ha de ser ISO 8601 amb zona horària")
    reports = issue.get("reports")
    if not errors.need(isinstance(reports, list) and 1 <= len(reports) <= MAX_REPORTS,
                       f"{tag}: reports ha de tenir entre 1 i {MAX_REPORTS} reportatges"):
        return issue
    seen = set()
    current_year = datetime.now(MADRID).year
    for index, report in enumerate(reports):
        where = f"{tag} reportatge {index + 1}"
        if not errors.need(isinstance(report, dict), f"{where}: ha de ser un objecte"):
            continue
        rid = report.get("id")
        errors.need(isinstance(rid, str) and rid.strip() != "" and rid not in seen, f"{where}: id buit o repetit ({rid!r})")
        seen.add(rid)
        where = f"{tag} [{rid}]"
        section = report.get("section")
        errors.need(section in SECTIONS, f"{where}: section no vàlida ({section!r})")
        subject = report.get("subject")
        errors.need(subject is None or subject in SUBJECTS, f"{where}: subject ha de ser film o series")
        errors.need(not (subject == "series" and section in ("cinema", "stage")),
                    f"{where}: una sèrie no pot anar a cinema ni a stage")
        errors.need(text_ok(report.get("headline"), 1, 200), f"{where}: headline buit o de més de 200 caràcters")
        errors.need(text_ok(report.get("deck"), 1, 500), f"{where}: deck buit o de més de 500 caràcters")
        paragraphs = report.get("paragraphs")
        errors.need(isinstance(paragraphs, list) and 1 <= len(paragraphs) <= 8
                    and all(text_ok(p, 1, 1500) for p in paragraphs),
                    f"{where}: paragraphs ha de tenir d'1 a 8 paràgrafs d'1 a 1.500 caràcters")
        errors.need(valid_stamp(report.get("publishedAt")), f"{where}: publishedAt ha de ser ISO 8601 amb zona horària")
        event = report.get("eventDate")
        errors.need(event is None or valid_day(event), f"{where}: eventDate ha de ser AAAA-MM-DD o null")
        territory = report.get("territory")
        errors.need(territory is None or (isinstance(territory, str) and bool(TERRITORY.match(territory))),
                    f"{where}: territory ha de ser dues lletres majúscules o null")
        errors.need(report.get("status") in STATUSES, f"{where}: status no vàlid ({report.get('status')!r})")
        errors.need(report.get("evidence") in EVIDENCE, f"{where}: evidence no vàlid ({report.get('evidence')!r})")
        sources = report.get("sources")
        urls = []
        if errors.need(isinstance(sources, list) and len(sources) >= 1, f"{where}: cal almenys una font"):
            for source in sources:
                ok = isinstance(source, dict) and text_ok(source.get("name"), 1, 300) \
                    and valid_url(source.get("url")) and source.get("kind") in SOURCE_KINDS
                errors.need(ok, f"{where}: font mal feta ({source!r})")
                if isinstance(source, dict):
                    urls.append(source.get("url"))
            errors.need(len(set(urls)) == len(urls), f"{where}: hi ha enllaços de font repetits")
        kinds_by_url = {s.get("url"): s.get("kind") for s in sources or [] if isinstance(s, dict)}

        report_titles = report.get("titles")
        if report_titles is not None:
            if errors.need(isinstance(report_titles, list) and len(report_titles) <= 12,
                           f"{where}: titles ha de ser una llista de 12 títols com a màxim"):
                for entry in report_titles:
                    ok = isinstance(entry, dict) and text_ok(entry.get("title"), 1, 200) \
                        and (entry.get("year") is None or (isinstance(entry["year"], int) and 1895 <= entry["year"] <= current_year + 5)) \
                        and entry.get("kind") in ("film", "series") \
                        and (entry.get("knownAs") is None or text_ok(entry.get("knownAs"), 1, 200)) \
                        and not re.search(r"\(\d{4}\)\s*$", entry.get("title") or "")
                    errors.need(ok, f"{where}: títol del reportatge mal fet ({entry!r}); cal title (sense l'any), year si consta i kind film/series")

        performance = report.get("filmedPerformance")
        if performance is not None:
            p = performance
            ok = isinstance(p, dict) and section == "stage" and p.get("kind") in ("theatre", "opera") \
                and text_ok(p.get("workTitle"), 1, 200) \
                and isinstance(p.get("creators"), list) and 1 <= len(p["creators"]) <= 10 \
                and all(text_ok(c, 1, 120) for c in p["creators"]) \
                and isinstance(p.get("recordingYear"), int) and 1895 <= p["recordingYear"] <= current_year + 1 \
                and (p.get("workYear") is None or (isinstance(p["workYear"], int) and -1000 <= p["workYear"] <= p["recordingYear"])) \
                and valid_url(p.get("completeRecordingSource")) \
                and kinds_by_url.get(p.get("completeRecordingSource")) in ("official", "catalogue") \
                and (p.get("recordingDate") is None or valid_day(p["recordingDate"])) \
                and (p.get("audiovisualReleaseDate") is None or valid_day(p["audiovisualReleaseDate"])) \
                and (p.get("durationMinutes") is None or (isinstance(p["durationMinutes"], int) and 1 <= p["durationMinutes"] <= 600)) \
                and all(optional_text(p.get(k)) for k in ("venue", "director", "musicalDirector", "language")) \
                and all(text_ok(c, 1, 120) for c in (p.get("principalCast") or [])) \
                and all(text_ok(s, 1, 80) for s in (p.get("subtitles") or []))
            errors.need(ok, f"{where}: filmedPerformance incorrecte (secció stage, any de captació, enllaç de la "
                            f"captació completa entre les fonts amb kind official o catalogue…)")
            access_ids = set()
            for access in (p.get("access") or []) if isinstance(p, dict) else []:
                ok = isinstance(access, dict) and text_ok(access.get("provider"), 1, 120) \
                    and isinstance(access.get("territory"), str) and bool(TERRITORY.match(access["territory"])) \
                    and access.get("mode") in ACCESS_MODES and valid_url(access.get("sourceURL")) \
                    and valid_stamp(access.get("checkedAt")) \
                    and (access.get("startsOn") is None or valid_day(access["startsOn"])) \
                    and (access.get("expiresOn") is None or valid_day(access["expiresOn"])) \
                    and (access.get("startsOn") is None or access.get("expiresOn") is None
                         or access["startsOn"] <= access["expiresOn"])
                errors.need(ok, f"{where}: accés mal fet ({access!r})")
                if isinstance(access, dict):
                    key = (access.get("provider"), access.get("territory"), access.get("mode"), access.get("sourceURL"))
                    errors.need(key not in access_ids, f"{where}: accés repetit")
                    access_ids.add(key)

        programme = report.get("festivalProgramme")
        if programme is not None:
            g = programme
            ok = isinstance(g, dict) and section == "festivals" and text_ok(g.get("festivalName"), 1, 200) \
                and isinstance(g.get("editionYear"), int) and 1895 <= g["editionYear"] <= current_year + 2 \
                and g.get("scope") in SCOPES and valid_url(g.get("officialProgrammeURL")) \
                and kinds_by_url.get(g.get("officialProgrammeURL")) == "official" \
                and isinstance(g.get("entries"), list) and 1 <= len(g["entries"]) <= 80
            errors.need(ok, f"{where}: festivalProgramme incorrecte (secció festivals, enllaç oficial entre les fonts "
                            f"amb kind official, d'1 a 80 entrades…)")
            entry_ids = set()
            for entry in (g.get("entries") or []) if isinstance(g, dict) else []:
                ok = isinstance(entry, dict) and text_ok(entry.get("id"), 1, 200) and entry.get("id") not in entry_ids \
                    and text_ok(entry.get("section"), 1, 120) and text_ok(entry.get("title"), 1, 200) \
                    and (entry.get("country") is None or (isinstance(entry["country"], str) and bool(TERRITORY.match(entry["country"])))) \
                    and optional_text(entry.get("director")) \
                    and (entry.get("synopsis") is None or text_ok(entry["synopsis"], 1, 600)) \
                    and (entry.get("sessionAt") is None or valid_stamp(entry["sessionAt"])) \
                    and optional_text(entry.get("venue")) \
                    and (entry.get("recommended") is None or isinstance(entry["recommended"], bool)) \
                    and (entry.get("sourceURL") is None or valid_url(entry["sourceURL"]))
                errors.need(ok, f"{where}: entrada de programa mal feta ({entry.get('id') if isinstance(entry, dict) else entry!r})")
                if isinstance(entry, dict):
                    entry_ids.add(entry.get("id"))

    titles = issue.get("recommendedTitles")
    if errors.need(isinstance(titles, list) and 1 <= len(titles) <= 80,
                   f"{tag}: recommendedTitles ha de ser una llista d'1 a 80 títols (la llista «Títol original (ANY)»)"):
        seen_titles = set()
        for entry in titles:
            ok = isinstance(entry, dict) and text_ok(entry.get("title"), 1, 200) \
                and isinstance(entry.get("year"), int) and 1895 <= entry["year"] <= current_year + 2 \
                and entry.get("kind") in ("film", "stage") \
                and (entry.get("knownAs") is None or text_ok(entry.get("knownAs"), 1, 200)) \
                and not re.search(r"\(\d{4}\)\s*$", entry.get("title") or "")
            errors.need(ok, f"{tag}: títol recomanat mal fet ({entry!r}); cal title (sense l'any), year i kind film/stage")
            if isinstance(entry, dict):
                key = (str(entry.get("title")).strip().lower(), entry.get("year"), entry.get("kind"))
                errors.need(key not in seen_titles, f"{tag}: títol recomanat repetit ({entry.get('title')})")
                seen_titles.add(key)

    errors.need(any(isinstance(r, dict) and r.get("section") == "stage" for r in reports),
                f"{tag}: falta el reportatge obligatori de teatre i òpera filmats (section stage)")
    errors.need(any(isinstance(r, dict) and r.get("section") == "recommendation" for r in reports),
                f"{tag}: falten les recomanacions de l'editor (section recommendation)")
    return issue


def same_shape(ca, en, errors):
    """Les dues edicions són la mateixa, traduïda: mateixos reportatges, en el mateix ordre i amb les mateixes dades."""
    if not ca or not en:
        return
    errors.need(ca.get("date") == en.get("date"), "ca i en tenen dates diferents")
    errors.need(ca.get("recommendedTitles") == en.get("recommendedTitles"),
                "recommendedTitles ha de ser idèntica en ca i en (són títols originals)")
    ids_ca = [r.get("id") for r in ca.get("reports", []) if isinstance(r, dict)]
    ids_en = [r.get("id") for r in en.get("reports", []) if isinstance(r, dict)]
    errors.need(ids_ca == ids_en, f"ca i en no tenen els mateixos reportatges en el mateix ordre: {ids_ca} / {ids_en}")
    for a, b in zip(ca.get("reports", []), en.get("reports", [])):
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        for key in ("section", "subject", "status", "evidence", "eventDate", "territory", "titles"):
            errors.need(a.get(key) == b.get(key), f"[{a.get('id')}]: {key} és diferent en ca i en")
        errors.need([s.get("url") for s in a.get("sources", []) if isinstance(s, dict)]
                    == [s.get("url") for s in b.get("sources", []) if isinstance(s, dict)],
                    f"[{a.get('id')}]: les fonts són diferents en ca i en")


ETIQUETES = {"laugh", "laughter", "laughs", "chuckle", "chuckles", "giggle", "sigh", "sighs", "short pause", "long pause",
             "breath", "gasp", "tsk", "snicker", "exhales", "throat-clearing", "phew", "pff", "cough", "groan"}


def check_podcast(en, errors):
    """podcast/en.json (apartat 10 d'INSTRUCCIONS): el guió del podcast en anglès de l'edició d'avui."""
    path = os.path.join(ARREL, "podcast", "en.json")
    if not errors.need(os.path.exists(path), "falta podcast/en.json (el guió del podcast, apartat 10)"):
        return
    try:
        script = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"podcast/en.json: no és JSON UTF-8 vàlid ({error})")
        return
    if not errors.need(isinstance(script, dict), "podcast/en.json ha de ser un objecte"):
        return
    errors.need(script.get("schemaVersion") == 1, "podcast/en.json: schemaVersion ha de ser 1")
    if en:
        errors.need(script.get("date") == en.get("date"), "podcast/en.json: la data ha de ser la de l'edició")
    segments = script.get("segments")
    if not errors.need(isinstance(segments, list) and 4 <= len(segments) <= 20,
                       "podcast/en.json: «segments» ha de ser una llista de 4 a 20 trossos"):
        return
    report_ids = {r.get("id") for r in (en or {}).get("reports", []) if isinstance(r, dict)}
    words, ids = 0, []
    for number, segment in enumerate(segments, 1):
        tag = f"podcast/en.json, segment {number}"
        if not errors.need(isinstance(segment, dict), f"{tag}: ha de ser un objecte"):
            continue
        ident = segment.get("id")
        errors.need(ident in report_ids or ident in ("intro", "outro", "picks"),
                    f"{tag}: «id» ha de ser el d'un reportatge de l'edició, «intro», «picks» o «outro»")
        ids.append(ident)
        errors.need(text_ok(segment.get("title"), 2, 90), f"{tag}: «title» (2–90 caràcters)")
        turns = segment.get("turns")
        if not errors.need(isinstance(turns, list) and 2 <= len(turns) <= 40, f"{tag}: «turns», de 2 a 40 torns"):
            continue
        for turn in turns:
            if not errors.need(isinstance(turn, dict) and turn.get("speaker") in ("A", "B")
                               and text_ok(turn.get("text"), 2, 900), f"{tag}: cada torn porta «speaker» A o B i «text» (fins a 900 caràcters)"):
                continue
            for etiqueta in re.findall(r"<([^<>]+)>", turn["text"]):
                errors.need(etiqueta.strip().lower() in ETIQUETES, f"{tag}: etiqueta desconeguda <{etiqueta}>")
            if turn.get("style") is not None:
                errors.need(text_ok(turn.get("style"), 2, 60), f"{tag}: «style», curt (fins a 60 caràcters)")
            words += len(re.sub(r"<[^<>]+>|\|[^|]*\|", " ", turn["text"]).split())
    errors.need(len(ids) == len(set(ids)), "podcast/en.json: hi ha segments repetits")
    pron = script.get("pronunciations", {})
    errors.need(isinstance(pron, dict) and len(pron) <= 150
                and all(text_ok(k, 2, 80) and text_ok(v, 2, 120) for k, v in pron.items()),
                "podcast/en.json: «pronunciations» ha de ser un objecte {nom: com es llegeix} (fins a 150, textos curts)")
    errors.need(ids[:1] == ["intro"] and ids[-1:] == ["outro"], "podcast/en.json: comença amb «intro» i acaba amb «outro»")
    errors.need(2400 <= words <= 3800, f"podcast/en.json: {words} paraules; han de ser entre 2.400 i 3.800 (uns 20 minuts)")


def main():
    today = None if "--sense-data" in sys.argv else datetime.now(MADRID).strftime("%Y-%m-%d")
    errors = Errors()
    ca = check_issue(os.path.join(ARREL, "ca", "latest.json"), errors, today)
    en = check_issue(os.path.join(ARREL, "en", "latest.json"), errors, today)
    same_shape(ca, en, errors)
    if "--sense-podcast" not in sys.argv:
        check_podcast(en, errors)
    for language, issue in (("ca", ca), ("en", en)):
        if issue and isinstance(issue.get("date"), str):
            archived = os.path.join(ARREL, "arxiu", language, f"{issue['date']}.json")
            latest = os.path.join(ARREL, language, "latest.json")
            errors.need(os.path.exists(archived) and open(archived, "rb").read() == open(latest, "rb").read(),
                        f"falta la còpia idèntica a arxiu/{language}/{issue['date']}.json")
    index_path = os.path.join(ARREL, "arxiu", "index.json")
    try:
        index = json.load(open(index_path, encoding="utf-8"))
        dates = index.get("dates") if isinstance(index, dict) else None
    except (OSError, json.JSONDecodeError):
        dates = None
    if errors.need(isinstance(dates, list) and all(valid_day(d) for d in dates),
                   "arxiu/index.json ha de ser {\"dates\": [\"AAAA-MM-DD\", …]}"):
        errors.need(dates == sorted(set(dates), reverse=True), "arxiu/index.json: dates de la més nova a la més antiga i sense repetir")
        if ca and isinstance(ca.get("date"), str):
            errors.need(ca["date"] in dates, f"arxiu/index.json: hi falta {ca['date']}")
        for day in dates:
            for language in ("ca", "en"):
                errors.need(os.path.exists(os.path.join(ARREL, "arxiu", language, f"{day}.json")),
                            f"arxiu/index.json diu {day} però no hi ha arxiu/{language}/{day}.json")
    if errors:
        print(f"{len(errors)} ERRORS:")
        for error in errors:
            print(" -", error)
        sys.exit(1)
    sizes = ", ".join(f"{lang} {os.path.getsize(os.path.join(ARREL, lang, 'latest.json')) // 1024} KB" for lang in ("ca", "en"))
    print(f"TOT CORRECTE: {len(ca['reports'])} reportatges del {ca['date']} ({sizes}).")


if __name__ == "__main__":
    main()
