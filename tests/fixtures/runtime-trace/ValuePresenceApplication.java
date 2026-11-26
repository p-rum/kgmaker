package fixture;

import org.kgmaker.runtime.RuntimeTrace;

public final class ValuePresenceApplication {
    private static final RuntimeTrace TRACE = new RuntimeTrace();

    static final class Source { String status; String reversed; String repeated; String callOnly; }
    static final class Target { String status; String reversed; String repeated; String callOnly; }

    static void copy(Source source, Target target) {
        target.status = source.status; TRACE.observeValuePresence(source.status, target.status);
    }

    static void reversed(Source source, Target target) {
        target.reversed = source.reversed; TRACE.observeValuePresence(target.reversed, source.reversed);
    }

    static void ambiguous(Source source, Target target) {
        target.repeated = source.repeated; target.repeated = source.repeated; TRACE.observeValuePresence(source.repeated, target.repeated);
    }

    static void plain(Source source, Target target) {
        target.callOnly = source.callOnly;
    }

    public static void main(String[] args) {
        Source source = new Source();
        if (!"absent".equals(args[0])) source.status = System.getenv("FIXTURE_ONLY_VALUE");
        source.reversed = source.repeated = source.callOnly = source.status;
        Target target = new Target();
        String actual = switch (args[0]) {
            case "reversed" -> { reversed(source, target); yield target.reversed; }
            case "ambiguous" -> { ambiguous(source, target); yield target.repeated; }
            case "call" -> TRACE.call(args[1], args[2], () -> { plain(source, target); return target.callOnly; });
            default -> { copy(source, target); yield target.status; }
        };
        if (source.status != actual) throw new IllegalStateException("Field transfer failed");
        TRACE.writeTo(System.out);
    }
}
