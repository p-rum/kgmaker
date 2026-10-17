package fixture;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

class EnvironmentTest {
    @Test void mixedInteropAndBranches() {
        assertEquals("number:7", JavaBridge.call(true));
        assertEquals("text:bridge", JavaBridge.call(false));
        assertEquals("text:typed", new Worker().process("typed"));
    }
}
