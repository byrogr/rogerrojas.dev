---
title: 'Programación funcional en Java 21: qué es y por qué importa'
description: 'Qué es la programación funcional, cómo se ve en un caso real (la rentabilidad de un portafolio de criptoactivos), qué se gana y qué se sacrifica frente al estilo imperativo, y qué herramientas te da Java 21. Primer artículo de una serie de ocho.'
pubDate: 2026-11-02
tags: ['Java', 'Java 21', 'Programación funcional', 'Backend']
draft: false
---

Si llevas un tiempo programando en Java, seguro has escrito un bucle `for` que recorre una lista, tiene tres `if` anidados y va modificando una variable acumuladora. Funciona, pero un mes después cuesta entender qué hace realmente.

La programación funcional propone otra forma de escribir ese mismo código: describir *qué* quieres obtener en lugar de *cómo* recorrer los datos. Desde Java 8, y mucho más en Java 21, el lenguaje te da las herramientas para hacerlo.

En este artículo vas a ver qué es la programación funcional, cómo se ve en un caso real, qué se gana y qué se sacrifica frente al estilo imperativo, y por qué vale la pena aprenderla. Es el primero de una serie de ocho.

## Qué es la programación funcional

No necesitas teoría matemática para entenderla. Se apoya en tres ideas:

- **Las funciones son valores.** Puedes guardar una función en una variable, pasarla como parámetro a otro método o devolverla como resultado. Es lo que permite escribir «qué hacer con cada elemento» y entregárselo a otro código.
- **Los datos no se modifican.** En lugar de cambiar un objeto existente, creas uno nuevo con el cambio aplicado. Así nadie te sorprende modificando algo que creías estable.
- **Las funciones no tienen efectos ocultos.** Con los mismos datos de entrada devuelven siempre el mismo resultado y no tocan nada fuera de ellas. Por eso son fáciles de probar.

## Un caso real: la rentabilidad de un portafolio

El ejemplo sale de un cálculo de rentabilidad de un portafolio de criptoactivos. Lo simplifiqué para que compile sin dependencias: sin repositorios, sin programación reactiva y sin logs.

El contexto es este: el usuario tiene billeteras, una por moneda, cada una con su tipo de cambio actual. También tiene órdenes de compra en las que invirtió un monto en dólares y recibió una cantidad del activo. Queremos saber cuánto invirtió en total, cuánto vale hoy lo que compró, cuánto ganó o perdió y qué porcentaje de rentabilidad representa.

### El modelo y los helpers

Los datos son `record`, y los dos métodos de redondeo los usan ambas versiones:

```java
record Wallet(String currency, BigDecimal exchangeRate) {}
record Order(String currency, BigDecimal amountInvested, BigDecimal quantity) {}
record Profitability(BigDecimal totalInvested, BigDecimal currentValue,
                     BigDecimal profit, BigDecimal profitabilityPercent) {}

private BigDecimal round2(BigDecimal value) {
    return value.setScale(2, RoundingMode.HALF_EVEN);
}

private BigDecimal percent(BigDecimal value, BigDecimal divider) {
    if (divider.compareTo(BigDecimal.ZERO) == 0) {
        divider = BigDecimal.ONE;
    }
    return value.divide(divider, 4, RoundingMode.HALF_EVEN)
            .multiply(BigDecimal.valueOf(100))
            .setScale(2, RoundingMode.HALF_EVEN);
}
```

### Versión imperativa

Primero, la forma tradicional, con bucles y acumuladores:

```java
public Profitability calculate(List<Wallet> wallets, List<Order> orders) {
    // 1. Indexar las billeteras por moneda
    Map<String, Wallet> walletByCurrency = new HashMap<>();
    for (Wallet wallet : wallets) {
        if (walletByCurrency.containsKey(wallet.currency())) {
            throw new IllegalStateException("Duplicate key " + wallet.currency());
        }
        walletByCurrency.put(wallet.currency(), wallet);
    }

    // 2. Acumular inversión y valor actual en un solo recorrido
    BigDecimal totalInvested = BigDecimal.ZERO;
    BigDecimal currentValue = BigDecimal.ZERO;

    for (Order order : orders) {
        Wallet wallet = walletByCurrency.get(order.currency());
        if (wallet == null) {
            continue; // orden de una moneda sin billetera: se ignora
        }

        totalInvested = totalInvested.add(round2(order.amountInvested()));
        currentValue = currentValue.add(
                round2(order.quantity().multiply(wallet.exchangeRate())));
    }

    // 3. Ganancia y rentabilidad
    BigDecimal profit = currentValue.subtract(totalInvested);
    BigDecimal profitability = percent(profit, totalInvested);

    return new Profitability(totalInvested, currentValue, profit, profitability);
}
```

