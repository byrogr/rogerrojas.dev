---
title: 'Idempotencia en órdenes asíncronas: evitar duplicados con Event Grid y Redis'
description: 'Los sistemas de mensajería entregan «al menos una vez». Este es el patrón que uso para que una orden de compra o venta se procese exactamente una vez.'
pubDate: 2026-10-22
tags: ['Arquitectura', 'Azure', 'Redis', 'Sistemas distribuidos']
---

Cuando una orden de compra o venta se procesa de forma asíncrona, tarde o temprano aparece la misma pregunta: **¿qué pasa si el mismo mensaje llega dos veces?** En un sistema financiero, la respuesta correcta nunca puede ser «se ejecuta dos veces».

## El problema: «al menos una vez»

Servicios como Azure Event Grid garantizan que un evento se entrega *al menos una vez*. Eso significa que los reintentos y los duplicados no son un caso raro: son parte del contrato. El consumidor tiene que estar preparado.

## El patrón: una clave de idempotencia en Redis

La idea es registrar, de forma atómica, que una orden ya empezó a procesarse. Cada orden trae un identificador estable, y ese identificador es la clave.

```text
SET orden:{id} PROCESANDO NX EX 300
```

- `NX` hace que el comando solo funcione si la clave **no existe**.
- `EX 300` asigna un tiempo de vida para que una clave huérfana no bloquee la orden para siempre.

Si el `SET` tiene éxito, este consumidor es el dueño de la orden y la procesa. Si falla, otro consumidor ya la tiene o ya la terminó, y el mensaje se descarta sin efectos secundarios.

## Los casos que rompen la versión ingenua

1. **El proceso cae a mitad de camino.** Si la clave expira antes de terminar, otra instancia puede retomarla. Por eso el procesamiento en sí también debe ser seguro de repetir (por ejemplo, con un estado de la orden que solo avanza hacia adelante).
2. **Clave marcada como «terminada».** Al finalizar, cambia el valor a `COMPLETADA` con un tiempo de vida más largo, para absorber duplicados tardíos.
3. **Redis no es la fuente de verdad.** Redis protege contra la ráfaga de duplicados; el estado definitivo de la orden vive en la base de datos, con una restricción única sobre el identificador.

## Resumen

- Asume que todo mensaje puede llegar más de una vez.
- Usa un identificador estable por orden como clave de idempotencia.
- Reserva la orden con una operación atómica (`SET … NX EX`).
- Haz también idempotente el procesamiento y respáldalo con una restricción en la base de datos.

La idempotencia no es una optimización: es lo que convierte un sistema asíncrono en uno en el que se puede confiar.
