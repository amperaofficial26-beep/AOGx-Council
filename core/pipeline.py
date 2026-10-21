"""Pipeline AOGx-Council: orchestrator -> riset -> diskusi -> sintesis -> verifikasi -> gerbang kualitas.
run() adalah generator yang menghasilkan event supaya UI bisa menampilkan proses secara live."""
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Generator, List

import config
from agents import debaters, orchestrator, researcher, synthesizer, verifier
from core.router import AllProvidersFailed

ROLES = ["analyst", "skeptic", "expert"]


def _agent(stage, role, provider, text):
    return {"kind": "agent", "stage": stage, "role": role, "provider": provider, "text": text}


def _status(text):
    return {"kind": "status", "text": text}


def _parallel(tasks: Dict[str, Callable]) -> Dict[str, object]:
    """Jalankan beberapa agen bersamaan. Hasil: {role: (teks, provider) | Exception}."""
    out = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = {role: ex.submit(fn) for role, fn in tasks.items()}
        for role, fut in futures.items():
            try:
                out[role] = fut.result()
            except Exception as e:  # satu agen gagal tidak boleh menjatuhkan seluruh diskusi
                out[role] = e
    return out


def run(router, question: str, mode_name: str, history: str = "") -> Generator[dict, None, None]:
    mode = config.MODES[mode_name]
    used = []  # provider yang terpakai, untuk transparansi

    try:
        yield _status("Orchestrator menganalisis pertanyaan…")
        plan, prov = orchestrator.plan(router, question, history)
        used.append(prov)
        yield _agent("Perencanaan", "Orchestrator", prov, json.dumps(plan, ensure_ascii=False, indent=2))

        # --- Lapis riset ---
        notes, sources = "", []
        if plan["needs_web"] and router.tavily.available():
            yield _status("Researcher mencari sumber web…")
            notes, sources, prov = researcher.gather(router, plan, question)
            if notes:
                used.append(prov)
                yield _agent("Riset", "Researcher", prov, notes)

        # --- Lapis diskusi ---
        simple = plan["complexity"] == "simple" and mode_name != "Mendalam"
        latest: Dict[str, str] = {}
        if not simple:
            yield _status("Agen berdiskusi (putaran 1)…")
            res = _parallel({r: (lambda r=r: debaters.opening(
                router, r, question, notes, plan["focus_points"], history)) for r in ROLES})
            for r, v in res.items():
                if isinstance(v, Exception):
                    yield _agent("Diskusi putaran 1", debaters.label(r), "-", f"(gagal: {v})")
                else:
                    latest[r] = v[0]
                    used.append(v[1])
                    yield _agent("Diskusi putaran 1", debaters.label(r), v[1], v[0])

            for rnd in range(2, mode["rounds"] + 1):
                if len(latest) < 2:
                    break
                yield _status(f"Agen berdiskusi (putaran {rnd})…")
                snapshot = dict(latest)
                res = _parallel({r: (lambda r=r: debaters.rebuttal(
                    router, r, question, notes, snapshot[r],
                    {o: t for o, t in snapshot.items() if o != r})) for r in snapshot})
                for r, v in res.items():
                    if isinstance(v, Exception):
                        continue  # pertahankan jawaban putaran sebelumnya
                    latest[r] = v[0]
                    used.append(v[1])
                    yield _agent(f"Diskusi putaran {rnd}", debaters.label(r), v[1], v[0])

        debate = {debaters.label(r): t for r, t in latest.items()}

        # --- Lapis sintesis ---
        yield _status("Menyusun jawaban final…")
        answer, prov = synthesizer.synthesize(router, question, notes, debate, history)
        used.append(prov)
        yield _agent("Sintesis", "Penyusun", prov, answer)

        # --- Lapis verifikasi + gerbang kualitas ---
        score, issues = None, []
        if mode["verify"] and not simple:
            for attempt in range(mode["max_retries"] + 1):
                yield _status("Verifier memeriksa jawaban…")
                try:
                    v, prov = verifier.verify(router, question, answer, notes)
                except AllProvidersFailed:
                    break
                used.append(prov)
                score, issues = v["score"], v["issues"]
                yield _agent("Verifikasi", "Verifier", prov,
                             f"Skor: {score:.2f}\n" + ("\n".join(f"- {i}" for i in issues) or "Tidak ada masalah berarti."))
                if score >= config.QUALITY_THRESHOLD or attempt == mode["max_retries"]:
                    break
                yield _status("Skor di bawah ambang, jawaban direvisi…")
                answer, prov = synthesizer.synthesize(
                    router, question, notes, debate, history, issues=issues, previous=answer)
                used.append(prov)
                yield _agent("Revisi", "Penyusun", prov, answer)

        yield {"kind": "final", "answer": answer, "score": score, "issues": issues,
               "sources": sources, "providers": sorted({u for u in used if u and u != "-"})}

    except AllProvidersFailed as e:
        yield {"kind": "error", "text": str(e)}
    except Exception as e:  # jangan bocorkan detail internal ke UI
        yield {"kind": "error", "text": f"Terjadi kesalahan tak terduga ({e.__class__.__name__})."}
