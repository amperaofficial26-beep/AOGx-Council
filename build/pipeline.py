"""Pipeline BUILD Tahap 1: RESEARCH (Tavily + provider) -> ANALISIS -> PRODUCT PLANNING.

Berdiri sendiri dari core/pipeline (diskusi Council) supaya fitur lama tidak berubah.
run() menghasilkan event berupa dict agar UI bisa menampilkan proses live:
  {"kind": "status", "text": ...}
  {"kind": "agent", "stage": ..., "role": ..., "provider": ..., "text": ...}
  {"kind": "final", "research": ..., "analysis": ..., "blueprint": ..., "sources": ...,
   "providers": [...], "form_kind": ..., "references": [...]}
  {"kind": "error", "text": ...}
Tidak ada pembuatan kode aplikasi di tahap ini.
"""
from agent import build_analyst, build_planner, build_research
from core.router import AllProvidersFailed


def _status(text):
    return {"kind": "status", "text": text}


def _agent(stage, role, provider, text):
    return {"kind": "agent", "stage": stage, "role": role,
            "provider": provider or "-", "text": text}


def run(router, request: str, references: list, form_kind: str = ""):
    """Jalankan riset + analisis + perencanaan. Menghasilkan event (generator)."""
    used = []
    try:
        yield _status("RESEARCH: mencari sumber tentang aplikasi referensi…")
        research, sources, prov = build_research.gather(router, request, references)
        if prov:
            used.append(prov)
        n_claims = len(research.get("claims") or [])
        n_missing = len(research.get("missing") or [])
        summary = (f"Klaim bersumber: {n_claims} · topik tanpa bukti: {n_missing} · "
                   f"sumber unik: {len(sources)}")
        yield _agent("RESEARCH", "Researcher", prov, summary)

        yield _status("ANALISIS: memetakan kekurangan dan merancang konsep alternatif…")
        analysis, prov = build_analyst.analyze(router, request, references, research)
        used.append(prov)
        yield _agent("ANALISIS", "Analis", prov, analysis)

        yield _status("PRODUCT PLANNING: menyusun blueprint aplikasi…")
        blueprint, prov = build_planner.plan(router, request, references, analysis,
                                             form_kind=form_kind)
        used.append(prov)
        yield _agent("PLANNING", "Perencana", prov,
                     blueprint.get("nama") or "(nama belum tersusun)")

        yield {"kind": "final",
               "request": request,
               "research": research,
               "analysis": analysis,
               "blueprint": blueprint,
               "sources": sources,
               "providers": sorted({u for u in used if u and u != "-"}),
               "references": list(references or []),
               "form_kind": form_kind}

    except AllProvidersFailed as e:
        yield {"kind": "error", "text": str(e)}
    except Exception as e:  # jangan bocorkan detail internal ke UI
        if e.__class__.__name__ == "AllProvidersFailed":
            message = str(e).strip() or (
                "Semua provider gagal atau tidak aktif. Periksa API key, model, dan koneksi provider."
            )
        else:
            message = f"Terjadi kesalahan tak terduga ({e.__class__.__name__})."
        yield {"kind": "error", "text": message}
