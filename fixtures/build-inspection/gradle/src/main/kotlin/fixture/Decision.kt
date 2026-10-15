package fixture
fun decision(value: Int): String = when {
    value > 0 -> "positive"
    else -> "other"
}
