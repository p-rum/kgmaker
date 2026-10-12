data class ExposureInput(val pessimisticDecline: Double)
data class ExposureOutput(val decline: Double)
fun calculate(input: ExposureInput): ExposureOutput = ExposureOutput(input.pessimisticDecline / 2)

@GetMapping("/exposure")
fun exposure(): ExposureOutput = calculate(ExposureInput(4.0))
