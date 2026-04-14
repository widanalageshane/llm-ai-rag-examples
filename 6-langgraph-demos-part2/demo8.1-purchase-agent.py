"""
Demo 8 – Homework version
Tasks covered:
1. Dynamic quantity parsing + tool-based unit price lookup
2. Conditional approval only if total > €10,000
3. Proper rejection path
4. Live data from DummyJSON laptops category
"""

import sys
import os
import re
import time
import json
import sqlite3
import logging
from typing import TypedDict

import requests
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ─── State ─────────────────────────────────────────────────────────────────────

class ProcurementState(TypedDict, total=False):
    request: str
    quantity: int
    vendors: list[dict]
    quotes: list[dict]
    best_quote: dict
    approval_status: str
    rejection_reason: str
    po_number: str
    notification: str


# ─── LLMs ──────────────────────────────────────────────────────────────────────

pricing_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0,
)

writer_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.2,
)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def extract_quantity(request_text: str) -> int:
    """Extract first integer from request text, default to 1."""
    match = re.search(r"(\d+)", request_text)
    return int(match.group(1)) if match else 1


def infer_delivery_days(shipping_info: str) -> int:
    """Best-effort conversion of shipping text into delivery days."""
    if not shipping_info:
        return 14

    text = shipping_info.lower()

    day_match = re.search(r"(\d+)\s*day", text)
    if day_match:
        return int(day_match.group(1))

    week_match = re.search(r"(\d+)\s*week", text)
    if week_match:
        return int(week_match.group(1)) * 7

    month_match = re.search(r"(\d+)\s*month", text)
    if month_match:
        return int(month_match.group(1)) * 30

    if "tomorrow" in text:
        return 1
    if "today" in text:
        return 0

    return 14


def available_within_two_weeks(product: dict) -> bool:
    """
    DummyJSON doesn't provide a strict normalized lead-time field, so this uses
    shippingInformation first and falls back to stock/availability.
    """
    shipping = product.get("shippingInformation", "")
    if shipping:
        days = infer_delivery_days(shipping)
        return days <= 14 and product.get("stock", 0) > 0

    availability = str(product.get("availabilityStatus", "")).lower()
    stock = int(product.get("stock", 0))
    return stock > 0 and availability in {"in stock", "low stock", ""}


def matches_vendor(product: dict, vendor: str) -> bool:
    vendor_lower = vendor.lower()
    brand = str(product.get("brand", "")).lower()
    title = str(product.get("title", "")).lower()
    return vendor_lower in brand or vendor_lower in title


def fetch_products_by_category(category: str) -> list[dict]:
    url = f"https://dummyjson.com/products/category/{category}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data.get("products", [])


def choose_best_product(products: list[dict], vendor: str) -> tuple[dict | None, bool]:
    """
    Returns:
      (product, fallback_used)

    1) Try cheapest product matching the vendor and available within 2 weeks
    2) Fall back to cheapest available product in the category
    3) Fall back to None if nothing usable exists
    """
    vendor_specific = [
        p for p in products
        if matches_vendor(p, vendor) and available_within_two_weeks(p)
    ]

    if vendor_specific:
        best = min(vendor_specific, key=lambda p: float(p.get("price", float("inf"))))
        return best, False

    all_available = [p for p in products if available_within_two_weeks(p)]
    if all_available:
        logging.warning(
            "No %s-specific laptop found within 2 weeks. Falling back to cheapest available laptop.",
            vendor,
        )
        best = min(all_available, key=lambda p: float(p.get("price", float("inf"))))
        return best, True

    return None, True


# ─── Tool ──────────────────────────────────────────────────────────────────────

@tool
def get_unit_price(vendor: str) -> dict:
    """Look up the best current laptop unit price for the given vendor."""
    try:
        products = fetch_products_by_category("laptops")
        product, fallback_used = choose_best_product(products, vendor)

        if not product:
            logging.warning(
                "No matching laptop found from API. Using sensible fallback for vendor %s.",
                vendor,
            )
            product = {
                "title": f"Fallback Laptop for {vendor}",
                "brand": vendor,
                "price": 999.0,
                "stock": 1,
                "shippingInformation": "Ships in 2 weeks",
                "availabilityStatus": "Fallback",
            }
            fallback_used = True

        unit_price = float(product.get("price", 999.0))
        shipping_info = product.get("shippingInformation", "Ships in 2 weeks")
        delivery_days = infer_delivery_days(shipping_info)

        return {
            "vendor": vendor,
            "product_title": product.get("title", f"{vendor} Laptop"),
            "brand": product.get("brand", vendor),
            "unit_price": unit_price,
            "delivery_days": delivery_days,
            "availability": product.get("availabilityStatus", "Unknown"),
            "shipping_information": shipping_info,
            "fallback_used": fallback_used,
        }

    except Exception as e:
        logging.warning("API lookup failed for %s. Using fallback. Error: %s", vendor, e)
        return {
            "vendor": vendor,
            "product_title": f"Fallback Laptop for {vendor}",
            "brand": vendor,
            "unit_price": 999.0,
            "delivery_days": 14,
            "availability": "Fallback",
            "shipping_information": "Ships in 2 weeks",
            "fallback_used": True,
        }