### Versión funcional

Y este es el mismo cálculo con streams:

```java
public Profitability calculate(List<Wallet> wallets, List<Order> orders) {
    Map<String, Wallet> walletByCurrency = wallets.stream()
            .collect(Collectors.toMap(Wallet::currency, wallet -> wallet));

    List<Order> validOrders = orders.stream()
            .filter(order -> walletByCurrency.containsKey(order.currency()))
            .toList();

    BigDecimal totalInvested = validOrders.stream()
            .map(Order::amountInvested)
            .map(this::round2)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

    BigDecimal currentValue = validOrders.stream()
            .map(order -> order.quantity()
                    .multiply(walletByCurrency.get(order.currency()).exchangeRate()))
            .map(this::round2)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

    BigDecimal profit = currentValue.subtract(totalInvested);
    BigDecimal profitability = percent(profit, totalInvested);

    return new Profitability(totalInvested, currentValue, profit, profitability);
}
```

Cada valor se lee de arriba abajo como una receta. Por ejemplo, `totalInvested`: toma las órdenes válidas, quédate con el monto invertido, redondéalo y súmalo todo. Las expresiones con `->` son *lambdas*: funciones pequeñas que le pasas a `filter` y `map` para decirles qué hacer con cada elemento. Las que usan `::`, como `Order::amountInvested` o `BigDecimal::add`, son *referencias a métodos*: la forma corta de una lambda que solo llama a un método existente.

### Concepto por concepto

| Concepto | Funcional | Imperativo |
| --- | --- | --- |
| Indexar billeteras por moneda | `Collectors.toMap(...)` | `HashMap` y `put` en un `for` |
| Descartar órdenes sin billetera | `filter(...)` y una lista intermedia | `if (wallet == null) continue;` |
| Valor actual de cada orden | `map(order -> quantity × rate)` | `multiply` dentro del bucle |
| Sumar montos | `reduce(BigDecimal.ZERO, BigDecimal::add)` | `total = total.add(x)` |
| Recorridos sobre las órdenes | 3: filtrar, sumar inversión y sumar valor | 1 solo bucle para ambas sumas |

Hay dos detalles que conviene notar:

- **`BigDecimal` es inmutable.** En la versión imperativa hay que reasignar: `total = total.add(x)`. Escribir solo `total.add(x)` es un error típico, porque no modifica nada. Con `reduce` ese problema no existe.
- **Claves duplicadas.** `Collectors.toMap` lanza una excepción si dos billeteras tienen la misma moneda, mientras que `HashMap.put` sobrescribiría la anterior sin avisar. Por eso la versión imperativa lleva un `throw` explícito: para que las dos se comporten igual.

### La regla del filtro como valor

La condición del `filter` también se puede guardar en una variable con nombre:

```java
Predicate<Order> hasWallet = order -> walletByCurrency.containsKey(order.currency());

List<Order> validOrders = orders.stream()
        .filter(hasWallet)
        .toList();
```

Eso es «las funciones son valores» en la práctica: `hasWallet` es una regla de negocio con nombre que puedes probar por separado y pasar a cualquier método que la necesite.

## Trade-offs: funcional o imperativo en este caso

Ninguna de las dos versiones es incorrecta: dan exactamente el mismo resultado. La pregunta es cuál conviene mantener. En este caso, la funcional.

### Lo que se gana

- **Cada cálculo se lee por separado.** Para saber cómo se obtiene `totalInvested` basta con leer su pipeline de cuatro líneas. En la versión imperativa, `totalInvested` y `currentValue` se calculan juntos dentro del mismo bucle, y para entender uno hay que leer el bucle completo y descartar mentalmente lo que corresponde al otro.
- **Desaparecen los errores típicos de los acumuladores.** `totalInvested.add(...)` sin reasignar compila sin advertencias, pero deja el total siempre en cero. Con `reduce(BigDecimal.ZERO, BigDecimal::add)` ese error no puede ocurrir, ni tampoco olvidar inicializar el acumulador o reutilizarlo por error.
- **Las variables no cambian después de asignarse.** En la versión funcional, `totalInvested` y `currentValue` reciben su valor una sola vez. En la imperativa son variables que cambian en cada vuelta del bucle. Cuando se calcula dinero, conviene que un valor no pueda alterarse por accidente más adelante en el método, y depurar es más fácil cuando cada variable tiene un único valor.
- **La regla de negocio queda escrita de forma explícita.** `.filter(order -> walletByCurrency.containsKey(order.currency()))` dice directamente «solo cuentan las órdenes de monedas que el usuario tiene habilitadas». En la versión imperativa, la misma regla es un `if (wallet == null) continue;` dentro del bucle, fácil de pasar por alto.
- **Es más fácil de modificar sin romper lo demás.** Si mañana piden excluir las órdenes canceladas o mostrar el total por moneda, basta con añadir un `.filter(...)` o cambiar el `reduce` por un `Collectors.groupingBy(...)`, y cada cambio queda aislado en su pipeline. En la imperativa hay que tocar el bucle compartido, con el riesgo de afectar la otra suma.
- **Hay menos estado que revisar en un code review.** En la versión funcional solo hay que comprobar qué se transforma y qué se suma. En la imperativa también hay que revisar el orden de las instrucciones, el `continue`, las reasignaciones y que los dos acumuladores se actualicen en el mismo caso.

