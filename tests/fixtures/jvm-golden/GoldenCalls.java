package golden;
final class Left {
    static String same(int value) { return "left-int"; }
    static String same(String value) { return "left-string"; }
}
final class Right {
    static String same(int value) { return "right-int"; }
    static String same(String value) { return "right-string"; }
}
public final class GoldenCalls {
    public static String choose(boolean flag) {
        if (flag) return Left.same(1);
        return Right.same("x");
    }
    public static String overloads() { return Left.same(1) + Left.same("x"); }
    public static String owners() { return Left.same(1) + Right.same(1); }
    public static int recurse(int value) {
        if (value <= 0) return 0;
        return recurse(value - 1);
    }
    public static java.util.function.Supplier<String> reference() { return GoldenCalls::target; }
    public static Runnable lambda() { return () -> target(); }
    public static String target() { return "value"; }
    public static Object dynamic(String type) throws Exception {
        return Class.forName(type).getMethod("target").invoke(null);
    }
}
