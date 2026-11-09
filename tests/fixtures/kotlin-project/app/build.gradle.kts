plugins {
    kotlin("jvm")
    id("org.jetbrains.kotlinx.kover")
}

kotlin {
    jvmToolchain(21)
}

dependencies {
    implementation(project(":core"))
    kover(project(":core"))
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
}

// Two variants, like a project that moved to Kover 0.9. `debug` is what Condor's defaults read; its report leaves
// :core out, the way the Android variant of a real app holds its own module alone. `merged` holds both modules and is
// what a project names with the coverage-* inputs.
kover {
    currentProject {
        createVariant("debug") {
            add("jvm")
        }
        createVariant("merged") {
            add("jvm")
        }
    }
    reports {
        variant("debug") {
            filters {
                excludes {
                    packages("fixture.core")
                }
            }
        }
    }
}
