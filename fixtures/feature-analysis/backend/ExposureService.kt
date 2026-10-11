package fixture

data class Account(val accountBalance: Double)

class ExposureService {
    fun pessimisticExposure(position: Double): Double = position * 1.1
}