# ─── Nodes ─────────────────────────────────────────────────────────────────────

def lookup_vendors(state: ProcurementState) -> dict:
    """Step 1: Parse quantity and look up approved vendors."""
    request_text = state["request"]
    quantity = extract_quantity(request_text)

    print("\n[Step 1] Looking up approved vendors...")
    print(f"   Parsed quantity from request: {quantity}")
    time.sleep(0.5)

    vendors = [
        {"name": "Dell", "id": "V-001", "category": "laptops", "rating": 4.5},
        {"name": "Lenovo", "id": "V-002", "category": "laptops", "rating": 4.3},
        {"name": "HP", "id": "V-003", "category": "laptops", "rating": 4.1},
    ]

    for v in vendors:
        print(f"   Found vendor: {v['name']} (rating {v['rating']})")

    return {
        "quantity": quantity,
        "vendors": vendors,
    }


def fetch_pricing(state: ProcurementState) -> dict:
    """
    Step 2: Ask the LLM to call the pricing tool once per vendor,
    then compute totals from returned unit prices.
    """
    print("\n[Step 2] Fetching live pricing via tool calls...")
    quantity = state["quantity"]
    vendor_names = [v["name"] for v in state["vendors"]]

    model_with_tools = pricing_llm.bind_tools([get_unit_price])

    system_msg = SystemMessage(
        content=(
            "You are a procurement pricing assistant. "
            "You must call the get_unit_price tool exactly once for each vendor provided. "
            "Do not answer with prose."
        )
    )

    human_msg = HumanMessage(
        content=(
            f"Purchase request: {state['request']}\n"
            f"Quantity: {quantity}\n"
            f"Vendors: {', '.join(vendor_names)}\n"
            "Call get_unit_price exactly once per vendor."
        )
    )

    ai_msg = model_with_tools.invoke([system_msg, human_msg])
    tool_calls = ai_msg.tool_calls or []

    quotes = []
    called_vendors = set()

    # Execute model-requested tool calls
    for tool_call in tool_calls:
        if tool_call.get("name") != "get_unit_price":
            continue

        vendor = tool_call.get("args", {}).get("vendor")
        if vendor not in vendor_names or vendor in called_vendors:
            continue

        tool_result = get_unit_price.invoke({"vendor": vendor})
        total = round(tool_result["unit_price"] * quantity, 2)

        quote = {
            "vendor": vendor,
            "product_title": tool_result["product_title"],
            "brand": tool_result["brand"],
            "unit_price": tool_result["unit_price"],
            "total": total,
            "delivery_days": tool_result["delivery_days"],
            "availability": tool_result["availability"],
            "shipping_information": tool_result["shipping_information"],
            "fallback_used": tool_result["fallback_used"],
        }
        quotes.append(quote)
        called_vendors.add(vendor)

    # Safety fallback if the LLM misses any vendor
    for vendor in vendor_names:
        if vendor in called_vendors:
            continue

        logging.warning(
            "LLM did not call the tool for vendor %s. Running fallback tool call directly.",
            vendor,
        )

        tool_result = get_unit_price.invoke({"vendor": vendor})
        total = round(tool_result["unit_price"] * quantity, 2)

        quote = {
            "vendor": vendor,
            "product_title": tool_result["product_title"],
            "brand": tool_result["brand"],
            "unit_price": tool_result["unit_price"],
            "total": total,
            "delivery_days": tool_result["delivery_days"],
            "availability": tool_result["availability"],
            "shipping_information": tool_result["shipping_information"],
            "fallback_used": tool_result["fallback_used"],
        }
        quotes.append(quote)

    for q in quotes:
        print(
            f"   {q['vendor']}: {q['product_title']} | "
            f"€{q['unit_price']:.2f}/unit x {quantity} = €{q['total']:,.2f} "
            f"({q['delivery_days']} day delivery)"
        )

    return {"quotes": quotes}


def compare_quotes(state: ProcurementState) -> dict:
    """Step 3: Compare quotes and choose the cheapest total."""
    print("\n[Step 3] Comparing quotes...")
    time.sleep(0.3)

    best = min(state["quotes"], key=lambda q: q["total"])
    most_expensive = max(state["quotes"], key=lambda q: q["total"])
    savings = most_expensive["total"] - best["total"]

    print(f"   Best quote: {best['vendor']} - {best['product_title']}")
    print(f"   Total: €{best['total']:,.2f}")
    print(f"   Savings vs highest quote: €{savings:,.2f}")

    return {"best_quote": best}


