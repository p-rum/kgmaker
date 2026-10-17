package fixture;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
class DecisionTest {
    @Test void branches() {
        assertEquals("positive", DecisionKt.decision(1));
        assertEquals("other", DecisionKt.decision(0));
    }
}
