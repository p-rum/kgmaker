package fixture
fun target(x: Int): Int = Helper.plus(x)
fun caller(): Int = target(3)
fun jdk(x: Int): Int = java.lang.Math.abs(x)
fun mappedBuiltin(s: String): String = s.substring(1)
fun missing(): Int = absent(4)
fun pick(x: String?): Int = 1
fun pick(x: Int?): Int = 2
fun ambiguous(): Int = pick(null)
