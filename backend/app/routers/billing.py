"""
Billing API Router — Individual subscriptions, report purchases, and Stripe webhooks.

Endpoints:
  GET  /billing/individual/status     — Individual billing status
  POST /billing/individual/checkout   — Create Stripe Checkout for Pro subscription
  POST /billing/individual/portal     — Create Stripe Customer Portal session
  POST /billing/report/checkout       — Create Stripe Checkout for single report
  GET  /billing/report/{report_type}  — Get report content (if authorized)
  POST /billing/webhook               — Stripe webhook handler
"""
import logging
import json
import uuid
from datetime import datetime

import httpx
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resident import Resident
from app.models.billing import IndividualSubscription, ReportPurchase, OrgSubscription
from app.models.company import Company, CompanyMember
from app.routers.auth import get_current_resident
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = settings.stripe_secret_key

VALID_REPORT_TYPES = {"work", "romance", "relationships", "stress", "growth", "compatibility"}

REPORT_LABELS = {
    "work": {"ja": "仕事・キャリア", "en": "Work & Career"},
    "romance": {"ja": "恋愛・パートナーシップ", "en": "Romance & Partnership"},
    "relationships": {"ja": "人間関係", "en": "Interpersonal Relationships"},
    "stress": {"ja": "ストレス・メンタルケア", "en": "Stress & Mental Care"},
    "growth": {"ja": "自己成長", "en": "Self Growth"},
    "compatibility": {"ja": "相性分析", "en": "Compatibility Analysis"},
}

REPORT_PROMPTS = {
    "work": (
        "以下のSTRUCT CODE診断結果に基づいて、仕事・キャリアに関する詳細分析レポートを生成してください。"
        "この人の内面構造が仕事においてどのように発現するか、適性のある職種・環境、"
        "リーダーシップスタイル、チームでの役割、キャリア形成における強みと注意点を分析してください。"
        "2000字程度で、具体的かつ実用的な内容にしてください。"
    ),
    "romance": (
        "以下のSTRUCT CODE診断結果に基づいて、恋愛・パートナーシップに関する詳細分析レポートを生成してください。"
        "この人の内面構造が恋愛においてどのように発現するか、恋愛傾向、パートナーに求めるもの、"
        "相性の良いタイプ、関係性構築の強みと課題を分析してください。"
        "2000字程度で、具体的かつ実用的な内容にしてください。"
    ),
    "relationships": (
        "以下のSTRUCT CODE診断結果に基づいて、人間関係に関する詳細分析レポートを生成してください。"
        "この人の内面構造が対人関係においてどのように発現するか、コミュニケーションスタイル、"
        "友人関係・家族関係の傾向、信頼の築き方、対人関係における強みと課題を分析してください。"
        "2000字程度で、具体的かつ実用的な内容にしてください。"
    ),
    "stress": (
        "以下のSTRUCT CODE診断結果に基づいて、ストレス・メンタルケアに関する詳細分析レポートを生成してください。"
        "この人の内面構造がストレス反応にどう影響するか、ストレスを感じやすい場面、"
        "効果的なストレス対処法、メンタルヘルス維持のためのアドバイスを分析してください。"
        "2000字程度で、具体的かつ実用的な内容にしてください。"
    ),
    "growth": (
        "以下のSTRUCT CODE診断結果に基づいて、自己成長に関する詳細分析レポートを生成してください。"
        "この人の内面構造における成長ポテンシャル、自己実現の方向性、"
        "克服すべき課題、具体的な成長ステップ、盲点への気づきを分析してください。"
        "2000字程度で、具体的かつ実用的な内容にしてください。"
    ),
    "compatibility": (
        "以下のSTRUCT CODE診断結果に基づいて、相性分析に関する詳細レポートを生成してください。"
        "この人の内面構造が他のタイプとどのような相性を持つか、相性の良いタイプ・課題のあるタイプ、"
        "各タイプとの関わり方のコツ、補完関係と衝突ポイントを分析してください。"
        "2000字程度で、具体的かつ実用的な内容にしてください。"
    ),
}


# ── Helpers ──

async def _get_individual_sub(
    db: AsyncSession, resident_id: uuid.UUID
) -> IndividualSubscription | None:
    result = await db.execute(
        select(IndividualSubscription).where(
            IndividualSubscription.resident_id == resident_id
        )
    )
    return result.scalar_one_or_none()


