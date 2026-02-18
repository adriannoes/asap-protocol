"""Delegation token REST API (v1.3). Requires OAuth2 and a delegation key store.

POST /asap/delegations creates a signed delegation token. The authenticated
agent (from OAuth2 claims) is the delegator; the request body specifies
delegate URN and scopes. The server must have the delegator's Ed25519 key
via app.state.delegation_key_store(delegator_urn) -> Ed25519PrivateKey.

DELETE /asap/delegations/{id} revokes a token. Only the delegator (issuer) can
revoke. Requires app.state.delegation_storage (DelegationStorage).

Validation: use Depends(require_delegation("task.execute")) on routes that
require a delegation token. Header X-ASAP-Delegation-Token must contain the
JWT. App state must set delegation_public_key_resolver(iss) -> Ed25519PublicKey.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Callable, cast

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from asap.auth.middleware import OAuth2Claims
from asap.auth.scopes import SCOPE_EXECUTE, require_scope
from asap.economics.delegation import (
    DelegationConstraints,
    create_delegation_jwt,
    get_jti_from_jwt,
)
from asap.economics.delegation_storage import DelegationStorage
from asap.models.base import ASAPBaseModel
from asap.observability import get_logger

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

logger = get_logger(__name__)

# Header for delegation token (validate before handler).
X_ASAP_DELEGATION_HEADER = "X-ASAP-Delegation-Token"


class DelegationTokenSummary(ASAPBaseModel):
    id: str = Field(..., description="Token ID (jti).")
    delegator: str = Field(..., description="URN of the issuer.")
    delegate: str = Field(..., description="URN of the delegate (holder).")
    created_at: datetime = Field(..., description="Creation time (UTC).")
    active: bool = Field(..., description="True if not revoked.")


class DelegationTokenDetail(ASAPBaseModel):
    id: str = Field(..., description="Token ID (jti).")
    delegator: str = Field(..., description="URN of the issuer.")
    delegate: str = Field(..., description="URN of the delegate (holder).")
    created_at: datetime = Field(..., description="Creation time (UTC).")
    active: bool = Field(..., description="True if not revoked.")
    revoked_at: datetime | None = Field(None, description="Revocation time (UTC) if revoked.")


class CreateDelegationRequest(ASAPBaseModel):
    delegate: str = Field(..., description="URN of the agent receiving the delegation.")
    scopes: list[str] = Field(
        ...,
        min_length=1,
        description="Allowed scopes (e.g. task.execute, data.read or *).",
    )
    expires_in_seconds: int | None = Field(
        86400,
        ge=1,
        le=365 * 24 * 3600,
        description="Token validity in seconds (default 24h).",
    )
    max_tasks: int | None = Field(
        None,
        ge=0,
        description="Maximum tasks the delegate may perform.",
    )


def _get_delegation_key_store(
    request: Request,
) -> Callable[[str], "Ed25519PrivateKey"]:
    store = getattr(request.app.state, "delegation_key_store", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Delegation API not configured (delegation_key_store not set)",
        )
    return cast(Callable[[str], "Ed25519PrivateKey"], store)


def _get_delegation_storage(request: Request) -> DelegationStorage:
    storage = getattr(request.app.state, "delegation_storage", None)
    if storage is None:
        raise HTTPException(
            status_code=503,
            detail="Delegation revocation not configured (delegation_storage not set)",
        )
    return cast(DelegationStorage, storage)


def create_delegation_router() -> APIRouter:
    """Create the delegation API router. Mount under /asap so OAuth2 protects it."""
    router = APIRouter(
        prefix="/delegations",
        tags=["delegations"],
    )

    @router.post(
        "",
        status_code=201,
    )
    async def post_delegation(
        request: Request,
        body: CreateDelegationRequest,
        claims: OAuth2Claims = Depends(require_scope(SCOPE_EXECUTE)),
    ) -> JSONResponse:
        delegator_urn = claims.sub
        key_store = _get_delegation_key_store(request)
        try:
            private_key = key_store(delegator_urn)
        except (KeyError, ValueError) as e:
            logger.warning(
                "asap.delegation.key_not_found",
                delegator=delegator_urn,
                error=str(e),
            )
            raise HTTPException(
                status_code=503,
                detail="Delegation key not configured for this agent",
            ) from e

        now = datetime.now(timezone.utc)
        expires_in = body.expires_in_seconds if body.expires_in_seconds is not None else 86400
        expires_at = now + timedelta(seconds=expires_in)
        constraints = DelegationConstraints(
            max_tasks=body.max_tasks,
            max_cost_usd=None,
            expires_at=expires_at,
        )
        token = create_delegation_jwt(
            delegator_urn=delegator_urn,
            delegate_urn=body.delegate,
            scopes=body.scopes,
            constraints=constraints,
            private_key=private_key,
        )
        storage = getattr(request.app.state, "delegation_storage", None)
        if storage is not None:
            jti = get_jti_from_jwt(token)
            if jti:
                await cast(DelegationStorage, storage).register_issued(
                    jti, delegator_urn, delegate_urn=body.delegate
                )
        return JSONResponse(
            status_code=201,
            content={"token": token},
        )

    @router.delete(
        "/{token_id}",
        status_code=204,
    )
    async def delete_delegation(
        request: Request,
        token_id: str,
        claims: OAuth2Claims = Depends(require_scope(SCOPE_EXECUTE)),
    ) -> None:
        storage = _get_delegation_storage(request)
        delegator_urn = await storage.get_delegator(token_id)
        if delegator_urn is None:
            raise HTTPException(
                status_code=404,
                detail="Delegation token not found or not issued via this server",
            )
        if delegator_urn != claims.sub:
            raise HTTPException(
                status_code=403,
                detail="Only the delegator that issued this token can revoke it",
            )
        await storage.revoke_cascade(token_id)

    @router.get(
        "",
        status_code=200,
    )
    async def list_delegations(
        request: Request,
        active: bool = True,
        claims: OAuth2Claims = Depends(require_scope(SCOPE_EXECUTE)),
    ) -> list[DelegationTokenSummary]:
        storage = _get_delegation_storage(request)
        delegator_urn = claims.sub
        summaries = await storage.list_issued_summaries(delegator_urn)
        revoked_map = await storage.are_revoked([s.id for s in summaries])
        return [
            DelegationTokenSummary(
                id=s.id,
                delegator=delegator_urn,
                delegate=s.delegate_urn or "",
                created_at=s.created_at,
                active=not revoked_map.get(s.id, False),
            )
            for s in summaries
            if not (active and revoked_map.get(s.id, False))
        ]

    @router.get(
        "/{token_id}",
        status_code=200,
    )
    async def get_delegation(
        request: Request,
        token_id: str,
        claims: OAuth2Claims = Depends(require_scope(SCOPE_EXECUTE)),
    ) -> DelegationTokenDetail:
        storage = _get_delegation_storage(request)
        detail = await storage.get_token_detail(token_id)
        if detail is None:
            raise HTTPException(
                status_code=404,
                detail="Delegation token not found",
            )
        delegate_urn = detail.delegate_urn or ""
        if claims.sub != detail.delegator_urn and claims.sub != delegate_urn:
            raise HTTPException(
                status_code=403,
                detail="Only the issuer or holder of this token can view it",
            )
        return DelegationTokenDetail(
            id=detail.id,
            delegator=detail.delegator_urn,
            delegate=delegate_urn,
            created_at=detail.created_at,
            active=not detail.is_revoked,
            revoked_at=detail.revoked_at,
        )

    return router
