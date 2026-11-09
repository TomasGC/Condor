plugins {
    kotlin("jvm")
    id("org.jetbrains.kotlinx.kover")
}

kotlin {
    jvmToolchain(21)
}

dependencies {
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
}

kover {
    currentProject {
        createVariant("debug") {
            add("jvm")
        }
        createVariant("merged") {
            add("jvm")
        }
    }
}