async def _get_purchased_reports(
    db: AsyncSession, resident_id: uuid.UUID
) -> list[str]:
    result = await db.execute(
        select(ReportPurchase.report_type).where(
            ReportPurchase.resident_id == resident_id,
            ReportPurchase.status == "completed",
        )
    )
    return [row[0] for row in result.all()]


async def _has_report_access(
    db: AsyncSession, resident_id: uuid.UUID, report_type: str
) -> bool:
    """Check if user can access a report: Pro subscriber OR purchased that report."""
    sub = await _get_individual_sub(db, resident_id)
    if sub and sub.status == "active":
        return True
    result = await db.execute(
        select(ReportPurchase).where(
            ReportPurchase.resident_id == resident_id,
            ReportPurchase.report_type == report_type,
            ReportPurchase.status == "completed",
        )
    )
    return result.scalar_one_or_none() is not None


async def _get_or_create_stripe_customer(
    resident: Resident, sub: IndividualSubscription | None, db: AsyncSession
) -> str:
    """Get existing or create new Stripe customer."""
    if sub and sub.stripe_customer_id:
        return sub.stripe_customer_id

    customer = stripe.Customer.create(
        metadata={
            "resident_id": str(resident.id),
            "resident_name": resident.name,
        },
    )
    if sub:
        sub.stripe_customer_id = customer.id
    else:
        sub = IndividualSubscription(
            resident_id=resident.id,
            stripe_customer_id=customer.id,
        )
        db.add(sub)
    await db.flush()
    return customer.id


# ── Individual Endpoints ──

