package fixture;

import java.util.HashMap;
import java.util.Map;
import java.util.function.Supplier;
import org.kgmaker.runtime.RuntimeTrace;

/** Executable application: creates a service, evaluates configuration and dispatches a router. */
public class TraceApplication {
    static int calls;
    public static class Service {
        String greet(String authorization) {
            calls++;
            return authorization;
        }
    }
    static Service createService() { return new Service(); }
    static boolean enabled() { return !"disabled".equals(System.getenv("FIXTURE_MODE")); }

    public static void main(String[] ids) {
        RuntimeTrace trace = new RuntimeTrace();
        Service service = trace.bean(ids[1], ids[2], TraceApplication::createService);
        Map<String, Supplier<String>> router = new HashMap<>();
        String credentials = "Authorization: Bearer VERYPRIVATE";
        String route = "https://user:URLPASSWORD@example.invalid/orders?token=QUERYSECRET";
        if (trace.condition(ids[0], ids[3], TraceApplication::enabled)) {
            trace.mapping(router, ids[0], ids[4], "GET", route,
                () -> trace.call(ids[0], ids[4], () -> service.greet(credentials)));
            if (!credentials.equals(router.get("GET " + route).get()) || calls != 1)
                throw new IllegalStateException("Application result is incorrect");
        } else if (calls != 0 || !router.isEmpty()) {
            throw new IllegalStateException("Disabled branch executed");
        }
        trace.writeTo(System.out);
    }
}
