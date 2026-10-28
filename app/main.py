import os
from fastapi import FastAPI, Request
from app.routers.users import router as users_router
from app.routers.courses import router as courses_router
from app.routers.cohort import router as cohort_router
from app.routers.enrollment import router as enrollment_router
from app.routers.payment import router as payment_router
from app.routers import course_class
from app.routers import recording
from app.routers import resource
from app.routers import assignment
from app.routers import submission
from app.routers import announcement
from  slowapi import  _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter

app = FastAPI(
    title="AE OFFICIAL WEBSITE API",
    description="API for ALGORITHMIC EXPLORERS OFFICIAL WEBSITE",
    version="1.0.0",
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)
APP_ENV = os.getenv("APP_ENV", "development").lower()
IS_PRODUCTION = APP_ENV == "production"



@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    
    response.headers["X-Content-Type-Options"] = "nosniff"

   
    response.headers["X-Frame-Options"] = "DENY"

    
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    
    response.headers["Cache-Control"] = "no-store"

    
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000"
        )

   
    documentation_paths = {
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    if request.url.path not in documentation_paths:
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'"
        )

    return response


@app.get("/")
async def home():
    return {
        "message": "Welcome to the AE OFFICIAL WEBSITE API!",
        "status": "running",
    }


app.include_router(
    users_router,
    prefix="/api/v1/users",
    tags=["Users"],
)

app.include_router(
    courses_router,
    prefix="/api/v1/courses",
    tags=["Courses"],
)

app.include_router(
    cohort_router,
    prefix="/api/v1/cohorts",
    tags=["Cohorts"],
)

app.include_router(
    enrollment_router,
    prefix="/api/v1/enrollments",
    tags=["Enrollments"],
)

app.include_router(
    payment_router,
    prefix="/api/v1",
)

app.include_router(
    course_class.router,
    prefix="/api/v1/classes",
    tags=["Classes"],
)

app.include_router(
    recording.router,
    prefix="/api/v1/recordings",
    tags=["Recordings"],
)

app.include_router(
    resource.router,
    prefix="/api/v1/resources",
    tags=["Learning Resources"],
)

app.include_router(
    assignment.router,
    prefix="/api/v1/assignments",
    tags=["Assignments"],
)

app.include_router(
    submission.router,
    prefix="/api/v1/submissions",
    tags=["Submissions"],
)

app.include_router(
    announcement.router,
    prefix="/api/v1/announcements",
    tags=["Announcements"],
)
