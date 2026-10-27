---
title: 'study-agent: convertir Microsoft Learn en un sistema de estudio dentro de Obsidian'
description: 'Un CLI open source que toma una ruta de Microsoft Learn y genera resúmenes, notas enlazadas, mapas conceptuales, preguntas tipo examen y flashcards en tu vault.'
pubDate: 2026-10-12
tags: ['Open source', 'Azure', 'Certificaciones', 'Obsidian']
---

Estudiar para una certificación de Microsoft suele ser leer módulos de Learn… y olvidar la mitad a la semana. Mientras me preparaba para AI-901 y AI-200 me di cuenta de que leer no era el problema: el problema era no tener un sistema para repasar.

Por eso construí **study-agent**, un CLI open source que convierte cualquier ruta o módulo de Microsoft Learn en un sistema de estudio completo dentro de Obsidian.

## Qué genera

A partir de una sola URL, el agente produce en tu vault:

- Un **resumen orientado al examen** con los puntos clave.
- **Notas de concepto** enlazadas entre sí, con las trampas típicas de la prueba.
- Un **mapa conceptual** en Mermaid.
- **Preguntas tipo examen**: opción única, múltiple, Sí/No y escenarios.
- **Flashcards** con repetición espaciada.
- Un **mapa del temario oficial** que muestra qué te falta por estudiar.

## Cómo se usa

Copias la URL de una ruta de Learn, ejecutas el comando con ella y en unos minutos tienes todo listo:

```bash
study-agent generate <url-de-la-ruta-de-learn>
```

Por dentro usa Claude Code con tu propia suscripción, así que no necesitas API keys ni pagar costes extra. Funciona en macOS, Linux y Windows y se instala con un solo comando (está en el README).

## Qué incluye

Viene con el temario de **AI-901 (Azure AI Fundamentals)** y puedes añadir el de cualquier otra certificación. Esa es la idea: que el mapa del temario oficial te diga qué te falta, en lugar de adivinarlo.

## Una lección de diseño

Lo que más valor aporta no es el resumen, sino el **mapa del temario**. Un resumen te da la sensación de haber estudiado; un mapa contra el temario oficial te dice con honestidad qué temas todavía no has tocado.

Si estás preparando una certificación de Azure, pruébalo y cuéntame qué tal. Las estrellas, los issues y los pull requests son bienvenidos.
