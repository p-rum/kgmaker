# Compiler return/consumer fixtures

Java21, Kotlin2.1.10 K1 and TypeScript5.7.3 strict source inputs cover distinct
branching return expressions, nullable call results, assignment, optional/safe
chained receivers and tuple/object/generated-data-component destructuring.

`tests/test_return_consumer_flow.py` copies these source files into an isolated
production source set and invokes the explicit compiler worker. No main,
application, network client, package installer or data source is executed.
The K2 distribution exercises the shared Javac path; Kotlin K2 lacks source CFG
and has an explicit negative UNKNOWN test rather than a K1 fallback.

Compilation, protocol and graph facts prove static declaration/consumer use, not
that a branch executes, a function terminates, or runtime data is available.