@router.get("/individual/status")
async def individual_status(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get individual billing status."""
    sub = await _get_individual_sub(db, current_resident.id)
    purchased = await _get_purchased_reports(db, current_resident.id)

    is_pro = sub is not None and sub.status == "active"
    has_diagnosed = current_resident.struct_type is not None

    return {
        "plan": "pro" if is_pro else "free",
        "plan_type": sub.plan_type if sub else None,
        "status": sub.status if sub else "none",
        "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
        "purchased_reports": purchased,
        "has_diagnosed": has_diagnosed,
        "can_chat": is_pro,
        "can_diagnose": is_pro or not has_diagnosed,
    }


@router.post("/individual/checkout")
async def individual_checkout(
    plan_type: str = Query(..., regex="^(monthly|annual)$"),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe Checkout session for individual Pro subscription."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    sub = await _get_individual_sub(db, current_resident.id)
    customer_id = await _get_or_create_stripe_customer(current_resident, sub, db)

    price_id = (
        settings.stripe_price_individual_monthly
        if plan_type == "monthly"
        else settings.stripe_price_individual_annual
    )
    if not price_id:
        raise HTTPException(status_code=503, detail="Price not configured")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={
            "type": "individual_subscription",
            "resident_id": str(current_resident.id),
            "plan_type": plan_type,
        },
        success_url=f"{settings.frontend_url}/account?checkout=success",
        cancel_url=f"{settings.frontend_url}/account?checkout=cancel",
    )

    return {"checkout_url": session.url}


@router.post("/individual/portal")
async def individual_portal(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe Customer Portal session for managing subscription."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    sub = await _get_individual_sub(db, current_resident.id)
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No subscription found")

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=f"{settings.frontend_url}/account",
    )

    return {"portal_url": session.url}


# ── Report Endpoints ──

@router.post("/report/checkout")
async def report_checkout(
    report_type: str = Query(...),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe Checkout session for a single category report."""
    if report_type not in VALID_REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {report_type}")

    if not settings.stripe_secret_key or not settings.stripe_price_report:
        raise HTTPException(status_code=503, detail="Billing not configured")

    # Check if already purchased
    existing = await db.execute(
        select(ReportPurchase).where(
            ReportPurchase.resident_id == current_resident.id,
            ReportPurchase.report_type == report_type,
            ReportPurchase.status == "completed",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Report already purchased")

    # Check if Pro subscriber (already has access)
    sub = await _get_individual_sub(db, current_resident.id)
    if sub and sub.status == "active":
        raise HTTPException(status_code=400, detail="Pro subscribers have access to all reports")

    customer_id = await _get_or_create_stripe_customer(current_resident, sub, db)

    label = REPORT_LABELS.get(report_type, {}).get("ja", report_type)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        line_items=[{"price": settings.stripe_price_report, "quantity": 1}],
        metadata={
            "type": "report_purchase",
            "resident_id": str(current_resident.id),
            "report_type": report_type,
        },
        success_url=f"{settings.frontend_url}/report/{report_type}?checkout=success",
        cancel_url=f"{settings.frontend_url}/struct-code/result/{current_resident.name}?checkout=cancel",
    )

    # Create pending purchase record
    purchase = ReportPurchase(
        resident_id=current_resident.id,
        report_type=report_type,
        stripe_checkout_session_id=session.id,
    )
    db.add(purchase)

    return {"checkout_url": session.url}


@router.get("/report/{report_type}")
async def get_report(
    report_type: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
    lang: str = Query("ja", regex="^(ja|en)$"),
):
    """Get report content. Requires Pro subscription or purchase."""
    if report_type not in VALID_REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {report_type}")

    if not await _has_report_access(db, current_resident.id, report_type):
        raise HTTPException(status_code=403, detail="Report access required. Purchase this report or subscribe to Pro.")

    if not current_resident.struct_result:
        raise HTTPException(status_code=400, detail="Please complete STRUCT CODE diagnosis first")

    # Check for cached report
    result = await db.execute(
        select(ReportPurchase).where(
            ReportPurchase.resident_id == current_resident.id,
            ReportPurchase.report_type == report_type,
            ReportPurchase.status == "completed",
        )
    )
    purchase = result.scalar_one_or_none()

    if purchase and purchase.content:
        return {
            "report_type": report_type,
            "label": REPORT_LABELS.get(report_type, {}).get(lang, report_type),
            "content": purchase.content,
            "cached": True,
        }

    # Generate report via Anthropic API
    content = await _generate_report(current_resident, report_type, lang)

    # Cache in purchase record if exists
    if purchase:
        purchase.content = content
    else:
        # Pro user — create a record for caching
        new_purchase = ReportPurchase(
            resident_id=current_resident.id,
            report_type=report_type,
            status="completed",
            content=content,
        )
        db.add(new_purchase)

    return {
        "report_type": report_type,
        "label": REPORT_LABELS.get(report_type, {}).get(lang, report_type),
        "content": content,
        "cached": False,
    }


async def _generate_report(resident: Resident, report_type: str, lang: str) -> str:
    """Generate a category report using the Anthropic API."""
    if not settings.claude_api_key:
        raise HTTPException(status_code=503, detail="AI report generation is not configured")

    struct_result = resident.struct_result
    prompt = REPORT_PROMPTS.get(report_type, "")

    # Build diagnosis context
    context_parts = [
        f"タイプ: {struct_result.get('current', {}).get('type', '')} ({struct_result.get('current', {}).get('type_name', '')})",
        f"ネイタルタイプ: {struct_result.get('natal', {}).get('type', '')} ({struct_result.get('natal', {}).get('type_name', '')})",
    ]

    axes = struct_result.get('current', {}).get('axes', [])
    axis_names = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
    if axes:
        axis_str = ", ".join(f"{axis_names[i]}: {round(v * 1000)}" for i, v in enumerate(axes) if i < len(axis_names))
        context_parts.append(f"5軸スコア: {axis_str}")

    axis_states = struct_result.get('axis_states', [])
    if axis_states:
        state_str = ", ".join(f"{s['axis']}: {s['state']}" for s in axis_states)
        context_parts.append(f"軸の状態: {state_str}")

    top_candidates = struct_result.get('top_candidates', [])
    if top_candidates:
        cand_str = ", ".join(f"{c['code']}({c['name']})" for c in top_candidates[:3])
        context_parts.append(f"候補タイプTOP3: {cand_str}")

    diagnosis_context = "\n".join(context_parts)

    full_prompt = f"{prompt}\n\n【診断結果】\n{diagnosis_context}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5-20250929",
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": full_prompt}],
                },
            )
            if response.status_code != 200:
                logger.error(f"Anthropic API error: {response.status_code} {response.text}")
                raise HTTPException(status_code=503, detail="Report generation failed")

            data = response.json()
            return data["content"][0]["text"]
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Report generation timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Report generation error: {e}")
        raise HTTPException(status_code=503, detail="Report generation failed")


# ── Stripe Webhook ──

