"""HTML page routes."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Dashboard"
    })


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "title": "Login"
    })


@router.get("/files", response_class=HTMLResponse)
async def files_page(request: Request):
    """Files list page."""
    return templates.TemplateResponse("data_files.html", {
        "request": request,
        "title": "Data Files"
    })


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """File upload page."""
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "title": "Upload File"
    })


@router.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    """Jobs list page."""
    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "title": "Jobs"
    })


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Reports page."""
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "title": "Reports"
    })


@router.get("/logout")
async def logout():
    """Logout and redirect to login."""
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response
