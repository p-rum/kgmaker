package golden
fun String.decorate(suffix: String = "!"): String = this + suffix
inline fun inlineTarget(value: Int): Int = value + 1
suspend fun suspendTarget(): Int = inlineTarget(1)
suspend fun suspendCaller(): Int = suspendTarget()
fun extensionCaller(): String = "x".decorate()
