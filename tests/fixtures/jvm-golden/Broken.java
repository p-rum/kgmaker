package golden;
public final class Broken {
    static int pick(String value) { return 1; }
    static int pick(Integer value) { return 2; }
    public static int missing() { return absent(1); }
    public static int ambiguous() { return pick(null); }
}
