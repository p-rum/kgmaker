package mapping;
public class Manual {
    private static String identity(String value) { return value; }
    private static String business(String value) { return value.trim(); }
    public static void copy(Source source, Target target) {
        target.publicName = source.publicName;
        target.setName(identity(source.getName()));
    }
    public static void transformed(Source source, Target target) {
        target.setName(business(source.getName()));
    }
    public static void ambiguous(Source source, Target target, boolean flag) {
        String value;
        if (flag) { value = source.publicName; } else { value = "other"; }
        target.setName(value);
    }
}
