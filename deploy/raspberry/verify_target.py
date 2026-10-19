"""Read-only business canary using existing staging test credentials in Actions."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID, uuid4

COUNT_FIELDS = (
    "placed_orders", "active_orders", "cancelled_orders",
    "returned_refunded_orders", "fulfilled_orders", "paid_fulfilled_orders",
    "metric_declared_orders",
)
MONEY_FIELDS = (
    "placed_revenue", "active_revenue", "fulfilled_revenue",
    "paid_fulfilled_revenue", "spend", "metric_declared_revenue",
)


def verify_ratio(value, numerator, denominator, multiplier=1):
    denominator = Decimal(str(denominator))
    if denominator == 0:
        assert value is None, "CRM ratio requires a nonzero denominator"
        return
    assert value is not None, "CRM ratio missing for a nonzero denominator"
    actual = Decimal(str(value))
    assert actual.is_finite() and actual >= 0, "CRM ratio must be finite and nonnegative"
    expected = ((Decimal(str(numerator)) / denominator) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert actual == expected, "CRM ratio calculation"


def verify_crm_report(report, start, end):
    """Check public aggregate contracts without printing business amounts/names."""
    assert report.get("start_date") == start and report.get("end_date") == end, "CRM selected period"
    assert report.get("date_basis") == "order_created_at_utc", "CRM date basis"
    assert report.get("source") == "crm_manual_campaign_link", "CRM source"
    assert report.get("state_basis") == "current_state", "CRM lifecycle basis"
    campaigns = report.get("campaigns")
    assert isinstance(campaigns, list), "CRM campaign rows"
    rows = [report.get("totals"), report.get("unattributed"), *campaigns]
    for row in rows:
        assert isinstance(row, dict), "CRM aggregate shape"
        for key in COUNT_FIELDS:
            assert type(row.get(key)) is int and row[key] >= 0, "CRM nonnegative count"
        for key in MONEY_FIELDS:
            amount = Decimal(str(row.get(key)))
            assert amount.is_finite() and amount >= 0, "CRM nonnegative finite amount"
        assert row["placed_orders"] == (
            row["active_orders"] + row["cancelled_orders"] + row["returned_refunded_orders"]
        ), "CRM disjoint lifecycle counts"
        assert row["paid_fulfilled_orders"] <= row["fulfilled_orders"] <= row["active_orders"], "CRM fulfilled subsets"
        assert Decimal(str(row["paid_fulfilled_revenue"])) <= Decimal(str(row["fulfilled_revenue"])), "CRM paid revenue subset"
        verify_ratio(row.get("crm_period_revenue_to_spend"), row["fulfilled_revenue"], row["spend"])
        if row is not report.get("unattributed"):
            verify_ratio(row.get("cost_per_fulfilled_order"), row["spend"], row["fulfilled_orders"])
    totals, unknown = rows[:2]
    for key in COUNT_FIELDS:
        assert totals[key] == unknown[key] + sum(row[key] for row in campaigns), "CRM count reconciliation"
    for key in MONEY_FIELDS:
        assert Decimal(str(totals[key])) == (
            Decimal(str(unknown[key])) + sum((Decimal(str(row[key])) for row in campaigns), Decimal(0))
        ), "CRM amount reconciliation"
    assert report.get("unattributed_orders") == unknown["placed_orders"], "CRM unattributed coverage"
    assert report.get("attributed_orders") == sum(row["placed_orders"] for row in campaigns), "CRM linked coverage"
    assert totals["placed_orders"] == report["attributed_orders"] + report["unattributed_orders"], "CRM total coverage"
    verify_ratio(report.get("attribution_coverage_percent"), report["attributed_orders"], totals["placed_orders"], 100)
    assert Decimal(str(unknown["spend"])) == 0, "CRM unknown campaign has no mapped spend"
    assert unknown["metric_declared_orders"] == 0 and Decimal(str(unknown["metric_declared_revenue"])) == 0, "CRM unknown campaign has no declared metrics"
    assert unknown.get("crm_period_revenue_to_spend") is None, "CRM unknown campaign has no attributed ratio"
    assert unknown.get("cost_per_fulfilled_order") is None, "CRM unknown campaign has no attributed cost"
    assert len({row["campaign_id"] for row in campaigns}) == len(campaigns), "CRM unique campaign groups"


def verify_order_proposal(proposal, conversation_id):
    """Validate a read contract without printing snippets, catalog or identities."""
    assert proposal.get("conversation_id") == conversation_id, "Proposal conversation ownership"
    state = proposal.get("analysis_state")
    assert state in {"MISSING", "COMPLETED", "STALE", "FAILED", "MALFORMED", "PENDING"}, "Proposal analysis state"
    for key in ("catalog_truncated", "context_truncated"):
        assert type(proposal.get(key)) is bool, "Proposal bounded-context state"
    for key in ("analysis_id", "analysis_context_message_id"):
        if proposal.get(key) is not None:
            UUID(proposal[key])
    assert (proposal.get("analysis_id") is None) == (state == "MISSING"), "Proposal analysis identity"
    lines = proposal.get("lines")
    assert isinstance(lines, list) and len(lines) <= 40, "Proposal bounded lines"
    assert len({line["id"] for line in lines}) == len(lines), "Proposal unique line identities"
    for line in lines:
        assert type(line.get("quantity")) is int and 1 <= line["quantity"] <= 999, "Proposal quantity"
        source = line.get("source")
        assert source in {"ANALYSIS_CONTEXT", "INBOUND_SKU"}, "Proposal source distinction"
        assert type(line.get("requires_review")) is bool, "Proposal review state"
        assert type(line.get("candidates_truncated")) is bool, "Proposal bounded candidates"
        evidence = line.get("evidence")
        assert isinstance(evidence, list), "Proposal evidence shape"
        if source == "ANALYSIS_CONTEXT":
            assert state in {"COMPLETED", "STALE"}, "Proposal valid saved analysis"
            assert line["requires_review"] and not evidence, "Proposal analysis context is not a citation"
        else:
            assert evidence and not line["requires_review"], "Proposal actual inbound evidence"
            for item in evidence:
                UUID(item["message_id"])
                assert isinstance(item.get("snippet"), str), "Proposal evidence text"
        candidates = line.get("candidates")
        assert isinstance(candidates, list) and len(candidates) <= 10, "Proposal bounded candidate list"
        match = line.get("match_status")
        assert match in {"MATCHED", "AMBIGUOUS", "NOT_FOUND"}, "Proposal match state"
        if match == "MATCHED":
            assert len(candidates) == 1 and not line["candidates_truncated"], "Proposal unique match"
        elif match == "AMBIGUOUS":
            assert len(candidates) >= 2, "Proposal ambiguous alternatives"
        else:
            assert not candidates, "Proposal unresolved is not guessed"
        assert len({candidate["variant_id"] for candidate in candidates}) == len(candidates), "Proposal unique candidates"
        for candidate in candidates:
            UUID(candidate["variant_id"])
            UUID(candidate["product_id"])
            price = candidate.get("price")
            if price is not None:
                amount = Decimal(str(price))
                assert amount.is_finite() and amount >= 0, "Proposal finite catalog price"
            available = candidate.get("available_quantity")
            assert available is None or type(available) is int, "Proposal known or unknown inventory"
        if proposal["catalog_truncated"]:
            assert match == "NOT_FOUND" and not candidates, "Proposal never guesses from partial catalog"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise HTTPError(request.full_url, code, "Canary redirect rejected", headers, response)


def main():
    base = os.environ["TARGET_API_URL"].rstrip("/")
    url = urlsplit(base)
    assert url.scheme == "https" and url.hostname == os.environ["TARGET_EXPECTED_HOST"]
    assert url.path == "/api/v1" and not url.query and not url.fragment
    assert not url.username and not url.password

    opener = build_opener(NoRedirect())

    def request(path, *, body=None, token=None, workspace=None):
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if workspace:
            headers["X-Workspace-ID"] = workspace
        payload = None
        if body is not None:
            assert path in {"/auth/login", "/auth/refresh"}, "Canary writes limited to authentication"
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        try:
            with opener.open(Request(base + path, data=payload, headers=headers), timeout=45) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, {}

    code, _ = request("/auth/me")
    assert code == 401, "Anonymous route protection"
    code, pair = request("/auth/login", body={
        "email": os.environ["STAGING_OWNER_EMAIL"],
        "password": os.environ["STAGING_OWNER_PASSWORD"],
    })
    assert code == 200 and pair.get("access_token"), "Staging canary login"
    code, renewed = request("/auth/refresh", body={"refresh_token": pair["refresh_token"]})
    assert code == 200 and renewed.get("access_token"), "Canary token refresh"
    token = renewed["access_token"]
    code, user = request("/auth/me", token=token)
    assert code == 200 and user.get("is_active"), "Canary current user"
    memberships = user.get("memberships", [])
    assert memberships, "Existing canary memberships"
    evidence = {
        "target_api": base, "anonymous_protection": True,
        "login": True, "refresh": True, "membership_count": len(memberships),
        "workspaces_checked": 0, "conversation_count": 0, "sample_message_count": 0,
        "crm_reports_checked": 0, "order_proposals_checked": 0,
    }
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=29)
    query = urlencode({"start_date": start.isoformat(), "end_date": end.isoformat()})
    sample_conversation = None
    for membership in memberships:
        workspace = str(membership["workspace_id"])
        code, _ = request("/onboarding/status", token=token, workspace=workspace)
        assert code == 200, "Existing workspace onboarding read"
        code, report = request("/advertising/crm-attribution?" + query, token=token, workspace=workspace)
        assert code == 200 and isinstance(report, dict), "CRM report authenticated read"
        verify_crm_report(report, start.isoformat(), end.isoformat())
        evidence["crm_reports_checked"] += 1
        code, conversations = request("/direct/conversations", token=token, workspace=workspace)
        assert code == 200 and isinstance(conversations, list), "Existing Direct read"
        evidence["workspaces_checked"] += 1
        evidence["conversation_count"] += len(conversations)
        if conversations:
            conversation_id = str(conversations[0]["id"])
            proposal_path = "/direct/conversations/" + conversation_id + "/order-proposal"
            code, proposal = request(proposal_path, token=token, workspace=workspace)
            assert code == 200 and isinstance(proposal, dict), "Order proposal authenticated read"
            verify_order_proposal(proposal, conversation_id)
            evidence["order_proposals_checked"] += 1
            sample_conversation = sample_conversation or (workspace, conversation_id)
            code, messages = request("/direct/conversations/" + conversations[0]["id"] + "/messages",
                                     token=token, workspace=workspace)
            assert code == 200 and isinstance(messages, list), "Existing message history read"
            evidence["sample_message_count"] += len(messages)
    workspace = str(memberships[0]["workspace_id"])
    code, _ = request("/direct/conversations/" + str(uuid4()) + "/order-proposal", token=token, workspace=workspace)
    assert code == 404, "Unknown proposal conversation must not exist"
    evidence["unknown_proposal_rejected"] = True
    if sample_conversation and len(memberships) > 1:
        source_workspace, conversation_id = sample_conversation
        other_workspace = next(str(item["workspace_id"]) for item in memberships if str(item["workspace_id"]) != source_workspace)
        code, _ = request("/direct/conversations/" + conversation_id + "/order-proposal", token=token, workspace=other_workspace)
        assert code == 404, "Foreign conversation proposal must reject object access"
        evidence["foreign_proposal_rejected"] = True
    code, _ = request("/direct/conversations", token=token, workspace=str(uuid4()))
    assert code == 403, "Unknown workspace must reject authenticated access"
    evidence["foreign_workspace_rejected"] = True
    print(json.dumps(evidence))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit("Target canary failed: " + type(error).__name__ + (
            ": " + str(error) if isinstance(error, AssertionError) else ""))
