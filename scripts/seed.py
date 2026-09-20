#!/usr/bin/env python3
"""
Seed script — populates the ordering platform with sample data via the Core API.

Usage:
    python scripts/seed.py [--base-url http://localhost:8000]

Requirements:
    - All containers must be running: docker compose up -d
    - The script uses only the stdlib (urllib) — no extra deps needed.

What it creates:
    - 5 Customers
    - 8 Products (different categories/prices)
    - 6 Orders (via the async flow: Order Service → RabbitMQ → Order Worker)
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

CUSTOMERS = [
    {
        "name": "Alice Souza",
        "email": "alice.souza@example.com",
        "phone": "+55 11 91234-5678",
    },
    {
        "name": "Bruno Lima",
        "email": "bruno.lima@example.com",
        "phone": "+55 21 99876-5432",
    },
    {
        "name": "Carla Mendes",
        "email": "carla.mendes@example.com",
        "phone": "+55 31 98765-4321",
    },
    {
        "name": "Daniel Costa",
        "email": "daniel.costa@example.com",
        "phone": "+55 41 97654-3210",
    },
    {
        "name": "Eva Rocha",
        "email": "eva.rocha@example.com",
        "phone": "+55 51 96543-2109",
    },
]

PRODUCTS = [
    {
        "name": "Notebook Pro 15",
        "description": (
            "Laptop profissional com processador de última geração, 16GB RAM e SSD 512GB."
        ),
        "price": "4599.90",
        "stock": 25,
    },
    {
        "name": "Mouse Sem Fio Ergonômico",
        "description": "Mouse óptico sem fio com design ergonômico e autonomia de 12 meses.",
        "price": "129.90",
        "stock": 150,
    },
    {
        "name": "Teclado Mecânico RGB",
        "description": "Teclado mecânico com switches blue, retroiluminação RGB e layout ABNT2.",
        "price": "349.90",
        "stock": 80,
    },
    {
        "name": 'Monitor Ultrawide 34"',
        "description": "Monitor curvo ultrawide 34 polegadas, resolução 3440x1440, 144Hz.",
        "price": "2899.00",
        "stock": 12,
    },
    {
        "name": "Headset Gamer 7.1",
        "description": (
            "Headset com som surround 7.1 virtual, microfone removível e almofadas memory foam."
        ),
        "price": "299.90",
        "stock": 60,
    },
    {
        "name": "SSD NVMe 1TB",
        "description": "SSD com interface NVMe PCIe 4.0, leitura até 7000 MB/s.",
        "price": "549.90",
        "stock": 45,
    },
    {
        "name": "Webcam Full HD 1080p",
        "description": (
            "Webcam com resolução 1080p, autofoco e microfone embutido com cancelamento de ruído."
        ),
        "price": "199.90",
        "stock": 90,
    },
    {
        "name": "Hub USB-C 7 em 1",
        "description": (
            "Concentrador USB-C com HDMI 4K, USB 3.0 x3, SD, microSD e carregamento PD 100W."
        ),
        "price": "179.90",
        "stock": 110,
    },
]

# Orders reference products by index (into the PRODUCTS list above) and qty.
# They will be assigned to customers round-robin after seed.
ORDER_TEMPLATES = [
    # Order 1: Alice — notebook + mouse
    {"items": [{"product_index": 0, "quantity": 1}, {"product_index": 1, "quantity": 2}]},
    # Order 2: Bruno — teclado + headset
    {"items": [{"product_index": 2, "quantity": 1}, {"product_index": 4, "quantity": 1}]},
    # Order 3: Carla — monitor
    {"items": [{"product_index": 3, "quantity": 1}]},
    # Order 4: Daniel — SSD + hub
    {"items": [{"product_index": 5, "quantity": 2}, {"product_index": 7, "quantity": 1}]},
    # Order 5: Eva — webcam + mouse + hub
    {
        "items": [
            {"product_index": 6, "quantity": 1},
            {"product_index": 1, "quantity": 1},
            {"product_index": 7, "quantity": 2},
        ]
    },
    # Order 6: Alice — teclado + SSD (segundo pedido do mesmo cliente)
    {"items": [{"product_index": 2, "quantity": 1}, {"product_index": 5, "quantity": 1}]},
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _request(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode() if body else None
    req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw}
        return exc.code, payload


def post(
    url: str, body: dict[str, Any], headers: dict[str, str] | None = None
) -> tuple[int, dict[str, Any]]:
    return _request("POST", url, body, headers)


def get(url: str) -> tuple[int, dict[str, Any]]:
    return _request("GET", url)


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


def check_health(base: str) -> bool:
    print("⏳ Verificando disponibilidade da Core API...", end=" ", flush=True)
    for _attempt in range(10):
        try:
            status, _ = get(f"{base}/health")
            if status == 200:
                print("✅ online")
                return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(2)
    print(
        "\n❌ Core API não respondeu. "
        "Verifique se os containers estão rodando: docker compose up -d"
    )
    return False


def seed_customers(base: str) -> list[dict[str, Any]]:
    print("\n📋 Criando clientes...")
    created = []
    for c in CUSTOMERS:
        status, body = post(f"{base}{API_PREFIX}/customers", c)
        if status == 201:
            cid = body.get("id", "?")
            print(f"  ✅ {c['name']} → id={cid}")
            created.append(body)
        elif status == 409:
            print(f"  ⚠️  {c['name']} já existe (email duplicado) — buscando...")
            s2, b2 = get(f"{base}{API_PREFIX}/customers/name/{c['name'].replace(' ', '%20')}")
            if s2 == 200:
                created.append(b2)
                print(f"     → id={b2.get('id', '?')}")
            else:
                print(f"     → Não foi possível recuperar o cliente existente (status {s2})")
        else:
            print(f"  ❌ {c['name']} falhou: status={status} body={body}")
    return created


def seed_products(base: str) -> list[dict[str, Any]]:
    print("\n📦 Criando produtos...")
    created = []
    for p in PRODUCTS:
        status, body = post(f"{base}{API_PREFIX}/products", p)
        if status == 201:
            pid = body.get("id", "?")
            print(f"  ✅ {p['name']} (R$ {p['price']}, estoque: {p['stock']}) → id={pid}")
            created.append(body)
        elif status == 409:
            print(f"  ⚠️  {p['name']} já existe — buscando...")
            s2, b2 = get(f"{base}{API_PREFIX}/products/name/{p['name'].replace(' ', '%20')}")
            if s2 == 200:
                created.append(b2)
                print(f"     → id={b2.get('id', '?')}")
            else:
                print(f"     → Não foi possível recuperar o produto existente (status {s2})")
        else:
            print(f"  ❌ {p['name']} falhou: status={status} body={body}")
    return created


def seed_orders(
    base: str,
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
) -> None:
    print("\n🛒 Criando pedidos (fluxo assíncrono via RabbitMQ)...")

    if not customers:
        print("  ⚠️  Nenhum cliente disponível, pulando pedidos.")
        return
    if not products:
        print("  ⚠️  Nenhum produto disponível, pulando pedidos.")
        return

    for i, template in enumerate(ORDER_TEMPLATES):
        customer = customers[i % len(customers)]
        customer_id = customer["id"]
        customer_name = customer["name"]

        items = []
        for item_def in template["items"]:
            idx = item_def["product_index"]
            if idx >= len(products):
                print(f"  ⚠️  Produto índice {idx} não disponível, pulando item.")
                continue
            items.append(
                {
                    "product_id": products[idx]["id"],
                    "quantity": item_def["quantity"],
                }
            )

        if not items:
            print(f"  ⚠️  Pedido {i + 1} sem itens válidos, pulando.")
            continue

        idempotency_key = str(uuid.uuid4())
        payload = {"customer_id": customer_id, "items": items}
        headers = {"Idempotency-Key": idempotency_key}

        status, body = post(f"{base}{API_PREFIX}/orders", payload, headers=headers)
        if status == 202:
            ext_id = body.get("external_id", "?")
            print(
                f"  ✅ Pedido {i + 1} ({customer_name}) "
                f"→ external_id={ext_id}, status={body.get('status')}"
            )
        else:
            print(f"  ❌ Pedido {i + 1} ({customer_name}) falhou: status={status} body={body}")

    print("\n⏳ Aguardando 5s para o Order Worker processar os pedidos...")
    time.sleep(5)


def print_summary(base: str) -> None:
    print("\n📊 Resumo final:")
    for resource, label in [
        ("customers", "Clientes"),
        ("products", "Produtos"),
        ("orders", "Pedidos"),
    ]:
        s, b = get(f"{base}{API_PREFIX}/{resource}/count")
        count = b.get("count", "?") if s == 200 else f"erro {s}"
        print(f"  {label}: {count}")

    print("\n🔍 Pedidos criados:")
    s, body = get(f"{base}{API_PREFIX}/orders")
    if s == 200:
        orders = body if isinstance(body, list) else body.get("orders", [])
        for order in orders:
            ext_id = order.get("external_id", "?")
            status = order.get("status", "?")
            total = order.get("total_amount", "?")
            cid = order.get("customer_id", "?")
            print(f"  • external_id={ext_id}  status={status}  total=R${total}  customer_id={cid}")
    else:
        print(f"  Não foi possível listar pedidos (status {s})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed da plataforma de pedidos via Core API.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="URL base da Core API (padrão: http://localhost:8000)",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    print("=" * 60)
    print("  Ordering Platform — Seed de Dados")
    print(f"  Core API: {base}")
    print("=" * 60)

    if not check_health(base):
        sys.exit(1)

    customers = seed_customers(base)
    products = seed_products(base)
    seed_orders(base, customers, products)
    print_summary(base)

    print("\n✅ Seed concluído! A plataforma está pronta para testes.\n")
    print("Dicas:")
    print(f"  • Swagger UI:  {base}/docs")
    print(f"  • Listar clientes: GET {base}{API_PREFIX}/customers")
    print(f"  • Listar produtos:  GET {base}{API_PREFIX}/products")
    print(f"  • Listar pedidos:   GET {base}{API_PREFIX}/orders")
    print()


if __name__ == "__main__":
    main()
