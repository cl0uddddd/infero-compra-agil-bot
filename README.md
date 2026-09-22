# Bot de alertas Compra Ágil — Infero SpA

Este bot revisa cada 1 hora las Compras Ágiles recién publicadas en Mercado
Público y te avisa en un canal de Discord cuando el título o la descripción
contiene alguna de tus palabras clave (inteligencia artificial, ciencia de
datos, Power BI, SIG, desarrollo de software, etc.).

Es **100% gratis**: usa GitHub Actions, que no cobra por este tipo de tareas
(2.000 minutos gratis al mes en repos privados, e ilimitado en repos
públicos — un bot que corre unos segundos cada hora usa muy poco).

No necesitas programar nada. Solo sigue estos pasos una vez.

---

## Paso 1 — Consigue tu ticket de la API de Mercado Público

1. Entra a https://www.chilecompra.cl/api/
2. Haz clic en **"Pide tu ticket"**.
3. Acepta términos y entra con tu Clave Única.
4. Completa el formulario y solicita el ticket.
5. Te llega por correo (revisa spam). Guárdalo, lo vas a necesitar en el Paso 4.

## Paso 2 — Crea el webhook de Discord

1. En tu servidor de Discord, entra al canal donde quieres recibir los avisos.
2. Clic en el engranaje del canal (Editar canal) → **Integraciones** → **Webhooks** → **Nuevo Webhook**.
3. Ponle un nombre, por ejemplo "Compra Ágil Bot".
4. Clic en **Copiar URL del Webhook**. Guárdala, la necesitas en el Paso 4.

(Si no tienes servidor de Discord, puedes crear uno gratis para ti en segundos desde la app o discord.com — solo con un canal de texto basta.)

## Paso 3 — Sube este proyecto a GitHub

1. Crea una cuenta gratis en https://github.com si no tienes.
2. Crea un repositorio nuevo (puede ser **privado**, por ejemplo `infero-compra-agil-bot`).
3. Sube todos los archivos de esta carpeta a ese repositorio. La forma más
   fácil sin usar la terminal: en la página del repo, botón **"Add file" →
   "Upload files"**, arrastra todos los archivos (incluyendo la carpeta
   `.github/workflows/monitor.yml`) y confirma.

## Paso 4 — Configura tus claves como "Secrets" (para que no queden expuestas)

1. En tu repositorio, ve a **Settings → Secrets and variables → Actions**.
2. Clic en **"New repository secret"** y crea estos dos:
   - Nombre: `MP_TICKET` → Valor: el ticket que te llegó por correo (Paso 1).
   - Nombre: `DISCORD_WEBHOOK_URL` → Valor: la URL del webhook (Paso 2).

## Paso 5 — Activa el bot

1. Ve a la pestaña **Actions** de tu repositorio.
2. Si GitHub pregunta, activa los workflows ("I understand my workflows, go ahead and enable them").
3. Entra al workflow **"Monitor Compra Ágil"** y haz clic en **"Run workflow"**
   para probarlo manualmente la primera vez.
4. Si todo está bien configurado, deberías recibir en Discord cualquier
   Compra Ágil publicada en los últimos 70 minutos que coincida con tus
   palabras clave. Si no hay ninguna en ese momento, no llega nada (es normal).

A partir de ahí, **corre solo cada 1 hora**, sin que tengas que hacer nada.

---

## Cómo editar tus palabras clave

Abre el archivo `keywords.txt` en GitHub (o donde quieras) y agrega, quita o
cambia líneas — una palabra o frase por línea. No importan tildes ni
mayúsculas. Ya viene precargado con los rubros de Infero SpA (IA, ciencia de
datos, Power BI, SIG, estadística, desarrollo de software, automatización,
etc.), pero puedes ajustarlo cuando quieras.

## Cómo funciona por dentro (por si te sirve)

- `monitor.py`: se conecta a la API pública de Compra Ágil, pide lo publicado
  en los últimos 30 minutos, y revisa si el nombre/descripción calza con tus
  palabras clave.
- `state.json`: guarda los códigos ya notificados para no avisarte dos veces
  de la misma compra. El propio bot lo actualiza y lo guarda en el repo.
- `.github/workflows/monitor.yml`: le dice a GitHub que ejecute el script
  cada 1 hora, gratis, en sus propios servidores (no necesitas tener tu
  computador prendido).

## Notas importantes

- La API tiene una **cuota diaria** de solicitudes por ticket. Si la agotas,
  el bot simplemente espera a la próxima corrida sin fallar. Si necesitas más
  cuota, puedes pedir un ticket de mayor límite directamente a ChileCompra.
- El filtro actual solo revisa procesos en estado **"publicada"** (recién
  abiertos). Si quieres también avisos cuando cambian a otro estado, se puede
  ajustar la variable `ESTADOS` en `monitor.yml`.
- Si en algún momento quieres cambiar la frecuencia (por ejemplo cada 30 min
  para enterarte más rápido, o cada 2 horas para gastar menos minutos de
  GitHub Actions), se edita la línea `cron: "0 * * * *"` en `monitor.yml`
  (por ejemplo `*/30 * * * *` para cada 30 min, o `0 */2 * * *` para cada 2
  horas) y, si corresponde, el valor de `TTL_CAMBIO_MS` en `monitor.py` para
  que la ventana de revisión sea un poco mayor que ese intervalo.
