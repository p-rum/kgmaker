package fixture

class Worker {
    fun process(value: Int): String = "number:$value"
    fun process(value: String): String = "text:$value"
    fun choose(flag: Boolean): String {
        if (flag) return process(7)
        return process(JavaBridge.text())
    }
}
