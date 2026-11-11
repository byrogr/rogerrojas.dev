---
title: 'Lambdas e interfaces funcionales en Java: Function, Predicate, Supplier y más'
description: 'Qué es una interfaz funcional, las que usarás casi a diario y tres usos reales en un sistema de pagos: conciliar contra el extracto bancario, elegir una estrategia de validación y ejecutar una acción dentro de un lock distribuido. Segundo artículo de una serie de ocho.'
pubDate: 2026-11-11
tags: ['Java', 'Java 21', 'Programación funcional', 'Backend']
draft: false
---

En el [artículo anterior](/blog/programacion-funcional-java-21/) viste que, en programación funcional, las funciones son valores. Hoy toca ver cómo se expresa eso en Java: con lambdas e interfaces funcionales.

Vas a ver qué es una interfaz funcional, cuáles usarás a diario y tres usos reales de un sistema de pagos, de menos a más.

## Interfaz funcional y lambda

Una **interfaz funcional** es una interfaz con un único método abstracto. Eso es todo. `Predicate<String>`, por ejemplo, solo tiene `test`, que recibe un valor y devuelve `true` o `false`.

Una **lambda** es una forma corta de implementar ese método sin escribir una clase:

```java
Predicate<String> isEmpty = s -> s.isBlank();
```

Se lee así: «dado un `s`, devuelve `s.isBlank()`». Java deduce el tipo de `s` a partir de `Predicate<String>`, y cuando el cuerpo es una sola expresión no hacen falta llaves ni `return`.

Cuando la lambda solo llama a un método que ya existe, puedes usar una **referencia a método**: `String::isBlank` hace exactamente lo mismo con menos ruido.

## Las interfaces que vas a usar a diario

El paquete `java.util.function` trae muchas, pero estas cubren casi todo lo cotidiano:

| Interfaz | Método | Recibe | Devuelve |
| --- | --- | --- | --- |
| `Predicate<T>` | `test` | un `T` | `boolean` |
| `Function<T, R>` | `apply` | un `T` | un `R` |
| `Supplier<T>` | `get` | nada | un `T` |
| `Consumer<T>` | `accept` | un `T` | nada |
| `BiFunction<T, U, R>` | `apply` | un `T` y un `U` | un `R` |
| `BinaryOperator<T>` | `apply` | dos `T` | un `T` |

`BinaryOperator<T>` es un `BiFunction<T, T, T>` con un nombre más corto, igual que `UnaryOperator<T>` lo es de `Function<T, T>`.

## 1. Conciliar un pago contra el extracto bancario

Primer contacto: un pago registrado debe coincidir con los movimientos del extracto que tienen el mismo número de operación y la misma fecha. Cada lambda de este pipeline cumple el contrato de una interfaz funcional:

```java
private PaymentMatch reconcile(Payment payment, List<BankTransaction> transactions) {
    var paymentId = normalize(payment.getOperationNumber());

    BigDecimal total = transactions.stream()
        .filter(tx -> normalize(tx.getId()).equals(paymentId))     // Predicate<BankTransaction>
        .filter(tx -> tx.getBookingDate() != null)                 // Predicate<BankTransaction>
        .filter(tx -> isSameDay(tx.getBookingDate(), payment.getDepositDate()))
        .map(tx -> BigDecimal.valueOf(tx.getAmount()))             // Function<BankTransaction, BigDecimal>
        .reduce(BigDecimal.ZERO, BigDecimal::add);                 // BinaryOperator<BigDecimal>

    return new PaymentMatch(payment.getOperationNumber(),
                            total.compareTo(BigDecimal.ZERO) > 0,
                            total);
}
```

- `filter` pide un `Predicate`, `map` una `Function` y `reduce` un `BinaryOperator`. Cada lambda es la implementación de `test` o `apply`.
- `BigDecimal::add` es una referencia a método que equivale a `(a, b) -> a.add(b)`.
- Con dinero se usa `BigDecimal`, nunca `double`. Aquí el extracto trae el monto como `double`, así que se convierte en la frontera con `BigDecimal.valueOf`, que respeta el valor tal como se escribe (`new BigDecimal(double)` arrastraría el error de representación binaria).

Los streams los veremos a fondo en el próximo artículo. Por ahora quédate con esto: cada operación recibe una función.

## 2. Elegir la estrategia de validación según el tipo de orden

Siguiente nivel: una función también se puede **devolver** como resultado. Para aprobar una orden, la validación depende de si es de compra o de venta:

```java
public Mono<ApprovalResponse> autoApprove(Long orderId, String user) {
    return orderService.findById(orderId)
        .flatMap(order -> resolveValidator(order).apply(order, user));
}

private BiFunction<Order, String, Mono<ApprovalResponse>> resolveValidator(Order order) {
    return switch (order.getType()) {
        case BUY  -> this::validateIncomingPayment;   // referencia a método
        case SELL -> this::validateOutgoingTransfer;  // referencia a método
        default   -> (o, user) -> Mono.error(         // lambda
                         new UnsupportedOperationException("Tipo no soportado: " + o.getType()));
    };
}
```