### Lo que se sacrifica

- **Más recorridos y una lista intermedia.** La versión funcional recorre las órdenes tres veces (filtro, suma de la inversión y suma del valor) y crea `validOrders`. La imperativa hace todo en un solo bucle, sin memoria extra.
- **Un vocabulario que hay que aprender.** `reduce`, `Collectors` y las referencias a métodos son naturales para quien ya los usa, pero un equipo que no los conoce va a leer más rápido el bucle.
- **Pipelines que pueden crecer de más.** Si cada paso se vuelve una lambda de varias líneas, la ventaja de leer «de arriba abajo» se pierde. La claridad depende de mantener cada pipeline corto.

### Por qué aquí gana la funcional

Un portafolio tiene pocas órdenes por usuario, normalmente decenas o cientos, así que la diferencia de rendimiento entre uno y tres recorridos es despreciable. A cambio se gana claridad y seguridad en un cálculo de dinero, donde un error silencioso cuesta mucho más que unos microsegundos.

> Si fueran millones de registros o una ruta crítica de rendimiento, la versión de un solo bucle sí tendría ventaja. La decisión depende del volumen y de lo que cueste equivocarse.

## Qué te ofrece Java 21

Java 21 es una versión de soporte a largo plazo (LTS) y reúne casi todo lo que Java fue sumando para escribir código funcional:

- **Lambdas, streams y `Optional`** (desde Java 8): la base para transformar datos sin bucles y manejar valores ausentes sin `null`.
- **`record`** (Java 16): clases de datos inmutables en una línea, como `Wallet` y `Order` en el ejemplo.
- **`Stream.toList()`** (Java 16): una lista inmodificable al final del pipeline, sin `Collectors.toList()`.
- **`sealed`** (Java 17): jerarquías cerradas, donde tú decides qué tipos existen.
- **Pattern matching en `switch` y record patterns** (Java 21): decidir según el tipo y la forma de los datos, con el compilador verificando que no olvidaste ningún caso.

A lo largo de la serie vamos a usar cada una de estas herramientas con ejemplos.

## Por qué importa

- **Código que se lee mejor.** Describes la intención y dejas que el lenguaje se encargue del recorrido. Menos variables temporales, menos lugares donde equivocarse.
- **Menos errores con datos compartidos.** Si nada se modifica a escondidas, es mucho más difícil que dos partes del programa se pisen entre sí, sobre todo con varios hilos.
- **Pruebas más simples.** Una función que solo depende de sus parámetros se prueba con una llamada y una comprobación, sin preparar escenarios complicados.
- **Es el estilo que ya usan tus herramientas.** Los streams, `Optional` y los pipelines reactivos de frameworks como Quarkus o Spring WebFlux se escriben con este vocabulario. Entenderlo te facilita leer y escribir ese código.

## Cuándo no usarlo

No todo problema mejora con streams. Un bucle simple y claro sigue siendo mejor que una cadena larga de operaciones difíciles de seguir, y algunos algoritmos que necesitan estado o salir a medio recorrido se escriben con más claridad de forma tradicional. Además, Java no es un lenguaje funcional puro: mezcla ambos estilos, y está bien.

> La meta no es eliminar los bucles, sino elegir la herramienta que deje el código más claro.

## Qué viene en la serie

En los próximos artículos vamos a ir de lo básico a lo avanzado: lambdas e interfaces funcionales, streams, `Optional`, inmutabilidad, composición de funciones, manejo de errores sin excepciones y pattern matching. Todos con casos del mundo financiero.

Si quieres ir practicando mientras tanto, toma un bucle de tu propio código y prueba reescribirlo con `stream()`. Y si quieres contarme cómo te fue, escríbeme por [LinkedIn](https://www.linkedin.com/in/roger-rojas-effio/).
