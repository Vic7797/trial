from fastapi import APIRouter
from app.api.v1 import (
    auth,
    users,
    categories,
    documents,
    tickets,
    analytics,
    organizations,
    payments
)

# Create main v1 router
router = APIRouter(prefix="/api/v1")

# Include all routers
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(categories.router)
router.include_router(documents.router)
router.include_router(tickets.router)
router.include_router(analytics.router)
router.include_router(organizations.router)
router.include_router(payments.router)