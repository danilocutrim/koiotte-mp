---
max_turns: 30
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, Write, Agent]
runs: 3
---
Crie estes 2 arquivos no diretório atual, exatamente com este conteúdo.

`build.gradle.kts`:
```kotlin
plugins { kotlin("jvm") version "1.9.24"; id("org.springframework.boot") version "3.3.0" }
dependencies { implementation("org.springframework.boot:spring-boot-starter-web"); implementation("io.awspring.cloud:spring-cloud-aws-starter-sqs:3.1.1") }
```

`src/main/kotlin/OrderController.kt`:
```kotlin
@RestController
class OrderController(private val sqs: SqsTemplate) {
    @PostMapping("/orders")
    fun create(@RequestBody order: Order): ResponseEntity<Order> {
        sqs.send("orders-out", order)
        return ResponseEntity.accepted().body(order)
    }

    @SqsListener("payments-queue")
    fun onPayment(event: PaymentEvent) {
        println("payment received: ${event.orderId}")
    }
}
```

Depois analise esse código e documente em `docs/diagrams/payments/flow.md`, em linguagem natural, como o serviço funciona: componentes, fluxos, integrações e infra. Cite os arquivos de onde tirou cada informação e deixe explícito o que não dá para saber só pelo código.
