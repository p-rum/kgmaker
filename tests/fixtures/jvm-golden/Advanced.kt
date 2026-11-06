package fixture
class Advanced(val seed: Int) {
  var label: String = consume("initial")
    get() = field
    set(next) { field = next }
  init { consume("init") }
  constructor(): this(1) { consume("secondary") }
  inline fun <T> apply(value: T, transform: (T) -> String): String = transform(value)
  operator fun plus(other: Advanced): Advanced = Advanced(seed + other.seed)
  suspend fun suspendValue(): String = consume("suspend")
  fun consume(value: String): String = value
  fun readLabel(): String = label
  fun writeLabel() { label = "changed" }
  fun scenario(): String {
    val reference = ::consume
    val lambda = { value: String -> consume(value) }
    val combined = this + Advanced()
    return apply("x", lambda) + reference("r") + combined.seed
  }
}