def request_approval(state: ProcurementState) -> dict:
    """Step 4: Pause execution and wait for manager approval."""
    best = state["best_quote"]
    quantity = state["quantity"]

    print("\n[Step 4] Order exceeds €10,000 — manager approval required!")
    print("   Sending approval request to manager...")

    amount_str = f"€{best['total']:,.2f}"
    delivery_str = f"{best['delivery_days']} business days"
    item_line = f"{quantity} x {best['product_title']}"

    print("   ┌────────────────────────────────────────────────────────────┐")
    print("   │  APPROVAL NEEDED                                           │")
    print(f"   │  Vendor:   {best['vendor']:<46}│")
    print(f"   │  Amount:   {amount_str:<46}│")
    print(f"   │  Item:     {item_line[:46]:<46}│")
    print(f"   │  Delivery: {delivery_str:<46}│")
    print("   └────────────────────────────────────────────────────────────┘")

    decision = interrupt({
        "message": (
            f"Approve purchase of {quantity} x {best['product_title']} "
            f"from {best['vendor']} for €{best['total']:,.2f}?"
        ),
        "vendor": best["vendor"],
        "product_title": best["product_title"],
        "amount": best["total"],
        "quantity": quantity,
    })

    decision_str = str(decision).strip()
    print(f"\n[Step 4] Manager responded: {decision_str}")

    result = {"approval_status": decision_str}
    if "reject" in decision_str.lower():
        result["rejection_reason"] = decision_str

    return result


def submit_purchase_order(state: ProcurementState) -> dict:
    """Step 5: Create a PO only when approved."""
    print("\n[Step 5] Submitting purchase order to ERP system...")
    time.sleep(0.8)

    po_number = f"PO-2026-{int(time.time()) % 100000:05d}"
    best = state["best_quote"]

    print(f"   Purchase order created: {po_number}")
    print(f"   Vendor: {best['vendor']}")
    print(f"   Product: {best['product_title']}")
    print(f"   Amount: €{best['total']:,.2f}")

    return {"po_number": po_number}


def notify_employee(state: ProcurementState) -> dict:
    """Step 6: Notify the requester cleanly for both approval and rejection."""
    print("\n[Step 6] Notifying employee...")

    quantity = state["quantity"]
    best = state["best_quote"]

    if state.get("approval_status") and "reject" in state["approval_status"].lower():
        reason = state.get("rejection_reason", state["approval_status"])
        prompt = (
            f"Write a brief, professional notification in 2-3 sentences to the employee. "
            f"The request for {quantity} laptops was rejected by the manager. "
            f"Vendor considered: {best['vendor']}. "
            f"Reason: {reason}. "
            f"Be empathetic, clear, and concise."
        )
    else:
        prompt = (
            f"Write a brief, professional notification in 2-3 sentences to the employee. "
            f"The purchase request has been approved and processed. "
            f"Details: {quantity} x {best['product_title']} from {best['vendor']}, "
            f"total €{best['total']:,.2f}, PO number {state.get('po_number', 'N/A')}, "
            f"delivery in {best['delivery_days']} business days. "
            f"Be concise and professional."
        )

    response = writer_llm.invoke(prompt)
    notification = response.content

    print("   Employee notification sent:")
    print(f'   "{notification}"')

    return {"notification": notification}


# ─── Routing functions ─────────────────────────────────────────────────────────

def route_after_compare(state: ProcurementState) -> str:
    """Task 2: Approval only when total exceeds €10,000."""
    if state["best_quote"]["total"] > 10_000:
        return "request_approval"
    return "submit_purchase_order"


def route_after_approval(state: ProcurementState) -> str:
    """Task 3: Approved continues, rejected skips PO creation."""
    approval = state.get("approval_status", "").lower()

    if "approve" in approval and "reject" not in approval:
        return "submit_purchase_order"

    return "notify_employee"


# ─── Build graph ───────────────────────────────────────────────────────────────

builder = StateGraph(ProcurementState)

builder.add_node("lookup_vendors", lookup_vendors)
builder.add_node("fetch_pricing", fetch_pricing)
builder.add_node("compare_quotes", compare_quotes)
builder.add_node("request_approval", request_approval)
builder.add_node("submit_purchase_order", submit_purchase_order)
builder.add_node("notify_employee", notify_employee)

builder.add_edge(START, "lookup_vendors")
builder.add_edge("lookup_vendors", "fetch_pricing")
builder.add_edge("fetch_pricing", "compare_quotes")

