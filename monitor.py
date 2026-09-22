"""
Monitor de Compra Ágil para Infero SpA
----------------------------------------
Revisa la API pública de Compra Ágil (Mercado Público) buscando procesos
publicados recientemente cuyo título o descripción contenga alguna de las
palabras clave definidas en keywords.txt, y envía una notificación a un
canal de Discord mediante un webhook.

Diseñado para correr periódicamente (por ejemplo, con GitHub Actions cada
15-30 minutos) sin costo. Guarda en state.json los códigos ya notificados
para no repetir avisos.
"""

import json
import os
import sys
import time
import unicodedata
from pathlib import Path

import requests

BASE_URL = "https://api2.mercadopublico.cl"
STATE_FILE = Path("state.json")
KEYWORDS_FILE = Path("keywords.txt")

# Ventana de tiempo hacia atrás que se revisa en cada corrida (en milisegundos).
# 70 minutos por defecto: el bot corre cada 1 hora, y este margen extra evita
# perder publicaciones aunque una corrida se atrase o falle una vez.
TTL_CAMBIO_MS = int(os.environ.get("TTL_CAMBIO_MS", 70 * 60 * 1000))

# Estados que nos interesan monitorear (recién publicadas)
ESTADOS = os.environ.get("ESTADOS", "publicada")

TICKET = os.environ.get("MP_TICKET")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def normalizar(texto: str) -> str:
    """Quita tildes y pasa a minúsculas para comparar sin problemas de acentos."""
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def cargar_keywords() -> list[str]:
    if not KEYWORDS_FILE.exists():
        print(f"⚠️  No existe {KEYWORDS_FILE}. Crea el archivo con una palabra clave por línea.")
        return []
    keywords = []
    for linea in KEYWORDS_FILE.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            keywords.append(normalizar(linea))
    return keywords


def cargar_estado() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"notificados": []}
    return {"notificados": []}


def guardar_estado(estado: dict) -> None:
    # Evita que el archivo crezca para siempre: se queda con los últimos 3000 códigos.
    estado["notificados"] = estado["notificados"][-3000:]
    STATE_FILE.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def obtener_compras_agiles() -> list[dict]:
    if not TICKET:
        print("❌ Falta la variable de entorno MP_TICKET con tu ticket de acceso a la API.")
        sys.exit(1)

    items = []
    pagina = 1
    while True:
        params = {
            "ttl_cambio_ms": TTL_CAMBIO_MS,
            "estado": ESTADOS,
            "tamano_pagina": 50,
            "numero_pagina": pagina,
            "ordenar_por": "FechaPublicacion",
        }
        resp = requests.get(
            f"{BASE_URL}/v2/compra-agil",
            headers={"ticket": TICKET},
            params=params,
            timeout=30,
        )

        if resp.status_code == 429:
            print("⏳ Se alcanzó la cuota diaria de la API (429). Se reintentará en la próxima corrida.")
            break

        resp.raise_for_status()
        data = resp.json()

        if data.get("success") != "OK":
            print("❌ Error de la API:", data.get("errors"))
            break

        payload = data.get("payload") or {}
        pagina_items = payload.get("items", [])
        items.extend(pagina_items)

        paginacion = payload.get("paginacion", {})
        total_paginas = paginacion.get("total_paginas", 1)
        if pagina >= total_paginas:
            break
        pagina += 1
        time.sleep(0.3)  # pequeño respiro entre páginas

    return items


def coincide_con_keywords(item: dict, keywords: list[str]) -> str | None:
    """Devuelve la palabra clave que hizo match, o None si no hay coincidencia."""
    texto = normalizar(f"{item.get('nombre', '')} ")
    # El listado no siempre trae descripción completa; si existe, se incluye.
    texto += normalizar(str(item.get("descripcion", "")))

    for kw in keywords:
        if kw in texto:
            return kw
    return None


def enviar_discord(item: dict, keyword: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        print("❌ Falta la variable de entorno DISCORD_WEBHOOK_URL.")
        return

    codigo = item.get("codigo", "N/A")
    nombre = item.get("nombre", "Sin título")
    institucion = item.get("institucion", {}).get("organismo_comprador", "N/A")
    region = item.get("institucion", {}).get("nombre_region", "N/A")
    monto = item.get("montos", {}).get("monto_disponible_clp")
    monto_txt = f"${monto:,.0f} CLP".replace(",", ".") if isinstance(monto, (int, float)) else "No informado"
    fecha_cierre = item.get("fechas", {}).get("fecha_cierre", "N/A")
    url_ficha = f"https://www.mercadopublico.cl/Home#!/compra-agil/{codigo}"

    embed = {
        "title": nombre[:250],
        "description": f"🔑 Coincidencia con: **{keyword}**",
        "url": url_ficha,
        "color": 3447003,
        "fields": [
            {"name": "Código", "value": codigo, "inline": True},
            {"name": "Institución", "value": institucion, "inline": True},
            {"name": "Región", "value": str(region), "inline": True},
            {"name": "Monto disponible", "value": monto_txt, "inline": True},
            {"name": "Cierra", "value": str(fecha_cierre), "inline": True},
        ],
    }

    payload = {
        "content": "📢 **Nueva Compra Ágil que te puede interesar**",
        "embeds": [embed],
    }

    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    if resp.status_code not in (200, 204):
        print(f"⚠️  Error enviando a Discord ({resp.status_code}): {resp.text}")
    else:
        print(f"✅ Notificado: {codigo} - {nombre[:60]}")


def main():
    keywords = cargar_keywords()
    if not keywords:
        print("No hay palabras clave configuradas, no se hace nada.")
        return

    estado = cargar_estado()
    ya_notificados = set(estado["notificados"])

    items = obtener_compras_agiles()
    print(f"🔎 {len(items)} Compras Ágiles revisadas en esta corrida.")

    nuevos = 0
    for item in items:
        codigo = item.get("codigo")
        if not codigo or codigo in ya_notificados:
            continue

        keyword = coincide_con_keywords(item, keywords)
        if keyword:
            enviar_discord(item, keyword)
            ya_notificados.add(codigo)
            nuevos += 1
            time.sleep(0.5)  # evita saturar el webhook de Discord

    estado["notificados"] = list(ya_notificados)
    guardar_estado(estado)
    print(f"✨ Listo. {nuevos} notificaciones nuevas enviadas.")


if __name__ == "__main__":
    main()
