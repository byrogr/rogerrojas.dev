---
title: 'La IA nunca debe calcular un monto: guardas para un asistente de pedidos'
description: 'Cómo separé lo que hace el modelo de lo que hace el backend en un asistente de WhatsApp, y por qué una guardia que compara cada cifra con la hoja evita respuestas inventadas.'
pubDate: 2026-10-15
tags: ['IA', 'Java', 'Quarkus', 'Azure']
---

Una clienta que vende ropa por catálogo recibía todos los días las mismas tres preguntas por WhatsApp: *¿cuánto es mi pedido?*, *¿cuándo pago?* y *¿qué pedí?*. Construimos un asistente que las responde solo, leyendo en tiempo real la hoja de Google Sheets donde ella gestiona los pedidos.

Mientras lo diseñaba me puse una regla que ordenó todo lo demás: **la IA nunca calcula ni inventa un monto**.

## Cada pieza hace una sola cosa

El diseño separa responsabilidades con claridad:

- **El modelo** (Azure OpenAI con LangChain4j) solo entiende la pregunta y redacta la respuesta.
- **El backend en Java** calcula los montos a partir de la hoja. Es código determinista, con pruebas.
- **Una guardia** revisa el borrador antes de enviarlo.
- **Un derivador** pasa a la dueña lo que el bot no puede resolver (pagos, reclamos), con un enlace directo a su chat.

## La guardia

Antes de enviar cualquier respuesta, la guardia extrae todas las cifras del texto y las compara con las que calculó el backend. Si alguna no coincide, la respuesta se descarta.

```java
// Ejemplo ilustrativo del enfoque
public Optional<String> validate(String draft, OrderSummary summary) {
    Set<BigDecimal> allowed = summary.allowedAmounts();
    boolean ok = extractAmounts(draft).stream().allMatch(allowed::contains);
    return ok ? Optional.of(draft) : Optional.empty();
}
```

Lo importante es la dirección de la confianza: el modelo propone y el código dispone. Si la guardia dice que no, nunca llega nada al cliente.

## Un aprendizaje: la regla de negocio no es la palabra

La evaluación del asistente detectó un caso curioso. Ante *«¿qué prendas tengo pendientes?»*, el modelo sumaba solo las prendas con estado «Pendiente». Pero para la tienda, **«pendiente» significa «lo que falta pagar»**, no un estado de entrega.

La guardia bloqueó esa respuesta, y la solución no fue más tecnología: fue enseñarle al sistema la regla de negocio.

## El ciclo completo

1. Lectura de la hoja y modelo de dominio.
2. Contrato OpenAPI.
3. Agente de IA con evaluación automática (48 de 48 casos).
4. Canal de WhatsApp con verificación de firma y deduplicación.
5. Despliegue en Azure Container Apps con CI/CD, alertas y un piloto con clientas reales.

> La IA es más útil cuando sabes exactamente qué no debe hacer.

Si trabajas con modelos de lenguaje en dominios donde un número equivocado cuesta dinero, empieza por definir qué decide el modelo y qué decide el código. Todo lo demás se vuelve más fácil de probar.
