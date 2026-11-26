package org.kgmaker.runtime;

import java.io.PrintStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.BooleanSupplier;
import java.util.function.Supplier;

/** Opt-in, synchronous JDK 21 capture. Never records arguments, values or exceptions. */
public final class RuntimeTrace {
    private static final int MAX_FACTS = 50_000;
    private final boolean enabled = "1".equals(System.getenv("KGMAKER_RUNTIME_TRACE"));
    private final List<String> facts = new ArrayList<>();
    private boolean incomplete;

    private void record(String fact) {
        if (!enabled) return;
        if (facts.size() < MAX_FACTS) facts.add(fact);
        else incomplete = true;
    }

    private static String quote(String value) {
        // Only graph IDs are accepted here. JSON escaping does not turn free text into evidence.
        if (value == null || value.length() > 2048 || value.chars().anyMatch(c -> c < 32))
            throw new IllegalArgumentException("Invalid graph symbol identifier");
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    public <T> T call(String caller, String target, Supplier<T> action) {
        if (!enabled) return action.get();
        String base = "{\"kind\":\"call\",\"caller\":" + quote(caller) + ",\"target\":" + quote(target);
        try {
            T value = action.get();
            record(base + ",\"outcome\":\"RETURNED\"}");
            return value;
        } catch (RuntimeException | Error error) {
            record(base + ",\"outcome\":\"THREW\"}");
            throw error;
        }
    }

    /** Place inside a concrete synchronous Java interface override, passing its actual this. */
    public void observeInterfaceDispatch(Object receiver) {
        if (!enabled) return;
        var frames = StackWalker.getInstance(Set.of(StackWalker.Option.RETAIN_CLASS_REFERENCE,
            StackWalker.Option.SHOW_HIDDEN_FRAMES))
            .walk(stack -> stack.skip(1).limit(2).toList());
        if (frames.size() != 2 || receiver == null) {
            incomplete = true;
            return;
        }
        var target = frames.get(0);
        var caller = frames.get(1);
        if (receiver.getClass() != target.getDeclaringClass() || caller.getLineNumber() <= 0) {
            incomplete = true;
            return;
        }
        record("{\"kind\":\"interface_dispatch\",\"caller_owner\":" + quote(caller.getClassName())
            + ",\"caller_name\":" + quote(caller.getMethodName())
            + ",\"caller_descriptor\":" + quote(caller.getDescriptor())
            + ",\"source_line\":" + caller.getLineNumber()
            + ",\"receiver_type\":" + quote(receiver.getClass().getName())
            + ",\"target_owner\":" + quote(target.getClassName())
            + ",\"target_name\":" + quote(target.getMethodName())
            + ",\"target_descriptor\":" + quote(target.getDescriptor()) + "}");
    }

    public <T> T bean(String factory, String beanType, Supplier<T> action) {
        if (!enabled) return action.get();
        String base = "{\"kind\":\"bean\",\"factory\":" + quote(factory) + ",\"bean_type\":" + quote(beanType);
        try {
            T value = action.get();
            record(base + ",\"outcome\":\"" + (value == null ? "NULL" : "CREATED") + "\"}");
            return value;
        } catch (RuntimeException | Error error) {
            record(base + ",\"outcome\":\"THREW\"}");
            throw error;
        }
    }

    public boolean condition(String owner, String predicate, BooleanSupplier action) {
        if (!enabled) return action.getAsBoolean();
        String base = "{\"kind\":\"condition\",\"owner\":" + quote(owner) + ",\"predicate\":" + quote(predicate);
        try {
            boolean matched = action.getAsBoolean();
            record(base + ",\"matched\":" + matched + "}");
            return matched;
        } catch (RuntimeException | Error error) {
            incomplete = true;
            throw error;
        }
    }

    /** Registers the callable in the actual application router, then records the registration. */
    public <T> void mapping(Map<String, Supplier<T>> router, String owner, String handler,
                            String method, String route, Supplier<T> action) {
        if (!enabled) {
            router.put(method + " " + route, action);
            return;
        }
        if (!List.of("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS").contains(method))
            throw new IllegalArgumentException("Unsupported HTTP method");
        String base = "{\"kind\":\"mapping\",\"owner\":" + quote(owner) + ",\"handler\":" + quote(handler);
        // Drop authority (including user-info), query and fragment before hashing.
        String path = route.contains("://") ? URI.create(route).getRawPath() : route.split("[?#]", 2)[0];
        if (path == null || !path.startsWith("/"))
            throw new IllegalArgumentException("Mapping requires an absolute route path");
        String hash;
        try {
            hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(path.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("JDK SHA-256 unavailable");
        }
        router.put(method + " " + route, action);
        record(base + ",\"method\":\"" + method + "\",\"route_sha256\":\"" + hash + "\"}");
    }

    /** Explicit publication only; no shutdown hooks, background agent or application startup. */
    public void writeTo(PrintStream output) {
        if (!enabled) return;
        String diagnostics = "\"INSTRUMENTED_SCOPE_ONLY\"";
        if (facts.isEmpty()) diagnostics += ",\"NO_FACTS\"";
        if (incomplete) diagnostics += ",\"CAPTURE_INCOMPLETE\"";
        output.println("{\"facts\":[" + String.join(",", facts)
            + "],\"status\":\"PARTIAL\",\"diagnostics\":[" + diagnostics + "]}");
    }
}