`Mono` es el tipo de Project Reactor (el de Spring WebFlux y Quarkus) que representa un valor que llegará más adelante; `flatMap` encadena el siguiente paso cuando llega.

- Es el patrón *Strategy* sin crear una clase por cada estrategia.
- Una referencia a método y una lambda son intercambiables si respetan la misma firma: `(Order, String) -> Mono<ApprovalResponse>`.

### Cuándo crear tu propia interfaz funcional

`BiFunction<Order, String, Mono<ApprovalResponse>>` funciona, pero no dice nada del dominio. Una interfaz propia sí:

```java
@FunctionalInterface
interface PaymentValidator {
    Mono<ApprovalResponse> validate(Order order, String performedBy);
}

private PaymentValidator resolveValidator(Order order) { ... } // mismo cuerpo
```

El cuerpo del `switch` no cambia: las mismas lambdas cumplen el nuevo contrato, y la llamada pasa a ser `validate(order, user)`. La anotación `@FunctionalInterface` es opcional, pero hace que el compilador te avise si alguien agrega un segundo método abstracto.

Regla práctica: usa las interfaces estándar por defecto y crea la tuya cuando un nombre de dominio comunique mejor que la firma genérica.

## 3. Procesar una orden dentro de un lock distribuido

El nivel más alto: el comportamiento se **recibe como parámetro**. Revertir o liquidar una orden exige el mismo ritual: tomar un lock en Redis, releer la orden, comprobar que sigue abierta y liberar el lock al final. Lo que cambia es la acción del medio.

```java
private Mono<Order> withOrderLock(Long orderId, Function<Order, Mono<Order>> action) {
    String key = "order-lock:" + orderId;

    return redis.opsForValue().setIfAbsent(key, "1", LOCK_TTL)
        .filter(Boolean.TRUE::equals)                        // solo si se obtuvo el lock
        .flatMap(acquired -> orderService.findById(orderId)  // relee el estado fresco
            .filter(Order::isOpen)
            .flatMap(action)                                 // aquí se ejecuta lo que te pasaron
            .doFinally(signal -> redis.delete(key).subscribe()));
}

// Uso
withOrderLock(orderId, order -> paymentService.revert(order));
withOrderLock(orderId, order -> paymentService.settle(order));
```

Simplifiqué la versión original quitando logs y validaciones internas.

- Separa el **cómo** (lock, relectura, liberación) del **qué** (revertir, liquidar).
- Es el patrón *execute around*: la misma idea que `try-with-resources`, escrita con funciones.
- `Order::isOpen` y `Boolean.TRUE::equals` son `Predicate` escritos como referencias a método.
- La liberación (`doFinally`) va **dentro** del `flatMap` a propósito: así solo borra el lock quien lo obtuvo. Si estuviera al final de la cadena exterior, se ejecutaría también cuando `setIfAbsent` falla y borraría el lock de otra instancia.

## Variables capturadas: por qué deben ser *effectively final*

En el primer ejemplo, las lambdas usan `paymentId` y `payment`, que vienen de fuera. Una lambda puede capturar variables del método donde la escribiste con una condición: no pueden cambiar después de asignarse. En Java eso se llama *effectively final*, aunque no escribas la palabra `final`.

Si después del pipeline hicieras `paymentId = "otro";`, el compilador respondería: `local variables referenced from a lambda expression must be final or effectively final`.

No es un capricho: la lambda se lleva el valor que tiene la variable en ese momento, y si pudiera cambiar, distintas partes del código verían valores distintos. Es la idea de «los datos no se modifican» del artículo anterior, aplicada por el propio compilador. Ojo: lo que no puede cambiar es la variable, no el objeto al que apunta; modificar una lista capturada compila, pero evítalo.

## Cuándo no usar una lambda

- **Si pasa de dos o tres líneas,** muévela a un método y usa una referencia, como `this::validateIncomingPayment`. El nombre explica lo que hace mejor que el cuerpo.
- **Si la copias en varios sitios,** dale un nombre en una variable o un método.
- **Si necesita lanzar una excepción chequeada,** las interfaces estándar no lo permiten. Lo resolveremos en el artículo 7.

## Resumen y qué sigue

- Una interfaz funcional tiene un solo método abstracto, y una lambda o una referencia a método es una forma corta de implementarla.
- Una función se puede pasar a un método, devolver como resultado o recibir como parámetro para separar el qué del cómo.
- Crea tu propia interfaz cuando un nombre de dominio aporte claridad.
- Las variables que captura una lambda no pueden cambiar: el compilador te protege.

En el próximo artículo vamos a profundizar en `stream()`: `map`, `filter`, `reduce` y `collect`, para procesar listas completas de transacciones.

Si quieres practicar antes, busca en tu código dos métodos que repitan el mismo ritual alrededor de una acción distinta y extráelo a un método que reciba una `Function`. Y si quieres contarme cómo te fue, escríbeme por [LinkedIn](https://www.linkedin.com/in/roger-rojas-effio/).
