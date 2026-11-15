package fixture;
public final class Checkout {
    static int charge(int amount) { return amount + 1; }
    public int checkout(boolean approved, int amount) {
        int result;
        if (approved) result = charge(amount);
        else result = amount;
        while (result < 3) result++;
        return result;
    }
    public void unresolved() { MissingGateway.send(); }
}
