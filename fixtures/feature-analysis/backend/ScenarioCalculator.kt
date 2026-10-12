data class ScenarioInput(val pessimisticDecline: Double)
data class ScenarioReport(val midDecline: Double)
class ScenarioCalculator {
    fun calculate(input: ScenarioInput): ScenarioReport {
        val midDecline = input.pessimisticDecline / 2
        return ScenarioReport(midDecline)
    }
}
