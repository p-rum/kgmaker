package fixture;

import org.kgmaker.runtime.RuntimeTrace;

/** Two concrete overrides reached by the same synchronous interface call. */
public final class DispatchApplication {
    private static final RuntimeTrace TRACE = new RuntimeTrace();

    public interface Service {
        int greet();
    }

    public static final class Alpha implements Service {
        public int greet() {
            TRACE.observeInterfaceDispatch(this);
            return 1;
        }
    }

    public static final class Beta implements Service {
        public int greet() {
            TRACE.observeInterfaceDispatch(this);
            return 2;
        }
    }

    static int invoke(Service service) {
        return service.greet();
    }

    static int alternative(Service service) {
        return service.greet();
    }

    static int ambiguous(Service service) {
        return service.greet() + service.greet();
    }

    static int mixed(Service service) {
        return service.greet() + ((Alpha) service).greet();
    }

    static int concatenate(Service service) {
        String text = "v=" + service.greet();
        return text.charAt(2) - '0';
    }

    static int lambda(Service service) {
        Runnable deferred = () -> {}; int value = service.greet();
        return value;
    }

    public static void main(String[] args) {
        boolean alpha = "alpha".equals(args[0]);
        Service service = alpha ? new Alpha() : new Beta();
        int result = switch (args[1]) {
            case "ambiguous" -> ambiguous(service);
            case "mixed" -> mixed(service);
            case "concatenate" -> concatenate(service);
            case "lambda" -> lambda(service);
            default -> invoke(service);
        };
        boolean repeated = "ambiguous".equals(args[1]) || "mixed".equals(args[1]);
        if (result != (alpha ? 1 : 2) * (repeated ? 2 : 1)) {
            throw new IllegalStateException("The selected receiver did not execute");
        }
        TRACE.writeTo(System.out);
    }
}
