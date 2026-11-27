package fixture;

import org.kgmaker.runtime.RuntimeTrace;

public final class ValuePresenceApplication {
    private static final RuntimeTrace TRACE = new RuntimeTrace();

    static final class Source { static String status; static String reversed; static String repeated; static String callOnly; }
    static final class Target { static String status; static String reversed; static String repeated; static String callOnly; }
    static final class InstanceSource { String status; }
    static final class InstanceTarget { String status; }

    static void copy() {
        Target.status = Source.status; TRACE.observeValuePresence(Source.status, Target.status);
    }

    static void reversed() {
        Target.reversed = Source.reversed; TRACE.observeValuePresence(Target.reversed, Source.reversed);
    }

    static void ambiguous() {
        Target.repeated = Source.repeated; Target.repeated = Source.repeated; TRACE.observeValuePresence(Source.repeated, Target.repeated);
    }

    static void plain() {
        Target.callOnly = Source.callOnly;
    }

    static String throwingCompanion() {
        throw new UnsupportedOperationException();
    }

    static void misleading(InstanceSource source, InstanceTarget target, InstanceSource otherSource, InstanceTarget otherTarget) {
        target.status = source.status; TRACE.observeValuePresence(otherSource.status, otherTarget.status);
    }

    static void differentReceivers() {
        var source = new InstanceSource();
        var target = new InstanceTarget();
        var otherSource = new InstanceSource();
        var otherTarget = new InstanceTarget();
        otherSource.status = otherTarget.status = System.getenv("FIXTURE_ONLY_VALUE");
        if (source == otherSource || target == otherTarget || otherTarget.status == null)
            throw new IllegalStateException("Expected distinct receivers and a non-null decoy");
        misleading(source, target, otherSource, otherTarget);
        if (target.status != null) throw new IllegalStateException("The real assignment must copy null");
    }

    public static void main(String[] args) {
        if ("different-receivers".equals(args[0])) {
            differentReceivers();
            TRACE.writeTo(System.out);
            return;
        }
        if (!"absent".equals(args[0]) && !"combined-absent".equals(args[0]))
            Source.status = System.getenv("FIXTURE_ONLY_VALUE");
        Source.reversed = Source.repeated = Source.callOnly = Source.status;
        String actual = switch (args[0]) {
            case "reversed" -> { reversed(); yield Target.reversed; }
            case "ambiguous" -> { ambiguous(); yield Target.repeated; }
            case "call" -> TRACE.call(args[1], args[2], () -> { plain(); return Target.callOnly; });
            case "combined-present", "combined-absent", "combined-threw" -> {
                if ("combined-threw".equals(args[0])) {
                    try {
                        TRACE.call(args[1], args[3], ValuePresenceApplication::throwingCompanion);
                    } catch (UnsupportedOperationException expected) {
                        // The companion exception is handled outside the value transfer.
                    }
                } else {
                    TRACE.call(args[1], args[3], () -> { plain(); return Target.callOnly; });
                }
                yield TRACE.call(args[1], args[2], () -> { copy(); return Target.status; });
            }
            default -> { copy(); yield Target.status; }
        };
        if (Source.status != actual) throw new IllegalStateException("Field transfer failed");
        TRACE.writeTo(System.out);
    }
}