@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if settings.stripe_webhook_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # Dev mode — parse without verification
        event = json.loads(payload)

    event_type = event.get("type", "") if isinstance(event, dict) else event.type
    data_object = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    logger.info(f"[Webhook] Received event: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(db, data_object)
        elif event_type in (
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            await _handle_subscription_updated(db, data_object)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, data_object)
    except Exception as e:
        logger.exception(f"[Webhook] Error processing {event_type}: {e}")

    return {"received": True}


async def _handle_checkout_completed(db: AsyncSession, session_data: dict):
    """Process completed checkout session."""
    metadata = session_data.get("metadata", {})
    checkout_type = metadata.get("type")
    resident_id_str = metadata.get("resident_id")

    if not resident_id_str:
        logger.warning("[Webhook] No resident_id in metadata")
        return

    resident_id = uuid.UUID(resident_id_str)

    if checkout_type == "individual_subscription":
        plan_type = metadata.get("plan_type", "monthly")
        subscription_id = session_data.get("subscription")
        customer_id = session_data.get("customer")

        sub = await _get_individual_sub(db, resident_id)
        if sub:
            sub.stripe_subscription_id = subscription_id
            sub.stripe_customer_id = customer_id
            sub.plan_type = plan_type
            sub.status = "active"
        else:
            sub = IndividualSubscription(
                resident_id=resident_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan_type=plan_type,
                status="active",
            )
            db.add(sub)
        await db.flush()
        logger.info(f"[Webhook] Individual subscription activated for {resident_id}")

    elif checkout_type == "report_purchase":
        report_type = metadata.get("report_type")
        checkout_session_id = session_data.get("id")

        # Find and complete the pending purchase
        result = await db.execute(
            select(ReportPurchase).where(
                ReportPurchase.resident_id == resident_id,
                ReportPurchase.report_type == report_type,
                ReportPurchase.status == "pending",
            )
        )
        purchase = result.scalar_one_or_none()
        if purchase:
            purchase.status = "completed"
            purchase.stripe_checkout_session_id = checkout_session_id
            logger.info(f"[Webhook] Report purchase completed: {resident_id} {report_type}")
        else:
            # Create if not found (edge case)
            purchase = ReportPurchase(
                resident_id=resident_id,
                report_type=report_type,
                stripe_checkout_session_id=checkout_session_id,
                status="completed",
            )
            db.add(purchase)
            logger.info(f"[Webhook] Report purchase created (fallback): {resident_id} {report_type}")

    elif checkout_type == "org_subscription":
        company_id_str = metadata.get("company_id")
        if not company_id_str:
            logger.warning("[Webhook] No company_id in org_subscription metadata")
            return

        company_id = uuid.UUID(company_id_str)
        plan_type = metadata.get("plan_type", "monthly")
        subscription_id = session_data.get("subscription")
        customer_id = session_data.get("customer")

        org_sub_result = await db.execute(
            select(OrgSubscription).where(OrgSubscription.company_id == company_id)
        )
        org_sub = org_sub_result.scalar_one_or_none()

        if org_sub:
            org_sub.stripe_subscription_id = subscription_id
            org_sub.stripe_customer_id = customer_id
            org_sub.plan_type = plan_type
            org_sub.status = "active"
        else:
            org_sub = OrgSubscription(
                company_id=company_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan_type=plan_type,
                status="active",
            )
            db.add(org_sub)
        await db.flush()
        logger.info(f"[Webhook] Org subscription activated for company {company_id}")


async def _handle_subscription_updated(db: AsyncSession, sub_data: dict):
    """Process subscription update/cancellation."""
    subscription_id = sub_data.get("id")
    status = sub_data.get("status")  # active, past_due, canceled, etc.
    current_period_end = sub_data.get("current_period_end")

    result = await db.execute(
        select(IndividualSubscription).where(
            IndividualSubscription.stripe_subscription_id == subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        # Check org subscriptions
        org_result = await db.execute(
            select(OrgSubscription).where(
                OrgSubscription.stripe_subscription_id == subscription_id
            )
        )
        org_sub = org_result.scalar_one_or_none()
        if org_sub:
            org_sub.status = status
            if current_period_end:
                org_sub.current_period_end = datetime.fromtimestamp(current_period_end)
            logger.info(f"[Webhook] Org subscription updated: {subscription_id} -> {status}")
        else:
            logger.warning(f"[Webhook] Subscription not found: {subscription_id}")
        return

    sub.status = status
    if current_period_end:
        sub.current_period_end = datetime.fromtimestamp(current_period_end)
    logger.info(f"[Webhook] Subscription updated: {subscription_id} -> {status}")


async def _handle_payment_failed(db: AsyncSession, invoice_data: dict):
    """Process payment failure."""
    subscription_id = invoice_data.get("subscription")
    if not subscription_id:
        return

    result = await db.execute(
        select(IndividualSubscription).where(
            IndividualSubscription.stripe_subscription_id == subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = "past_due"
        logger.info(f"[Webhook] Payment failed, set past_due: {subscription_id}")
    else:
        # Check org subscriptions
        org_result = await db.execute(
            select(OrgSubscription).where(
                OrgSubscription.stripe_subscription_id == subscription_id
            )
        )
        org_sub = org_result.scalar_one_or_none()
        if org_sub:
            org_sub.status = "past_due"
            logger.info(f"[Webhook] Org payment failed, set past_due: {subscription_id}")


# ── Organization Billing Endpoints ──

async def _get_org_sub(db: AsyncSession, company_id: uuid.UUID) -> OrgSubscription | None:
    result = await db.execute(
        select(OrgSubscription).where(OrgSubscription.company_id == company_id)
    )
    return result.scalar_one_or_none()


async def _get_company_by_slug(db: AsyncSession, slug: str) -> Company:
    result = await db.execute(select(Company).where(Company.slug == slug))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Organization not found")
    return company


async def _require_company_admin(db: AsyncSession, company: Company, resident_id: uuid.UUID):
    if company.admin_id != resident_id:
        result = await db.execute(
            select(CompanyMember).where(
                CompanyMember.company_id == company.id,
                CompanyMember.resident_id == resident_id,
                CompanyMember.role.in_(["admin", "manager"]),
                CompanyMember.status == "active",
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Organization admin access required")


@router.get("/org/{slug}/status")
async def org_billing_status(
    slug: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get organization billing status."""
    company = await _get_company_by_slug(db, slug)
    await _require_company_admin(db, company, current_resident.id)

    sub = await _get_org_sub(db, company.id)

    # Count active members
    member_count_result = await db.execute(
        select(func.count()).select_from(CompanyMember).where(
            CompanyMember.company_id == company.id,
            CompanyMember.status == "active",
        )
    )
    member_count = member_count_result.scalar() or 0

    return {
        "company_id": str(company.id),
        "company_name": company.name,
        "plan_type": sub.plan_type if sub else None,
        "status": sub.status if sub else "none",
        "quantity": sub.quantity if sub else 0,
        "member_count": member_count,
        "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
    }


@router.post("/org/{slug}/checkout")
async def org_checkout(
    slug: str,
    plan_type: str = Query("monthly", regex="^(monthly|annual)$"),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe Checkout session for organization subscription."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    company = await _get_company_by_slug(db, slug)
    await _require_company_admin(db, company, current_resident.id)

    # Count active members for quantity
    member_count_result = await db.execute(
        select(func.count()).select_from(CompanyMember).where(
            CompanyMember.company_id == company.id,
            CompanyMember.status == "active",
        )
    )
    quantity = member_count_result.scalar() or 1

    price_id = (
        settings.stripe_price_org_monthly
        if plan_type == "monthly"
        else settings.stripe_price_org_annual
    )
    if not price_id:
        raise HTTPException(status_code=503, detail="Organization pricing not configured")

    sub = await _get_org_sub(db, company.id)

    # Get or create Stripe customer
    customer_id = None
    if sub and sub.stripe_customer_id:
        customer_id = sub.stripe_customer_id
    else:
        customer = stripe.Customer.create(
            metadata={
                "company_id": str(company.id),
                "company_slug": company.slug,
                "type": "organization",
            },
        )
        customer_id = customer.id
        if sub:
            sub.stripe_customer_id = customer_id
        else:
            sub = OrgSubscription(
                company_id=company.id,
                stripe_customer_id=customer_id,
                plan_type=plan_type,
                quantity=quantity,
            )
            db.add(sub)
        await db.flush()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": quantity}],
        metadata={
            "type": "org_subscription",
            "company_id": str(company.id),
            "plan_type": plan_type,
        },
        success_url=f"{settings.frontend_url}/org/{company.slug}/settings?checkout=success",
        cancel_url=f"{settings.frontend_url}/org/{company.slug}/settings?checkout=cancel",
    )

    return {"checkout_url": session.url}


@router.post("/org/{slug}/portal")
async def org_portal(
    slug: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe Customer Portal session for organization."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    company = await _get_company_by_slug(db, slug)
    await _require_company_admin(db, company, current_resident.id)

    sub = await _get_org_sub(db, company.id)
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No organization subscription found")

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=f"{settings.frontend_url}/org/{company.slug}/settings",
    )

    return {"portal_url": session.url}
