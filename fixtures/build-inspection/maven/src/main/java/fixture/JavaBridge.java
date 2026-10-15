package fixture;

public final class JavaBridge {
    public static String text() { return "bridge"; }
    public static String call(boolean flag) { return new Worker().choose(flag); }
}