builder.add_conditional_edges(
    "compare_quotes",
    route_after_compare,
    {
        "request_approval": "request_approval",
        "submit_purchase_order": "submit_purchase_order",
    },
)

builder.add_conditional_edges(
    "request_approval",
    route_after_approval,
    {
        "submit_purchase_order": "submit_purchase_order",
        "notify_employee": "notify_employee",
    },
)

builder.add_edge("submit_purchase_order", "notify_employee")
builder.add_edge("notify_employee", END)


# ─── Persistence ───────────────────────────────────────────────────────────────

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "procurement_checkpoints.db",
)
THREAD_ID = "procurement-thread-1"
config = {"configurable": {"thread_id": THREAD_ID}}


# ─── CLI helpers ───────────────────────────────────────────────────────────────

def get_request_from_cli() -> str:
    args = [a for a in sys.argv[1:] if a != "--resume"]
    if args:
        return " ".join(args)
    return "Order 50 laptops for the new engineering team"


def get_resume_value_from_cli() -> str:
    if "--resume" not in sys.argv:
        return ""

    idx = sys.argv.index("--resume")
    if idx + 1 < len(sys.argv):
        return sys.argv[idx + 1]

    return "Approved — go ahead with the purchase."


def run_first_invocation(graph) -> None:
    request_text = get_request_from_cli()

    print("=" * 60)
    print("  FIRST INVOCATION — Employee submits purchase request")
    print("=" * 60)
    print(f'\nEmployee request: "{request_text}"')

    result = graph.invoke({"request": request_text}, config)

    if result.get("po_number"):
        print("\n" + "=" * 60)
        print("PROCUREMENT COMPLETE — no manager approval was needed")
        print("=" * 60)
        print(f"\n  PO Number: {result.get('po_number', 'N/A')}")
        print(f"  Vendor:    {result.get('best_quote', {}).get('vendor', 'N/A')}")
        print(f"  Total:     €{result.get('best_quote', {}).get('total', 0):,.2f}")
        return

    print("\n" + "=" * 60)
    print("AGENT SUSPENDED — waiting for manager approval")
    print("=" * 60)
    print("\n  The agent process can now exit completely.")
    print("  All state is frozen in SQLite.")
    print(f"  Checkpoint DB: {DB_PATH}")
    print(f"  Thread ID: {THREAD_ID}")
    print("\n  To resume with approval:")
    print(f'    python {os.path.basename(__file__)} --resume "Approved — go ahead with the purchase."')
    print("\n  To resume with rejection:")
    print(f'    python {os.path.basename(__file__)} --resume "Rejected — over budget"')
    print()


def run_second_invocation(graph) -> None:
    print("=" * 60)
    print("  SECOND INVOCATION — Resume from checkpoint")
    print("=" * 60)

    saved_state = graph.get_state(config)
    if not saved_state or not saved_state.values:
        print("\nNo saved state found. Run the script without --resume first.")
        return

    print("\nLoading state from checkpoint...")
    print(f"  ✓ Request: {saved_state.values.get('request', 'N/A')}")
    print(f"  ✓ Quantity: {saved_state.values.get('quantity', 'N/A')}")
    print(f"  ✓ Vendors found: {len(saved_state.values.get('vendors', []))}")
    print(f"  ✓ Quotes received: {len(saved_state.values.get('quotes', []))}")

    best = saved_state.values.get("best_quote", {})
    print(f"  ✓ Best quote: {best.get('vendor', 'N/A')} - {best.get('product_title', 'N/A')}")
    print(f"  ✓ Total: €{best.get('total', 0):,.2f}")
    print("\n  Steps 1-3 are NOT re-executed.\n")

    resume_value = get_resume_value_from_cli()
    print(f"Manager response: {resume_value}")
    time.sleep(0.6)

    result = graph.invoke(Command(resume=resume_value), config)

    print("\n" + "=" * 60)
    print("PROCUREMENT FINISHED")
    print("=" * 60)
    print(f"\n  Approval:  {result.get('approval_status', 'N/A')}")
    print(f"  Vendor:    {result.get('best_quote', {}).get('vendor', 'N/A')}")
    print(f"  Product:   {result.get('best_quote', {}).get('product_title', 'N/A')}")
    print(f"  Total:     €{result.get('best_quote', {}).get('total', 0):,.2f}")
    print(f"  PO Number: {result.get('po_number', 'N/A')}")
    print()


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    resume_mode = "--resume" in sys.argv

    # Clean DB only for a fresh non-resume run
    if not resume_mode and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("(Cleaned up old checkpoint DB)")

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = builder.compile(checkpointer=checkpointer)

    try:
        if resume_mode:
            run_second_invocation(graph)
        else:
            run_first_invocation(graph)
    finally:
        conn.close()