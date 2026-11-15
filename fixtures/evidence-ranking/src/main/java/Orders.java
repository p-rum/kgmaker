package ranking;

// Production-shaped declarations: enum method execution is distinct from type reuse.
enum Currency {
    EUR;
    static int decide(int value) { return value > 0 ? value : 0; }
}
class Order { Currency currency; int value; }
interface Gateway { void save(Order order); }
class Store implements Gateway { public void save(Order order) {} }
class AlternateStore implements Gateway { public void save(Order order) {} }
class Orders {
    static int entry(Order order) { return Currency.decide(order.value); }
    static void dispatch(Gateway gateway, Order order) { gateway.save(order); }
    static void unresolved(Order order) { MissingClient.send(order); }
    static Currency referenceOnly(Order order) { return order.currency; }
    static java.util.function.IntUnaryOperator methodReference() { return Currency::decide; }
}
