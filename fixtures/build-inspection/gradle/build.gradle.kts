plugins {
    kotlin("jvm") version "2.1.10"
    java
}
repositories { mavenCentral() }
dependencies { testImplementation("org.junit.jupiter:junit-jupiter:5.11.4") }
kotlin { jvmToolchain(21) }
tasks.test { useJUnitPlatform() }
