from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import compatibility, pricing
from .db import engine, get_session
from .models import CATEGORIES, CATEGORY_LABELS, Base, Component, Frame

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Crée les tables si absentes (l'ingestion peuple ensuite les données).
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Cyclopathe", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _components_by_category(session: Session) -> dict[str, list[Component]]:
    comps = session.scalars(select(Component).order_by(Component.brand, Component.model)).all()
    return {cat: [c for c in comps if c.category == cat] for cat in CATEGORIES}


def _prune_incompatible(frame: Frame, selected: dict[str, Component]) -> dict[str, Component]:
    """Retire les composants sélectionnés devenus incompatibles avec les autres
    (ex. on change les roues → la transmission au mauvais freehub saute)."""
    changed = True
    while changed:
        changed = False
        for cat, comp in list(selected.items()):
            others = {k: v for k, v in selected.items() if k != cat}
            if not compatibility.is_compatible(frame, comp, others):
                del selected[cat]
                changed = True
    return selected


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"status": "healthy"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    frames = session.scalars(select(Frame).order_by(Frame.brand, Frame.model)).all()
    road_frames = [f for f in frames if f.discipline == "road"]
    gravel_frames = [f for f in frames if f.discipline == "gravel"]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "frames": frames,
            "road_count": len(road_frames),
            "gravel_count": len(gravel_frames),
            "brands": sorted({f.brand for f in frames}),
            "years": sorted({f.year for f in frames}, reverse=True),
        },
    )


def _get_frame_query(discipline: str = "", brand: str = "", year: str = ""):
    q = select(Frame)
    if discipline:
        q = q.where(Frame.discipline == discipline)
    if brand:
        q = q.where(Frame.brand == brand)
    if year:
        q = q.where(Frame.year == int(year))
    return q.order_by(Frame.brand, Frame.model)


@app.get("/frames", response_class=HTMLResponse)
def frame_list(
    request: Request,
    discipline: str = "",
    brand: str = "",
    year: str = "",
    page: int = 1,
    per_page: int = 5,
    session: Session = Depends(get_session),
):
    q = _get_frame_query(discipline, brand, year)

    total = len(session.scalars(q).all())
    offset = (page - 1) * per_page
    frames = session.scalars(q.offset(offset).limit(per_page)).all()

    has_next = offset + per_page < total
    return templates.TemplateResponse(
        request,
        "partials/frame_list.html",
        {
            "frames": frames,
            "page": page,
            "per_page": per_page,
            "has_next": has_next,
            "discipline": discipline,
            "brand": brand,
            "year": year,
        },
    )


@app.get("/frames/append", response_class=HTMLResponse)
def frames_append(
    request: Request,
    discipline: str = "",
    brand: str = "",
    year: str = "",
    page: int = 1,
    per_page: int = 5,
    session: Session = Depends(get_session),
):
    """Endpoint pour ajouter des cartes (sans wrapper ul/div)."""
    q = _get_frame_query(discipline, brand, year)
    offset = (page - 1) * per_page
    frames = session.scalars(q.offset(offset).limit(per_page)).all()

    total = len(session.scalars(q).all())
    has_next = offset + per_page < total

    return templates.TemplateResponse(
        request,
        "partials/frame_cards_only.html",
        {
            "frames": frames,
            "page": page,
            "per_page": per_page,
            "has_next": has_next,
            "discipline": discipline,
            "brand": brand,
            "year": year,
        },
    )


@app.post("/configure", response_class=HTMLResponse)
async def configure(request: Request, session: Session = Depends(get_session)):
    form = await request.form()

    frame = session.get(Frame, int(form["frame_id"])) if form.get("frame_id") else None
    if frame is None:
        return HTMLResponse("<div id='configurator'></div>")

    by_cat = _components_by_category(session)

    # Sélection courante depuis le formulaire (un champ <cat>_id par catégorie).
    selected: dict[str, Component] = {}
    for cat in CATEGORIES:
        cid = form.get(f"{cat}_id")
        if cid:
            comp = session.get(Component, int(cid))
            if comp is not None:
                selected[cat] = comp
    selected = _prune_incompatible(frame, selected)

    # Options encore compatibles pour chaque catégorie (au regard des autres choix).
    options: dict[str, list[Component]] = {}
    for cat in CATEGORIES:
        others = {k: v for k, v in selected.items() if k != cat}
        options[cat] = compatibility.filter_compatible(frame, by_cat[cat], others)

    totals = pricing.compute_totals(frame, selected)

    return templates.TemplateResponse(
        request,
        "partials/configurator.html",
        {
            "frame": frame,
            "categories": CATEGORIES,
            "labels": CATEGORY_LABELS,
            "options": options,
            "selected": selected,
            "totals": totals,
        },
    )
