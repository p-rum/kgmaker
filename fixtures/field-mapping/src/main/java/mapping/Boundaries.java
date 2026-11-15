package mapping;
public class Boundaries {
    public String getValue() { return "base"; }
    private static String identity(String first, String second) { return second; }
    private static String identity(int first, String second) { return "unrelated"; }
    private static String[] pack(String... values) { return values; }
    public static void vararg(Source source, Target target) {
        target.packed = pack(source.publicName);
    }
    private static String recursive(String value) { return recursive(value); }
    public static void overloaded(Source source, Target target) {
        target.publicName = identity("ignored", source.publicName);
    }
    public static void unknown(Boundaries receiver, Source source, Target target) {
        target.publicName = receiver.getValue();
        target.setName(recursive(source.getName()));
    }
    public static void overwritten(Source source, Target target) {
        String value = source.publicName;
        value = "unrelated";
        target.publicName = value;
    }
    public static void loop(Source source, Target target) {
        String value = source.publicName;
        while (value != null) { value = "other"; break; }
        target.publicName = value;
    }
}
